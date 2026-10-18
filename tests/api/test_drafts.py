import json
import uuid
from collections.abc import Iterator
from typing import Any, Literal

import pytest
import structlog
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from news.api.app import app
from news.service.drafts import create_draft
from news.service.models import Plugin, PluginDraft, PluginRevision
from news.service.plugins import create_plugin
from tests.db_failures import fail_commits_on
from tests.service.factories import a_built_in_plugin_revision, a_reader


@pytest.fixture
def client(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("NEWS_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    previous = structlog.get_config()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
    finally:
        structlog.configure(**previous)


def base(reader_id: uuid.UUID, plugin_id: uuid.UUID) -> str:
    return f"/readers/{reader_id}/plugins/{plugin_id}/drafts"


def test_api_starter_and_draft_crud(client: TestClient, session: Session, engine: Engine) -> None:
    reader = a_reader(session)
    session.commit()
    created = client.post(f"/readers/{reader.id}/plugins", json={"name": "API Plugin"})
    assert created.status_code == 201, created.text
    result = created.json()
    plugin_id, parent_id = uuid.UUID(result["plugin_id"]), uuid.UUID(result["revision_id"])
    url = base(reader.id, plugin_id)
    assert client.get(url).json() == []
    response = client.post(url, json={"parent_revision_id": str(parent_id)})
    assert response.status_code == 201, response.text
    draft = response.json()
    assert draft["reader_id"] == str(reader.id) and draft["plugin_id"] == str(plugin_id)
    assert draft["version"] == 1 and draft["parent_revision_id"] == str(parent_id)
    assert draft["code"]["main.py"]
    sibling = client.post(url, json={"parent_revision_id": str(parent_id)}).json()
    endpoint = url + "/" + draft["id"]
    unfinished = {
        "expected_version": 1,
        "manifest": 'name = "unfinished',
        "code": {"unfinished.py": "def not_done(\r\n"},
    }
    response = client.put(endpoint, json=unfinished)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["version"] == 2
    assert saved["manifest"] == unfinished["manifest"] and saved["code"] == unfinished["code"]
    assert client.get(endpoint).json() == saved
    assert client.get(url).json() == [saved, sibling]
    with Session(engine) as outside:
        assert outside.get_one(PluginDraft, uuid.UUID(draft["id"])).version == 2
        assert outside.get_one(Plugin, plugin_id).current_revision_id == parent_id
        assert outside.scalar(select(func.count()).select_from(PluginRevision)) == 1
    stale = client.put(endpoint, json=unfinished)
    assert stale.status_code == 409
    assert stale.json()["expected_version"] == 1 and stale.json()["actual_version"] == 2
    assert client.get(endpoint).json() == saved
    assert client.delete(endpoint).status_code == 204
    assert client.get(endpoint).status_code == 404
    assert client.get(url).json() == [sibling]


@pytest.mark.parametrize("operation", ["create", "list", "read", "save", "delete"])
def test_foreign_and_unknown_api_targets_return_identical_safe_errors(
    operation: str,
    client: TestClient,
    session: Session,
) -> None:
    reader, other = a_reader(session), a_reader(session, "other")
    parent = create_plugin(session, reader.id, "own")
    draft = create_draft(session, reader.id, parent.plugin_id, parent.id)
    session.commit()
    responses: list[dict[str, Any]] = []
    for actor, plugin_id in [(other.id, parent.plugin_id), (reader.id, uuid.uuid7())]:
        url = base(actor, plugin_id)
        endpoint = f"{url}/{draft.id}"
        match operation:
            case "create":
                response = client.post(url, json={"parent_revision_id": str(parent.id)})
            case "list":
                response = client.get(url)
            case "read":
                response = client.get(endpoint)
            case "save":
                response = client.put(
                    endpoint, json={"expected_version": 1, "manifest": "x", "code": {}}
                )
            case _:
                response = client.delete(endpoint)
        assert response.status_code == 404, response.text
        responses.append(response.json())
    assert responses[0] == responses[1]
    session.expire_all()
    assert session.get_one(PluginDraft, draft.id).version == 1
    assert session.scalar(select(func.count()).select_from(PluginDraft)) == 1


@pytest.mark.parametrize("problem", ["wrong_plugin", "builtin", "unknown_parent"])
def test_api_rejects_invalid_parent_targets_without_inserting(
    problem: str,
    client: TestClient,
    session: Session,
) -> None:
    reader = a_reader(session)
    parent = create_plugin(session, reader.id, "own")
    other = create_plugin(session, reader.id, "other")
    builtin = a_built_in_plugin_revision(session)
    plugin_id, parent_id = {
        "wrong_plugin": (parent.plugin_id, other.id),
        "builtin": (builtin.plugin_id, builtin.id),
        "unknown_parent": (parent.plugin_id, uuid.uuid7()),
    }[problem]
    session.commit()
    response = client.post(base(reader.id, plugin_id), json={"parent_revision_id": str(parent_id)})
    assert response.status_code == (404 if problem == "builtin" else 422), response.text
    assert session.scalar(select(func.count()).select_from(PluginDraft)) == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"expected_version": 0, "manifest": "", "code": {}},
        {"expected_version": True, "manifest": "", "code": {}},
        {"expected_version": 1, "manifest": 123, "code": {}},
        {"expected_version": 1, "manifest": "", "code": {"x.py": 1}},
        {"expected_version": 1, "manifest": "SENSITIVE", "code": {"../escape": "SENSITIVE"}},
        {"expected_version": 1, "manifest": "", "code": {}, "extra": "no"},
    ],
)
def test_api_validates_request_shape_and_safe_paths(
    payload: dict[str, Any],
    client: TestClient,
    session: Session,
) -> None:
    reader = a_reader(session)
    parent = create_plugin(session, reader.id, "own")
    draft = create_draft(session, reader.id, parent.plugin_id, parent.id)
    session.commit()
    response = client.put(f"{base(reader.id, parent.plugin_id)}/{draft.id}", json=payload)
    assert response.status_code == 422, response.text
    session.expire_all()
    assert session.get_one(PluginDraft, draft.id).version == 1


@pytest.mark.parametrize(
    "operation,table,event",
    [
        ("plugin", "plugin", "INSERT"),
        ("create", "plugin_draft", "INSERT"),
        ("save", "plugin_draft", "UPDATE"),
        ("delete", "plugin_draft", "DELETE"),
    ],
)
def test_api_commit_failure_returns_no_success_and_rolls_back(
    operation: str,
    table: str,
    event: Literal["INSERT", "UPDATE", "DELETE"],
    client: TestClient,
    session: Session,
    engine: Engine,
    capsys: pytest.CaptureFixture[str],
) -> None:
    reader = a_reader(session)
    parent = create_plugin(session, reader.id, "own")
    draft = create_draft(session, reader.id, parent.plugin_id, parent.id)
    session.commit()
    fail_commits_on(engine, table, event)
    url = base(reader.id, parent.plugin_id)
    response = {
        "plugin": lambda: client.post(f"/readers/{reader.id}/plugins", json={"name": "SENSITIVE"}),
        "create": lambda: client.post(url, json={"parent_revision_id": str(parent.id)}),
        "save": lambda: client.put(
            f"{url}/{draft.id}",
            json={"expected_version": 1, "manifest": "SENSITIVE", "code": {"x.py": "SENSITIVE"}},
        ),
        "delete": lambda: client.delete(f"{url}/{draft.id}"),
    }[operation]()
    assert response.status_code == 503, response.text
    assert "SENSITIVE" not in response.text
    session.expire_all()
    assert session.get_one(PluginDraft, draft.id).version == 1
    assert session.scalar(select(func.count()).select_from(PluginDraft)) == 1
    assert session.scalar(select(func.count()).select_from(Plugin)) == 1
    lines = capsys.readouterr().out
    assert "SENSITIVE" not in lines
    assert any(json.loads(line)["event"] == "api.database_failed" for line in lines.splitlines())


def test_api_logs_conflicts_and_discard_to_stdout_without_source(
    client: TestClient,
    session: Session,
    capsys: pytest.CaptureFixture[str],
) -> None:
    reader = a_reader(session)
    parent = create_plugin(session, reader.id, "own")
    draft = create_draft(session, reader.id, parent.plugin_id, parent.id)
    session.commit()
    endpoint = f"{base(reader.id, parent.plugin_id)}/{draft.id}"
    payload = {"expected_version": 1, "manifest": "SENSITIVE", "code": {"x.py": "SENSITIVE"}}
    assert client.put(endpoint, json=payload).status_code == 200
    assert client.put(endpoint, json=payload).status_code == 409
    assert client.delete(endpoint).status_code == 204
    output = capsys.readouterr()
    logs = [json.loads(line) for line in output.out.splitlines()]
    assert [line["event"] for line in logs] == ["plugin_draft.conflict", "plugin_draft.deleted"]
    assert all(line["level"] == "info" for line in logs)
    assert "SENSITIVE" not in output.out + output.err
