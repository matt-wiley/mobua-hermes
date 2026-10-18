import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from news.service.drafts import (
    DraftConflict,
    DraftNotFound,
    check_version,
    create_draft,
    delete_draft,
    get_draft,
    save_draft,
)
from news.service.models import Plugin, PluginBinding, PluginDraft, PluginRevision
from news.service.plugins import create_plugin
from tests.service.factories import a_reader
from tests.service.test_immutability import a_bound_channel, stored_columns


@pytest.mark.parametrize(
    "expected,actual,conflict",
    [(1, 1, False), (2, 2, False), (1, 2, True), (3, 2, True), (0, 1, True)],
)
def test_expected_version_rule(expected: int, actual: int, conflict: bool) -> None:
    if conflict:
        with pytest.raises(DraftConflict) as raised:
            check_version(expected, actual)
        assert (raised.value.expected, raised.value.actual) == (expected, actual)
    else:
        check_version(expected, actual)


@pytest.mark.parametrize(
    "manifest,code",
    [
        ('name = "unfinished', {"main.py": "def broken(\r\n", "nested/util.py": "π\n"}),
        ("", {}),
        (
            'name = "x"\ntimeout = -1\n',
            {"main.py": '# /// script\n# dependencies = ["requests>=1"]\n# ///\nprint(1)'},
        ),
    ],
)
def test_unfinished_saves_replace_files_and_preserve_revision_and_binding_state(
    session: Session,
    engine: Engine,
    manifest: str,
    code: dict[str, str],
) -> None:
    parent, channel = a_bound_channel(session)
    assert parent.reader_id is not None and channel.current_revision is not None
    draft = create_draft(session, parent.reader_id, parent.plugin_id, parent.id)
    sibling = create_draft(session, parent.reader_id, parent.plugin_id, parent.id)
    session.commit()
    revision_before = stored_columns(engine, PluginRevision, parent.id)
    plugin_before = stored_columns(engine, Plugin, parent.plugin_id)
    binding = channel.current_revision.bindings[0]
    binding_before = stored_columns(engine, PluginBinding, binding.id)
    with capture_logs() as logs:
        saved = save_draft(session, parent.reader_id, parent.plugin_id, draft.id, 1, manifest, code)
    assert saved.version == 2 and saved.code == code and saved.manifest == manifest
    assert saved.parent_revision_id == parent.id
    assert sibling.version == 1 and sibling.code == parent.code
    assert logs == []
    with Session(engine) as outside:
        assert outside.get_one(PluginDraft, draft.id).version == 1
    session.commit()
    with Session(engine) as outside:
        stored = get_draft(outside, parent.reader_id, parent.plugin_id, draft.id)
        assert stored.version == 2 and stored.manifest == manifest and stored.code == code
        assert outside.scalar(select(func.count()).select_from(PluginRevision)) == 1
    assert stored_columns(engine, PluginRevision, parent.id) == revision_before
    assert stored_columns(engine, Plugin, parent.plugin_id) == plugin_before
    assert stored_columns(engine, PluginBinding, binding.id) == binding_before


def test_stale_saves_even_with_a_cached_draft_leave_state_unchanged_and_log_only_ids(
    session: Session,
    engine: Engine,
) -> None:
    reader = a_reader(session)
    parent = create_plugin(session, reader.id, "own")
    draft = create_draft(session, reader.id, parent.plugin_id, parent.id)
    session.commit()
    ids = reader.id, parent.plugin_id, draft.id
    with Session(engine) as first, Session(engine) as second:
        cached = get_draft(first, *ids)
        first.commit()
        save_draft(second, *ids, 1, "saved", {"a.py": "saved"})
        second.commit()
        with capture_logs() as logs, pytest.raises(DraftConflict):
            save_draft(first, *ids, 1, "SENSITIVE_MANIFEST", {"x.py": "SENSITIVE_CODE"})
        assert not first.dirty and not first.new
        assert cached.version == 2 and cached.manifest == "saved"
        assert logs == [
            {
                "event": "plugin_draft.conflict",
                "log_level": "info",
                "reader_id": str(ids[0]),
                "plugin_id": str(ids[1]),
                "draft_id": str(ids[2]),
                "operation": "save",
                "expected_version": 1,
                "actual_version": 2,
                "reason": "stale_version",
            }
        ]
        first.commit()
    with Session(engine) as outside:
        assert get_draft(outside, *ids).manifest == "saved"


@pytest.mark.parametrize("operation", ["save", "delete"])
@pytest.mark.parametrize("target", ["foreign", "wrong_plugin", "unknown"])
def test_rejected_save_and_delete_preserve_state_before_rollback_and_after_commit(
    session: Session,
    engine: Engine,
    operation: str,
    target: str,
) -> None:
    reader, other = a_reader(session), a_reader(session, "other")
    parent = create_plugin(session, reader.id, "own")
    wrong = create_plugin(session, reader.id, "wrong")
    draft = create_draft(session, reader.id, parent.plugin_id, parent.id)
    session.commit()
    before = stored_columns(engine, PluginDraft, draft.id)
    actor = other.id if target == "foreign" else reader.id
    plugin_id = wrong.plugin_id if target == "wrong_plugin" else parent.plugin_id
    draft_id = uuid.uuid7() if target == "unknown" else draft.id
    with pytest.raises(DraftNotFound):
        if operation == "save":
            save_draft(session, actor, plugin_id, draft_id, 1, "bad", {})
        else:
            delete_draft(session, actor, plugin_id, draft_id)
    assert not session.new and not session.dirty and not session.deleted
    session.commit()
    assert stored_columns(engine, PluginDraft, draft.id) == before


def test_discard_deletes_only_that_draft_and_logs_ids(session: Session, engine: Engine) -> None:
    parent, channel = a_bound_channel(session)
    assert parent.reader_id is not None and channel.current_revision is not None
    ids = parent.reader_id, parent.plugin_id
    draft = create_draft(session, *ids, parent.id)
    sibling = create_draft(session, *ids, parent.id)
    session.commit()
    before = stored_columns(engine, PluginRevision, parent.id)
    binding = channel.current_revision.bindings[0]
    binding_before = stored_columns(engine, PluginBinding, binding.id)
    with capture_logs() as logs:
        delete_draft(session, *ids, draft.id)
    assert logs == [
        {
            "event": "plugin_draft.deleted",
            "log_level": "info",
            "reader_id": str(ids[0]),
            "plugin_id": str(ids[1]),
            "draft_id": str(draft.id),
        }
    ]
    with Session(engine) as outside:
        assert outside.get(PluginDraft, draft.id) is not None
    session.commit()
    with Session(engine) as outside:
        assert outside.get(PluginDraft, draft.id) is None
        assert outside.get(PluginDraft, sibling.id) is not None
    assert stored_columns(engine, PluginRevision, parent.id) == before
    assert stored_columns(engine, PluginBinding, binding.id) == binding_before


def test_competing_saves_allow_one_writer_and_refuse_the_other(
    session: Session, engine: Engine
) -> None:
    reader = a_reader(session)
    parent = create_plugin(session, reader.id, "race")
    draft = create_draft(session, reader.id, parent.plugin_id, parent.id)
    session.commit()
    ids = reader.id, parent.plugin_id, draft.id
    start = Barrier(2)

    def save(text: str) -> str:
        with Session(engine) as writer:
            start.wait(timeout=5)
            try:
                save_draft(writer, *ids, 1, text, {"main.py": text})
                writer.commit()
                return text
            except DraftConflict:
                writer.rollback()
                return "conflict"

    with capture_logs() as logs, ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(save, ["first", "second"]))
    assert results.count("conflict") == 1
    conflicts = [log for log in logs if log["event"] == "plugin_draft.conflict"]
    assert [(log["reason"], log["expected_version"]) for log in conflicts] == [("stale_version", 1)]
    winner = next(text for text in results if text != "conflict")
    with Session(engine) as outside:
        stored = get_draft(outside, *ids)
        assert (
            stored.version == 2 and stored.manifest == winner and stored.code == {"main.py": winner}
        )
