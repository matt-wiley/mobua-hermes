"""API promotion, Revision history and current selection (AC-65, AC-66, AC-67, AC-69, AC-81)."""

import json
import uuid
from typing import Any, Literal, cast

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine
from sqlalchemy.orm import Session

from news.api.app import app
from news.service.channels import bind_plugin, create_channel
from news.service.drafts import create_draft, promote_draft
from news.service.plugins import create_plugin
from tests.api.test_drafts import base
from tests.api.test_drafts import client as client
from tests.db_failures import fail_commits_on
from tests.service.factories import a_reader
from tests.service.test_promotion import committed_state, concurrent_write_before

SENSITIVE = "SENSITIVE_sk-live-sentinel"
PINNED = "# /// script\n# dependencies = ['feedparser==6.0.11']\n# ///\n"
UNPINNED = "# /// script\n# dependencies = ['feedparser>=6']\n# ///\n"


class Ids:
    """A committed Reader-owned Plugin at its starter, bound into a Channel, with one Draft."""

    def __init__(self, session: Session) -> None:
        reader = a_reader(session)
        starter = create_plugin(session, reader.id, "Experiments")
        channel = create_channel(session, reader.id, "Local news")
        bind_plugin(session, reader.id, channel.id, starter.id, {})
        draft = create_draft(session, reader.id, starter.plugin_id, starter.id)
        session.commit()
        self.reader, self.plugin, self.starter, self.draft = (
            reader.id,
            starter.plugin_id,
            starter.id,
            draft.id,
        )
        self.manifest = starter.manifest

    @property
    def drafts(self) -> str:
        return base(self.reader, self.plugin)

    @property
    def revisions(self) -> str:
        return f"/readers/{self.reader}/plugins/{self.plugin}/revisions"

    @property
    def current(self) -> str:
        return f"/readers/{self.reader}/plugins/{self.plugin}/current-revision"


@pytest.fixture
def ids(session: Session) -> Ids:
    return Ids(session)


def promote(client: TestClient, ids: Ids, draft: Any, version: int, confirm: Any = None) -> Any:
    body: dict[str, Any] = {"expected_version": version}
    if confirm is not None:
        body["expected_current_revision_id"] = str(confirm)
    return client.post(f"{ids.drafts}/{draft}/promote", json=body)


def save(client: TestClient, ids: Ids, draft: Any, version: int, code: dict[str, str]) -> Any:
    return client.put(
        f"{ids.drafts}/{draft}",
        json={"expected_version": version, "manifest": ids.manifest, "code": code},
    )


def test_api_promotes_after_commit_and_history_shows_the_new_current_revision(
    client: TestClient, engine: Engine, ids: Ids
) -> None:
    assert save(client, ids, ids.draft, 1, {"main.py": PINNED}).status_code == 200
    bindings = committed_state(engine)["bindings"]

    response = promote(client, ids, ids.draft, 2)

    assert response.status_code == 201, response.text
    revision = response.json()
    assert revision["number"] == 2 and revision["parent_revision_id"] == str(ids.starter)
    assert revision["created_by"] == str(ids.reader)
    assert revision["code"] == {"main.py": PINNED} and revision["manifest"] == ids.manifest
    assert client.get(f"{ids.drafts}/{ids.draft}").status_code == 404
    history = client.get(ids.revisions).json()
    assert history["current_revision_id"] == revision["id"]
    assert [r["id"] for r in history["revisions"]] == [str(ids.starter), revision["id"]]
    assert history["revisions"][1] == revision
    state = committed_state(engine)
    assert state["drafts"] == [] and state["bindings"] == bindings


def test_api_rejects_an_invalid_draft_with_field_errors_and_changes_nothing(
    client: TestClient, engine: Engine, ids: Ids
) -> None:
    assert save(client, ids, ids.draft, 1, {"main.py": UNPINNED}).status_code == 200
    before = committed_state(engine)

    response = promote(client, ids, ids.draft, 2)

    assert response.status_code == 422, response.text
    [error] = response.json()["errors"]
    assert error["field"] == "code[main.py].dependencies.0"
    assert "==" in error["message"]
    assert committed_state(engine) == before


def test_api_stale_promotion_is_a_conflict_naming_both_versions(
    client: TestClient, engine: Engine, ids: Ids
) -> None:
    assert save(client, ids, ids.draft, 1, {"main.py": PINNED}).status_code == 200
    before = committed_state(engine)

    response = promote(client, ids, ids.draft, 1)

    assert response.status_code == 409, response.text
    assert response.json()["expected_version"] == 1
    assert response.json()["actual_version"] == 2
    assert committed_state(engine) == before


def test_api_older_parent_promotion_requires_and_accepts_confirmation(
    client: TestClient, engine: Engine, ids: Ids, session: Session
) -> None:
    sibling = create_draft(session, ids.reader, ids.plugin, ids.starter)
    session.commit()
    newer = promote(client, ids, sibling.id, 1).json()
    before = committed_state(engine)

    unconfirmed = promote(client, ids, ids.draft, 1)

    assert unconfirmed.status_code == 409, unconfirmed.text
    body = unconfirmed.json()
    assert body["reason"] == "confirmation_required"
    assert body["expected_current_revision_id"] is None
    assert body["actual_current_revision_id"] == newer["id"]
    assert body["errors"][0]["field"] == "expected_current_revision_id"
    assert committed_state(engine) == before
    stale = promote(client, ids, ids.draft, 1, confirm=ids.starter)
    assert stale.status_code == 409 and stale.json()["reason"] == "stale_current_selection"

    confirmed = promote(client, ids, ids.draft, 1, confirm=newer["id"])

    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["number"] == 3
    assert confirmed.json()["parent_revision_id"] == str(ids.starter)
    assert client.get(ids.revisions).json()["current_revision_id"] == confirmed.json()["id"]


def test_api_promotion_losing_a_race_for_the_number_is_an_actionable_conflict(
    client: TestClient,
    engine: Engine,
    ids: Ids,
    session: Session,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sibling = create_draft(session, ids.reader, ids.plugin, ids.starter)
    session.commit()
    competing: list[uuid.UUID] = []

    def promote_sibling(connection: Connection) -> None:
        with Session(bind=connection) as other:
            revision = promote_draft(other, ids.reader, ids.plugin, sibling.id, 1)
            competing.append(revision.id)
            other.flush()

    served = cast(Engine, app.state.engine)
    with concurrent_write_before(served, "UPDATE plugin SET", promote_sibling):
        response = promote(client, ids, ids.draft, 1)

    assert response.status_code == 409, response.text
    assert response.json()["reason"] == "stale_current_selection"
    assert response.json()["actual_current_revision_id"] == str(competing[0])
    history = client.get(ids.revisions).json()
    assert history["current_revision_id"] == str(competing[0])
    assert sorted(revision["number"] for revision in history["revisions"]) == [1, 2]
    assert ids.draft in [row[0] for row in committed_state(engine)["drafts"]]
    logs = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    events = [(line["event"], line.get("reason")) for line in logs]
    assert ("plugin_draft.conflict", "stale_current_selection") in events
    assert "api.database_failed" not in [event for event, _ in events]


def test_api_selects_any_revision_without_creating_one_or_moving_bindings(
    client: TestClient, engine: Engine, ids: Ids
) -> None:
    newer = promote(client, ids, ids.draft, 1).json()
    before = committed_state(engine)

    response = client.put(
        ids.current,
        json={"revision_id": str(ids.starter), "expected_current_revision_id": newer["id"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["current_revision_id"] == str(ids.starter)
    assert response.json() == client.get(ids.revisions).json()
    after = committed_state(engine)
    assert after["current"] == [(ids.plugin, ids.starter)]
    assert after["revisions"] == before["revisions"]
    assert after["bindings"] == before["bindings"]

    stale = client.put(
        ids.current,
        json={"revision_id": newer["id"], "expected_current_revision_id": newer["id"]},
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["actual_current_revision_id"] == str(ids.starter)
    assert committed_state(engine) == after


@pytest.mark.parametrize("target", ["unknown", "other_plugin", "foreign"])
def test_api_rejects_selecting_revisions_outside_the_plugin(
    client: TestClient, engine: Engine, session: Session, ids: Ids, target: str
) -> None:
    other = create_plugin(session, ids.reader, "Other")
    foreign = create_plugin(session, a_reader(session, "Mallory").id, "Theirs")
    session.commit()
    revision = {"unknown": uuid.uuid7(), "other_plugin": other.id, "foreign": foreign.id}[target]
    before = committed_state(engine)

    response = client.put(
        ids.current,
        json={"revision_id": str(revision), "expected_current_revision_id": str(ids.starter)},
    )

    assert response.status_code == 422, response.text
    assert response.json()["errors"][0]["field"] == "revision_id"
    assert committed_state(engine) == before


@pytest.mark.parametrize("operation", ["promote", "history", "select"])
def test_api_foreign_and_unknown_plugins_return_identical_safe_errors(
    client: TestClient, engine: Engine, session: Session, ids: Ids, operation: str
) -> None:
    other = a_reader(session, "Mallory")
    session.commit()
    before = committed_state(engine)
    responses: list[Any] = []
    for reader, plugin in [(other.id, ids.plugin), (ids.reader, uuid.uuid7())]:
        prefix = f"/readers/{reader}/plugins/{plugin}"
        match operation:
            case "promote":
                response = client.post(
                    f"{prefix}/drafts/{ids.draft}/promote", json={"expected_version": 1}
                )
            case "history":
                response = client.get(f"{prefix}/revisions")
            case _:
                response = client.put(
                    f"{prefix}/current-revision",
                    json={
                        "revision_id": str(ids.starter),
                        "expected_current_revision_id": str(ids.starter),
                    },
                )
        assert response.status_code == 404, response.text
        responses.append(response.json())
    assert responses[0] == responses[1]
    assert committed_state(engine) == before


@pytest.mark.parametrize(
    "path,payload",
    [
        ("promote", {"expected_version": 0}),
        ("promote", {"expected_version": True}),
        ("promote", {"expected_version": 1, "expected_current_revision_id": "nope"}),
        ("promote", {"expected_version": 1, "extra": "no"}),
        ("select", {"revision_id": "x", "expected_current_revision_id": "x"}),
        ("select", {"revision_id": str(uuid.uuid7())}),
    ],
)
def test_api_validates_request_shapes(
    client: TestClient, engine: Engine, ids: Ids, path: str, payload: dict[str, Any]
) -> None:
    before = committed_state(engine)
    if path == "promote":
        response = client.post(f"{ids.drafts}/{ids.draft}/promote", json=payload)
    else:
        response = client.put(ids.current, json=payload)

    assert response.status_code == 422, response.text
    assert committed_state(engine) == before


@pytest.mark.parametrize(
    "operation,table,event",
    [
        ("promote", "plugin_draft", "DELETE"),
        ("promote", "plugin_revision", "INSERT"),
        ("select", "plugin", "UPDATE"),
    ],
)
def test_api_commit_failure_reports_no_success_and_rolls_back(
    client: TestClient,
    engine: Engine,
    ids: Ids,
    operation: str,
    table: str,
    event: Literal["INSERT", "UPDATE", "DELETE"],
) -> None:
    before = committed_state(engine)
    fail_commits_on(engine, table, event)

    if operation == "promote":
        response = promote(client, ids, ids.draft, 1)
    else:
        response = client.put(
            ids.current,
            json={
                "revision_id": str(ids.starter),
                "expected_current_revision_id": str(ids.starter),
            },
        )

    assert response.status_code == 503, response.text
    assert committed_state(engine) == before


def test_no_endpoint_archives_or_deletes_revisions() -> None:
    routes = [route for route in app.routes if isinstance(route, APIRoute)]
    revision_paths = [route for route in routes if "revision" in route.path]

    assert {(route.path, *sorted(route.methods or ())) for route in revision_paths} == {
        ("/readers/{reader_id}/plugins/{plugin_id}/revisions", "GET"),
        ("/readers/{reader_id}/plugins/{plugin_id}/current-revision", "PUT"),
    }
    assert not any("archive" in route.path for route in routes)


def test_api_logs_lifecycle_events_to_stdout_with_ids_and_no_source(
    client: TestClient,
    session: Session,
    ids: Ids,
    capsys: pytest.CaptureFixture[str],
) -> None:
    discard = create_draft(session, ids.reader, ids.plugin, ids.starter)
    session.commit()
    secret_code = {"main.py": UNPINNED + f"TOKEN = '{SENSITIVE}'\n"}
    assert save(client, ids, ids.draft, 1, secret_code).status_code == 200
    assert save(client, ids, ids.draft, 1, secret_code).status_code == 409
    assert promote(client, ids, ids.draft, 2).status_code == 422
    assert promote(client, ids, ids.draft, 1).status_code == 409
    fixed = {"main.py": PINNED + f"TOKEN = '{SENSITIVE}'\n"}
    assert save(client, ids, ids.draft, 2, fixed).status_code == 200
    promoted = promote(client, ids, ids.draft, 3).json()
    assert promote(client, ids, discard.id, 1).status_code == 409
    selection = {"revision_id": str(ids.starter), "expected_current_revision_id": str(ids.starter)}
    assert client.put(ids.current, json=selection).status_code == 409
    assert client.delete(f"{ids.drafts}/{discard.id}").status_code == 204

    output = capsys.readouterr()
    logs = [json.loads(line) for line in output.out.splitlines()]
    events = [(line["event"], line.get("operation"), line.get("reason")) for line in logs]
    assert events == [
        ("plugin_draft.conflict", "save", "stale_version"),
        ("plugin_draft.rejected", None, "invalid_implementation"),
        ("plugin_draft.conflict", "promote", "stale_version"),
        ("plugin_draft.promoted", None, None),
        ("plugin_draft.conflict", "promote", "confirmation_required"),
        ("plugin_draft.conflict", "select_current", "stale_current_selection"),
        ("plugin_draft.deleted", None, None),
    ]
    assert all(line["level"] == "info" for line in logs)
    assert all(line["reader_id"] == str(ids.reader) for line in logs)
    assert all(line["plugin_id"] == str(ids.plugin) for line in logs)
    assert logs[1]["fields"] == ["code[main.py].dependencies.0"]
    assert logs[3]["draft_id"] == str(ids.draft)
    assert logs[3]["parent_revision_id"] == str(ids.starter)
    assert logs[3]["revision_id"] == promoted["id"]
    assert "draft_id" not in logs[5]
    assert logs[6]["draft_id"] == str(discard.id)
    assert SENSITIVE not in output.out + output.err
    assert "feedparser" not in output.out
