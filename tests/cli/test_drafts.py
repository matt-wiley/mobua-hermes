import json
import uuid
from pathlib import Path
from typing import Literal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from typer.testing import Result

from news.api.app import app as api_app
from news.service.models import Plugin, PluginDraft, PluginRevision
from news.service.workspaces import IMPLEMENTATION, MANIFEST, MARKER
from tests.cli.test_cli import created_id, log_lines, news, open_session
from tests.cli.test_cli import database_path as database_path
from tests.cli.test_cli import database_url as database_url
from tests.db_failures import fail_commits_on


def new_draft(database_url: str) -> tuple[str, str, str, str]:
    reader = created_id(news(database_url, "reader", "create", "Ada"))
    result = news(database_url, "plugin", "create", "--reader", reader, "Experiments")
    assert result.exit_code == 0, result.output
    plugin = json.loads(result.stdout)
    plugin_id, parent_id = plugin["plugin_id"], plugin["revision_id"]
    result = news(
        database_url,
        "plugin",
        "draft",
        "create",
        "--reader",
        reader,
        "--plugin",
        plugin_id,
        "--from-revision",
        parent_id,
    )
    draft = created_id(result)
    return reader, plugin_id, parent_id, draft


def draft_command(
    database_url: str,
    operation: str,
    ids: tuple[str, str, str, str],
    *args: str,
) -> Result:
    reader, plugin, _, draft = ids
    return news(
        database_url,
        "plugin",
        "draft",
        operation,
        "--reader",
        reader,
        "--plugin",
        plugin,
        "--draft",
        draft,
        *args,
    )


def test_cli_export_edit_save_read_matches_api_and_discards_only_saved_draft(
    database_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = new_draft(database_url)
    reader, plugin, parent, draft = ids
    exported = tmp_path / "experiment"
    assert draft_command(database_url, "export", ids, "--directory", str(exported)).exit_code == 0
    implementation = exported / IMPLEMENTATION
    (implementation / MANIFEST).write_bytes(b'name = "unfinished\r\n')
    (implementation / "main.py").write_bytes(b"def unfinished(\r\n")
    (implementation / ".DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1\xff")
    (implementation / "new.py").write_text("ignored by save")
    before = json.loads(draft_command(database_url, "read", ids).stdout)
    assert before["code"]["main.py"] != "def unfinished(\r\n"
    saved = draft_command(database_url, "save", ids, "--directory", str(exported))
    assert saved.exit_code == 0, saved.output
    assert "version 2" in saved.stdout
    assert json.loads((exported / MARKER).read_text())["version"] == 2
    current = json.loads(draft_command(database_url, "read", ids).stdout)
    assert current["manifest"] == 'name = "unfinished\r\n'
    assert current["code"] == {"main.py": "def unfinished(\r\n"}
    assert current["version"] == 2
    listed = news(database_url, "plugin", "draft", "list", "--reader", reader, "--plugin", plugin)
    assert listed.exit_code == 0 and json.loads(listed.stdout) == [current]
    monkeypatch.setenv("NEWS_DATABASE_URL", database_url)
    with TestClient(api_app) as client:
        assert client.get(f"/readers/{reader}/plugins/{plugin}/drafts/{draft}").json() == current
    with open_session(database_url) as session:
        assert session.get_one(Plugin, uuid.UUID(plugin)).current_revision_id == uuid.UUID(parent)
        assert session.scalar(select(func.count()).select_from(PluginRevision)) == 1
    assert draft_command(database_url, "delete", ids).exit_code == 0
    assert (implementation / "main.py").read_bytes() == b"def unfinished(\r\n"
    assert (exported / MARKER).exists()
    with open_session(database_url) as session:
        assert session.get(PluginDraft, uuid.UUID(draft)) is None
        assert session.get(PluginRevision, uuid.UUID(parent)) is not None


def test_cli_stale_workspace_fails_without_changing_database_or_marker(
    database_url: str,
    tmp_path: Path,
    log_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = new_draft(database_url)
    reader, plugin, _, draft = ids
    directory = tmp_path / "stale"
    assert draft_command(database_url, "export", ids, "--directory", str(directory)).exit_code == 0
    original_marker = (directory / MARKER).read_bytes()
    monkeypatch.setenv("NEWS_DATABASE_URL", database_url)
    with TestClient(api_app) as client:
        assert (
            client.put(
                f"/readers/{reader}/plugins/{plugin}/drafts/{draft}",
                json={"expected_version": 1, "manifest": "API saved", "code": {}},
            ).status_code
            == 200
        )
    result = draft_command(database_url, "save", ids, "--directory", str(directory))
    assert result.exit_code == 1 and result.stdout == ""
    assert "saved version is 2" in result.stderr and "export" in result.stderr
    assert str(log_file) in result.stderr
    assert (directory / MARKER).read_bytes() == original_marker
    with open_session(database_url) as session:
        assert session.get_one(PluginDraft, uuid.UUID(draft)).manifest == "API saved"
    [event] = log_lines(log_file)
    assert event["event"] == "plugin_draft.conflict" and event["operation"] == "save"


@pytest.mark.parametrize("operation", ["read", "save", "delete", "export"])
def test_cli_foreign_draft_rejected_without_changes(
    database_url: str,
    tmp_path: Path,
    operation: str,
) -> None:
    ids = new_draft(database_url)
    other = created_id(news(database_url, "reader", "create", "Other"))
    foreign = (other, *ids[1:])
    args = ["--directory", str(tmp_path / "workspace")] if operation in {"save", "export"} else []
    result = draft_command(database_url, operation, foreign, *args)
    assert result.exit_code == 1 and result.stdout == ""
    assert "no such Reader-owned Plugin or Draft" in result.stderr
    assert not (tmp_path / "workspace").exists()
    with open_session(database_url) as session:
        assert session.get_one(PluginDraft, uuid.UUID(ids[3])).version == 1


def test_cli_unreadable_import_changes_no_saved_files_or_version(
    database_url: str,
    tmp_path: Path,
) -> None:
    ids = new_draft(database_url)
    directory = tmp_path / "unreadable"
    assert draft_command(database_url, "export", ids, "--directory", str(directory)).exit_code == 0
    source = directory / IMPLEMENTATION / "main.py"
    source.chmod(0)
    try:
        result = draft_command(database_url, "save", ids, "--directory", str(directory))
        assert result.exit_code == 1 and result.stdout == ""
        assert "Cannot read workspace" in result.stderr
        assert "permissions" in result.stderr
        with open_session(database_url) as session:
            assert session.get_one(PluginDraft, uuid.UUID(ids[3])).version == 1
        assert json.loads((directory / MARKER).read_text())["version"] == 1
    finally:
        source.chmod(0o600)


@pytest.mark.parametrize(
    "operation,event", [("create", "INSERT"), ("save", "UPDATE"), ("delete", "DELETE")]
)
def test_cli_commit_failure_prints_no_success_and_does_not_advance_marker(
    database_url: str,
    tmp_path: Path,
    operation: str,
    event: Literal["INSERT", "UPDATE", "DELETE"],
) -> None:
    ids = new_draft(database_url)
    directory = tmp_path / "workspace"
    assert draft_command(database_url, "export", ids, "--directory", str(directory)).exit_code == 0
    before = (directory / MARKER).read_bytes()
    with open_session(database_url) as session:
        fail_commits_on(session.get_bind().engine, "plugin_draft", event)
    if operation == "create":
        result = news(
            database_url,
            "plugin",
            "draft",
            "create",
            "--reader",
            ids[0],
            "--plugin",
            ids[1],
            "--from-revision",
            ids[2],
        )
    else:
        args = ["--directory", str(directory)] if operation == "save" else []
        result = draft_command(database_url, operation, ids, *args)
    assert result.exit_code == 1 and result.stdout == ""
    assert (directory / MARKER).read_bytes() == before
    with open_session(database_url) as session:
        assert session.get_one(PluginDraft, uuid.UUID(ids[3])).version == 1
        assert session.scalar(select(func.count()).select_from(PluginDraft)) == 1


def test_cli_database_error_logs_hide_manifest_and_code_parameters(
    database_url: str,
    tmp_path: Path,
    log_file: Path,
) -> None:
    ids = new_draft(database_url)
    directory = tmp_path / "workspace"
    assert draft_command(database_url, "export", ids, "--directory", str(directory)).exit_code == 0
    (directory / IMPLEMENTATION / MANIFEST).write_text("SENSITIVE_MANIFEST")
    (directory / IMPLEMENTATION / "main.py").write_text("SENSITIVE_CODE")
    with open_session(database_url) as session:
        session.connection().exec_driver_sql(
            "CREATE TRIGGER fail_save BEFORE UPDATE ON plugin_draft "
            "BEGIN SELECT RAISE(ABORT, 'cannot save'); END"
        )
        session.commit()
    result = draft_command(database_url, "save", ids, "--directory", str(directory))
    assert result.exit_code == 1 and result.stdout == ""
    assert "SENSITIVE" not in result.output + log_file.read_text()


def test_marker_write_failure_explains_that_the_database_save_committed(
    database_url: str,
    tmp_path: Path,
) -> None:
    ids = new_draft(database_url)
    directory = tmp_path / "workspace"
    assert draft_command(database_url, "export", ids, "--directory", str(directory)).exit_code == 0
    (directory / IMPLEMENTATION / "main.py").write_text("saved local source")
    directory.chmod(0o500)
    try:
        result = draft_command(database_url, "save", ids, "--directory", str(directory))
        assert result.exit_code == 1 and result.stdout == ""
        assert "Draft saved at version 2" in result.stderr
        assert "export again" in result.stderr
        assert json.loads((directory / MARKER).read_text())["version"] == 1
        with open_session(database_url) as session:
            stored = session.get_one(PluginDraft, uuid.UUID(ids[3]))
            assert stored.version == 2 and stored.code == {"main.py": "saved local source"}
    finally:
        directory.chmod(0o700)
