"""CLI promotion, Revision history and current selection (AC-63, AC-65 to AC-69, AC-81)."""

import json
import uuid
from pathlib import Path
from typing import Any, Literal

import pytest
from fastapi.testclient import TestClient
from typer.testing import Result

from news.api.app import app as api_app
from news.service.db import create_engine_for
from news.service.workspaces import IMPLEMENTATION, MARKER
from tests.cli.test_cli import bind, created_id, log_lines, news
from tests.cli.test_cli import database_path as database_path
from tests.cli.test_cli import database_url as database_url
from tests.cli.test_drafts import draft_command, new_draft
from tests.db_failures import fail_commits_on
from tests.service.test_promotion import committed_state

SENSITIVE = "SENSITIVE_sk-live-sentinel"
PINNED = "# /// script\n# dependencies = ['feedparser==6.0.11']\n# ///\n"
UNPINNED = "# /// script\n# dependencies = ['feedparser>=6']\n# ///\n"

type Ids = tuple[str, str, str, str]


def state(database_url: str) -> dict[str, Any]:
    engine = create_engine_for(database_url)
    try:
        return committed_state(engine)
    finally:
        engine.dispose()


def bound_draft(database_url: str) -> Ids:
    """A new Draft of a Plugin whose starter is bound into a Channel."""
    ids = new_draft(database_url)
    reader, _, starter, _ = ids
    channel = created_id(news(database_url, "channel", "create", "--reader", reader, "Local"))
    assert bind(database_url, reader, channel, starter, "{}").exit_code == 0
    return ids


def promote(database_url: str, ids: Ids, *args: str) -> Result:
    return draft_command(database_url, "promote", ids, *args)


def revision_command(database_url: str, ids: Ids, operation: str, *args: str) -> Result:
    reader, plugin, _, _ = ids
    return news(
        database_url, "plugin", "revision", operation, "--reader", reader, "--plugin", plugin, *args
    )


def select(database_url: str, ids: Ids, revision: str, expected: str) -> Result:
    return revision_command(
        database_url, ids, "select", "--revision", revision, "--expected-current", expected
    )


def export(database_url: str, ids: Ids, directory: Path) -> None:
    assert draft_command(database_url, "export", ids, "--directory", str(directory)).exit_code == 0


def save_main(database_url: str, ids: Ids, directory: Path, source: str) -> None:
    (directory / IMPLEMENTATION / "main.py").write_text(source)
    saved = draft_command(database_url, "save", ids, "--directory", str(directory))
    assert saved.exit_code == 0, saved.output


def another_draft(database_url: str, ids: Ids, parent: str) -> Ids:
    reader, plugin, _, _ = ids
    result = news(
        database_url,
        "plugin",
        "draft",
        "create",
        "--reader",
        reader,
        "--plugin",
        plugin,
        "--from-revision",
        parent,
    )
    return (reader, plugin, parent, created_id(result))


def test_cli_promotes_the_saved_workspace_draft_and_history_matches_the_api(
    database_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = bound_draft(database_url)
    reader, plugin, starter, draft = ids
    directory = tmp_path / "workspace"
    export(database_url, ids, directory)
    save_main(database_url, ids, directory, PINNED)
    bindings = state(database_url)["bindings"]

    result = promote(database_url, ids, "--directory", str(directory))

    assert result.exit_code == 0, result.output
    revision = json.loads(result.stdout)
    assert revision["number"] == 2 and revision["parent_revision_id"] == starter
    assert revision["code"] == {"main.py": PINNED} and revision["created_by"] == reader
    assert (directory / IMPLEMENTATION / "main.py").read_text() == PINNED
    assert (directory / MARKER).exists()
    after = state(database_url)
    assert after["drafts"] == [] and after["bindings"] == bindings
    history = revision_command(database_url, ids, "list")
    assert history.exit_code == 0, history.output
    assert json.loads(history.stdout)["current_revision_id"] == revision["id"]
    monkeypatch.setenv("NEWS_DATABASE_URL", database_url)
    with TestClient(api_app) as client:
        api_history = client.get(f"/readers/{reader}/plugins/{plugin}/revisions").json()
    assert json.loads(history.stdout) == api_history
    assert draft_command(database_url, "read", ids).exit_code == 1, f"{draft} was deleted"


def test_cli_promotes_saved_contents_not_unsaved_local_edits(
    database_url: str, tmp_path: Path
) -> None:
    ids = bound_draft(database_url)
    directory = tmp_path / "workspace"
    export(database_url, ids, directory)
    saved = json.loads(draft_command(database_url, "read", ids).stdout)
    (directory / IMPLEMENTATION / "main.py").write_text(UNPINNED + "unsaved()\n")

    result = promote(database_url, ids, "--directory", str(directory))

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["code"] == saved["code"]


def test_cli_promotes_with_an_explicit_expected_version(database_url: str) -> None:
    ids = bound_draft(database_url)

    result = promote(database_url, ids, "--expected-version", "1")

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["number"] == 2


def test_cli_stale_workspace_promotion_is_a_conflict_and_changes_nothing(
    database_url: str, tmp_path: Path, log_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = bound_draft(database_url)
    reader, plugin, _, draft = ids
    directory = tmp_path / "workspace"
    export(database_url, ids, directory)
    monkeypatch.setenv("NEWS_DATABASE_URL", database_url)
    with TestClient(api_app) as client:
        saved = client.put(
            f"/readers/{reader}/plugins/{plugin}/drafts/{draft}",
            json={"expected_version": 1, "manifest": "API saved", "code": {}},
        )
        assert saved.status_code == 200
    before = state(database_url)

    result = promote(database_url, ids, "--directory", str(directory))

    assert result.exit_code == 1 and result.stdout == ""
    assert "saved version is 2" in result.stderr
    assert state(database_url) == before
    [event] = [line for line in log_lines(log_file) if line["event"] == "plugin_draft.conflict"]
    assert event["operation"] == "promote" and event["reason"] == "stale_version"


def test_cli_invalid_promotion_reports_field_errors_and_changes_nothing(
    database_url: str, tmp_path: Path, log_file: Path
) -> None:
    ids = bound_draft(database_url)
    directory = tmp_path / "workspace"
    export(database_url, ids, directory)
    save_main(database_url, ids, directory, UNPINNED)
    before = state(database_url)

    result = promote(database_url, ids, "--directory", str(directory))

    assert result.exit_code == 1 and result.stdout == ""
    assert "code[main.py].dependencies.0" in result.stderr
    assert "==" in result.stderr and str(log_file) in result.stderr
    assert state(database_url) == before


def test_cli_older_parent_promotion_needs_confirmation(database_url: str) -> None:
    ids = bound_draft(database_url)
    starter = ids[2]
    sibling = another_draft(database_url, ids, starter)
    newer = json.loads(promote(database_url, sibling, "--expected-version", "1").stdout)
    before = state(database_url)

    unconfirmed = promote(database_url, ids, "--expected-version", "1")

    assert unconfirmed.exit_code == 1 and unconfirmed.stdout == ""
    assert newer["id"] in unconfirmed.stderr and "confirm" in unconfirmed.stderr
    assert state(database_url) == before

    confirmed = promote(
        database_url, ids, "--expected-version", "1", "--confirm-current", newer["id"]
    )

    assert confirmed.exit_code == 0, confirmed.output
    revision = json.loads(confirmed.stdout)
    assert revision["number"] == 3 and revision["parent_revision_id"] == starter


def test_cli_selects_an_older_revision_without_moving_bindings(database_url: str) -> None:
    ids = bound_draft(database_url)
    starter = ids[2]
    newer = json.loads(promote(database_url, ids, "--expected-version", "1").stdout)
    before = state(database_url)

    result = select(database_url, ids, starter, newer["id"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["current_revision_id"] == starter
    after = state(database_url)
    assert after["revisions"] == before["revisions"]
    assert after["bindings"] == before["bindings"]
    assert after["current"] == [(uuid.UUID(ids[1]), uuid.UUID(starter))]

    stale = select(database_url, ids, newer["id"], newer["id"])

    assert stale.exit_code == 1 and stale.stdout == ""
    assert "review the history" in stale.stderr
    assert state(database_url) == after


@pytest.mark.parametrize(
    "target", ["unknown", "other_plugin", "foreign_revision", "foreign_plugin"]
)
def test_cli_rejects_selections_outside_the_readers_plugin(database_url: str, target: str) -> None:
    ids = bound_draft(database_url)
    reader, _, starter, _ = ids
    other = json.loads(news(database_url, "plugin", "create", "--reader", reader, "Other").stdout)
    mallory = created_id(news(database_url, "reader", "create", "Mallory"))
    theirs = json.loads(
        news(database_url, "plugin", "create", "--reader", mallory, "Theirs").stdout
    )
    before = state(database_url)
    actor = (mallory, *ids[1:]) if target == "foreign_plugin" else ids
    revision = {
        "unknown": str(uuid.uuid7()),
        "other_plugin": other["revision_id"],
        "foreign_revision": theirs["revision_id"],
        "foreign_plugin": starter,
    }[target]

    result = select(database_url, actor, revision, starter)

    assert result.exit_code == 1 and result.stdout == ""
    expected = "no such Reader-owned Plugin" if target == "foreign_plugin" else "revision_id"
    assert expected in result.stderr
    assert state(database_url) == before


@pytest.mark.parametrize("args", [[], ["--expected-version", "1", "--directory", "x"]])
def test_cli_promotion_needs_exactly_one_version_source(database_url: str, args: list[str]) -> None:
    ids = bound_draft(database_url)
    before = state(database_url)

    result = promote(database_url, ids, *args)

    assert result.exit_code == 2
    assert "--directory" in result.stderr and "--expected-version" in result.stderr
    assert state(database_url) == before


@pytest.mark.parametrize(
    "operation,table,event",
    [
        ("promote", "plugin_draft", "DELETE"),
        ("promote", "plugin_revision", "INSERT"),
        ("select", "plugin", "UPDATE"),
    ],
)
def test_cli_commit_failure_prints_no_success(
    database_url: str,
    operation: str,
    table: str,
    event: Literal["INSERT", "UPDATE", "DELETE"],
) -> None:
    ids = bound_draft(database_url)
    before = state(database_url)
    engine = create_engine_for(database_url)
    fail_commits_on(engine, table, event)
    engine.dispose()

    if operation == "promote":
        result = promote(database_url, ids, "--expected-version", "1")
    else:
        result = select(database_url, ids, ids[2], ids[2])

    assert result.exit_code == 1 and result.stdout == ""
    assert state(database_url) == before


def test_cli_has_no_revision_archive_or_delete_command(database_url: str) -> None:
    result = news(database_url, "plugin", "revision", "--help")

    assert result.exit_code == 0, result.output
    assert "list" in result.stdout and "select" in result.stdout
    assert "delete" not in result.stdout.lower() and "archive" not in result.stdout.lower()


def test_cli_logs_lifecycle_events_to_its_log_file_without_source(
    database_url: str, tmp_path: Path, log_file: Path
) -> None:
    ids = bound_draft(database_url)
    starter = ids[2]
    discard = another_draft(database_url, ids, starter)
    directory = tmp_path / "workspace"
    export(database_url, ids, directory)
    save_main(database_url, ids, directory, UNPINNED + f"TOKEN = '{SENSITIVE}'\n")
    log_file.write_text("")

    outputs = [
        promote(database_url, ids, "--directory", str(directory)),
        promote(database_url, ids, "--expected-version", "1"),
    ]
    save_main(database_url, ids, directory, PINNED + f"TOKEN = '{SENSITIVE}'\n")
    promoted = promote(database_url, ids, "--directory", str(directory))
    outputs += [
        promoted,
        promote(database_url, discard, "--expected-version", "1"),
        select(database_url, ids, starter, starter),
        draft_command(database_url, "delete", discard),
    ]

    logs = log_lines(log_file)
    events = [(line["event"], line.get("operation"), line.get("reason")) for line in logs]
    assert events == [
        ("plugin_draft.rejected", None, "invalid_implementation"),
        ("plugin_draft.conflict", "promote", "stale_version"),
        ("plugin_draft.promoted", None, None),
        ("plugin_draft.conflict", "promote", "confirmation_required"),
        ("plugin_draft.conflict", "select_current", "stale_current_selection"),
        ("plugin_draft.deleted", None, None),
    ]
    assert all(line["level"] == "info" for line in logs)
    assert all(line["reader_id"] == ids[0] and line["plugin_id"] == ids[1] for line in logs)
    assert logs[0]["fields"] == ["code[main.py].dependencies.0"]
    assert logs[2]["revision_id"] == json.loads(promoted.stdout)["id"]
    assert logs[2]["parent_revision_id"] == starter and logs[2]["draft_id"] == ids[3]
    assert SENSITIVE not in log_file.read_text()
    assert "feedparser" not in log_file.read_text()
    assert all("plugin_draft" not in result.stdout for result in outputs)
