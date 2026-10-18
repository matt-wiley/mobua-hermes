import json
import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from news.service.drafts import create_draft, save_draft
from news.service.models import PluginDraft
from news.service.plugins import create_plugin
from news.service.validation import ValidationRejected
from news.service.workspaces import (
    IMPLEMENTATION,
    MANIFEST,
    MARKER,
    WorkspaceError,
    advance_marker,
    export_workspace,
    implementation_files,
    read_marker_version,
    read_workspace,
)
from tests.service.factories import a_reader


def a_draft(session: Session) -> PluginDraft:
    reader = a_reader(session)
    parent = create_plugin(session, reader.id, "workspace")
    draft = create_draft(session, reader.id, parent.plugin_id, parent.id)
    session.commit()
    return draft


def test_file_selection_preserves_text_and_excludes_metadata() -> None:
    assert implementation_files("bad\r\n", {"nested/main.py": "π\r\n", ".env.example": ""}) == {
        "manifest.toml": "bad\r\n",
        "nested/main.py": "π\r\n",
        ".env.example": "",
    }
    assert MARKER not in implementation_files("", {})


@pytest.mark.parametrize(
    "filename",
    [
        "",
        ".",
        "..",
        "../escape.py",
        "/escape.py",
        "pkg/../../escape",
        "a//b",
        "a/./b",
        "a/../b",
        "C:/escape.py",
        "a\\b",
        "null\x00.py",
        "a/",
        MANIFEST,
        MARKER,
        "manifest.toml/x",
    ],
)
def test_unsafe_or_reserved_names_are_rejected_without_echoing_payload(filename: str) -> None:
    with pytest.raises(ValidationRejected) as raised:
        implementation_files("SENSITIVE_MANIFEST", {filename: "SENSITIVE_CODE"})
    assert [error.field for error in raised.value.errors] == ["code"]
    assert "SENSITIVE" not in str(raised.value)


def test_file_directory_collision_is_rejected() -> None:
    with pytest.raises(ValidationRejected):
        implementation_files("", {"pkg": "", "pkg/main.py": ""})


@pytest.mark.parametrize(
    "code",
    [
        {"MANIFEST.TOML": "would overwrite Manifest"},
        {"Main.py": "one", "main.py": "two"},
        {"PKG": "file", "pkg/main.py": "nested"},
        {"é.py": "one", "e\u0301.py": "two"},
        {"Pkg/a.py": "one", "pkg/b.py": "two"},
        {"é/a.py": "one", "e\u0301/b.py": "two"},
    ],
)
def test_export_names_remain_distinct_on_case_insensitive_filesystems(code: dict[str, str]) -> None:
    with pytest.raises(ValidationRejected):
        implementation_files("", code)


def test_export_edit_read_and_marker_advance_preserve_exact_text(
    session: Session,
    tmp_path: Path,
) -> None:
    draft = a_draft(session)
    save_draft(
        session,
        draft.reader_id,
        draft.plugin_id,
        draft.id,
        1,
        "unfinished\r\n",
        {"main.py": "π\r\n"},
    )
    session.commit()
    directory = tmp_path / "workspace"
    export_workspace(draft, directory)
    marker = json.loads((directory / MARKER).read_text())
    assert marker == {
        "format": 1,
        "reader_id": str(draft.reader_id),
        "plugin_id": str(draft.plugin_id),
        "draft_id": str(draft.id),
        "version": 2,
    }
    assert sorted(path.name for path in (directory / IMPLEMENTATION).iterdir()) == [
        "main.py",
        MANIFEST,
    ]
    assert (directory / IMPLEMENTATION / MANIFEST).read_bytes() == b"unfinished\r\n"
    assert (directory / IMPLEMENTATION / "main.py").read_bytes() == "π\r\n".encode()
    (directory / IMPLEMENTATION / "main.py").write_bytes(b"if unfinished(\r\n")
    workspace = read_workspace(directory, draft.reader_id, draft.plugin_id, draft.id)
    assert workspace.manifest == "unfinished\r\n"
    assert workspace.code == {"main.py": "if unfinished(\r\n"}
    assert workspace.version == 2
    advance_marker(directory, workspace, 3)
    assert read_workspace(directory, draft.reader_id, draft.plugin_id, draft.id).version == 3
    assert workspace.version == 2


def test_read_ignores_every_file_except_the_manifest_and_main_py(
    session: Session, tmp_path: Path
) -> None:
    draft = a_draft(session)
    directory = tmp_path / "workspace"
    export_workspace(draft, directory)
    implementation = directory / IMPLEMENTATION
    (implementation / ".DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1\xff")
    (implementation / "__pycache__").mkdir()
    (implementation / "__pycache__" / "main.cpython-314.pyc").write_bytes(b"\xa7\r\r\n\xff")
    (implementation / "main.py~").write_text("editor backup")
    (implementation / ".main.py.swp").write_bytes(b"\xff\xfe")
    (implementation / "helper.py").write_text("not part of the Plugin")
    (implementation / "link.py").symlink_to(tmp_path / "outside.py")
    os.mkfifo(implementation / "pipe")
    workspace = read_workspace(directory, draft.reader_id, draft.plugin_id, draft.id)
    assert workspace.code == draft.code
    assert workspace.manifest == draft.manifest


def test_removing_main_py_saves_an_empty_code_set(session: Session, tmp_path: Path) -> None:
    draft = a_draft(session)
    directory = tmp_path / "workspace"
    export_workspace(draft, directory)
    (directory / IMPLEMENTATION / "main.py").unlink()
    workspace = read_workspace(directory, draft.reader_id, draft.plugin_id, draft.id)
    assert workspace.code == {}


@pytest.mark.parametrize(
    "code", [{"main.py": "", "helper.py": ""}, {"lib/main.py": ""}, {"other.py": ""}]
)
def test_export_refuses_drafts_with_files_other_than_main_py(
    session: Session, tmp_path: Path, code: dict[str, str]
) -> None:
    draft = a_draft(session)
    save_draft(session, draft.reader_id, draft.plugin_id, draft.id, 1, "", code)
    session.commit()
    directory = tmp_path / "workspace"
    with capture_logs() as logs, pytest.raises(WorkspaceError, match=r"main\.py") as raised:
        export_workspace(draft, directory)
    assert not directory.exists()
    assert "helper.py" not in str(raised.value) and "other.py" not in str(raised.value)
    assert logs[0]["event"] == "plugin_workspace.failed"


def test_export_refuses_existing_directory_and_leaves_local_edits(
    session: Session, tmp_path: Path
) -> None:
    draft = a_draft(session)
    directory = tmp_path / "workspace"
    export_workspace(draft, directory)
    (directory / IMPLEMENTATION / "main.py").write_text("local unsaved")
    with pytest.raises(WorkspaceError, match="exist"):
        export_workspace(draft, directory)
    assert (directory / IMPLEMENTATION / "main.py").read_text() == "local unsaved"


@pytest.mark.parametrize(
    "problem",
    [
        "missing_marker",
        "malformed_marker",
        "wrong_draft",
        "missing_manifest",
        "unreadable",
        "bad_utf8",
        "symlink_main",
        "symlink_manifest",
        "symlink_implementation",
        "symlink_root",
        "fifo_main",
        "main_is_directory",
    ],
)
def test_read_failures_are_actionable_and_never_return_partial_contents(
    session: Session,
    tmp_path: Path,
    problem: str,
) -> None:
    draft = a_draft(session)
    directory = tmp_path / "workspace"
    export_workspace(draft, directory)
    manifest = directory / IMPLEMENTATION / MANIFEST
    marker = directory / MARKER
    unreadable: Path | None = None
    if problem == "missing_marker":
        marker.unlink()
    elif problem == "malformed_marker":
        marker.write_text("not-json")
    elif problem == "wrong_draft":
        data = json.loads(marker.read_text())
        data["draft_id"] = str(uuid.uuid7())
        marker.write_text(json.dumps(data))
    elif problem == "missing_manifest":
        manifest.unlink()
    elif problem == "unreadable":
        unreadable = directory / IMPLEMENTATION / "main.py"
        unreadable.chmod(0)
    elif problem == "bad_utf8":
        (directory / IMPLEMENTATION / "main.py").write_bytes(b"\xff")
    elif problem == "symlink_main":
        outside = tmp_path / "outside.py"
        outside.write_text("SENSITIVE")
        (directory / IMPLEMENTATION / "main.py").unlink()
        (directory / IMPLEMENTATION / "main.py").symlink_to(outside)
    elif problem == "symlink_manifest":
        outside = tmp_path / "outside.toml"
        outside.write_text("SENSITIVE")
        manifest.unlink()
        manifest.symlink_to(outside)
    elif problem == "symlink_implementation":
        moved = tmp_path / "moved"
        (directory / IMPLEMENTATION).rename(moved)
        (directory / IMPLEMENTATION).symlink_to(moved, target_is_directory=True)
    elif problem == "symlink_root":
        linked = tmp_path / "linked-workspace"
        linked.symlink_to(directory, target_is_directory=True)
        directory = linked
    elif problem == "fifo_main":
        (directory / IMPLEMENTATION / "main.py").unlink()
        os.mkfifo(directory / IMPLEMENTATION / "main.py")
    else:
        (directory / IMPLEMENTATION / "main.py").unlink()
        (directory / IMPLEMENTATION / "main.py").mkdir()
    try:
        with capture_logs() as logs, pytest.raises(WorkspaceError) as raised:
            read_workspace(directory, draft.reader_id, draft.plugin_id, draft.id)
        assert str(directory) in str(raised.value)
        assert logs[0]["event"] == "plugin_workspace.failed"
        assert "SENSITIVE" not in str(logs)
    finally:
        if unreadable is not None:
            unreadable.chmod(0o600)


def test_failed_export_leaves_no_partial_destination(session: Session, tmp_path: Path) -> None:
    draft = a_draft(session)
    parent = tmp_path / "readonly"
    parent.mkdir(mode=0o500)
    try:
        with pytest.raises(WorkspaceError):
            export_workspace(draft, parent / "workspace")
        assert not (parent / "workspace").exists()
    finally:
        parent.chmod(0o700)


def test_save_rejects_unsafe_paths_before_mutation_and_logs_safe_fields(session: Session) -> None:
    draft = a_draft(session)
    with capture_logs() as logs, pytest.raises(ValidationRejected):
        save_draft(
            session,
            draft.reader_id,
            draft.plugin_id,
            draft.id,
            1,
            "SENSITIVE_MANIFEST",
            {"../escape": "SENSITIVE_CODE"},
        )
    assert not session.dirty and not session.new
    assert draft.version == 1
    assert logs[0]["event"] == "plugin_draft.save_rejected"
    assert "SENSITIVE" not in str(logs)


def test_marker_version_is_read_without_the_implementation_files(
    session: Session, tmp_path: Path
) -> None:
    draft = a_draft(session)
    directory = tmp_path / "workspace"
    export_workspace(draft, directory)
    (directory / IMPLEMENTATION / MANIFEST).unlink()
    (directory / IMPLEMENTATION / "main.py").unlink()

    version = read_marker_version(directory, draft.reader_id, draft.plugin_id, draft.id)

    assert version == 1


@pytest.mark.parametrize("problem", ["other_draft", "missing", "invalid"])
def test_marker_version_failures_are_actionable(
    session: Session, tmp_path: Path, problem: str
) -> None:
    draft = a_draft(session)
    directory = tmp_path / "workspace"
    export_workspace(draft, directory)
    draft_id = uuid.uuid7() if problem == "other_draft" else draft.id
    if problem == "missing":
        (directory / MARKER).unlink()
    if problem == "invalid":
        (directory / MARKER).write_text('{"version": 0}')

    with capture_logs() as logs, pytest.raises(WorkspaceError) as raised:
        read_marker_version(directory, draft.reader_id, draft.plugin_id, draft_id)

    assert f"Cannot read workspace {directory}" in str(raised.value)
    assert {
        "other_draft": "different Reader, Plugin or Draft",
        "missing": "version marker",
        "invalid": "export again",
    }[problem] in str(raised.value)
    assert [log["event"] for log in logs] == ["plugin_workspace.failed"]
