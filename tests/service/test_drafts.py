import uuid

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from news.service.drafts import (
    DraftNotFound,
    create_draft,
    get_draft,
    list_drafts,
    parent_is_eligible,
)
from news.service.models import Plugin, PluginDraft, PluginRevision
from news.service.plugins import create_plugin
from news.service.validation import ValidationRejected
from tests.service.factories import a_built_in_plugin_revision, a_reader


@pytest.mark.parametrize(
    "parent_owner,parent_plugin,allowed",
    [
        ("own", "same", True),
        ("own", "other", False),
        ("other", "same", False),
        ("system", "same", False),
    ],
)
def test_parent_eligibility_is_same_reader_and_plugin(
    parent_owner: str,
    parent_plugin: str,
    allowed: bool,
) -> None:
    reader, plugin = uuid.uuid7(), uuid.uuid7()
    owner = {"own": reader, "other": uuid.uuid7(), "system": None}[parent_owner]
    assert (
        parent_is_eligible(
            reader, plugin, owner, plugin if parent_plugin == "same" else uuid.uuid7()
        )
        is allowed
    )


def test_sibling_drafts_copy_an_older_parent_independently(
    session: Session, engine: Engine
) -> None:
    reader = a_reader(session)
    parent = create_plugin(session, reader.id, "experiments")
    plugin = session.get_one(Plugin, parent.plugin_id)
    latest = PluginRevision(
        id=uuid.uuid7(),
        plugin_id=plugin.id,
        reader_id=reader.id,
        number=2,
        parent_revision_id=parent.id,
        manifest="newer",
        code={"new.py": "newer"},
        created_by=str(reader.id),
    )
    session.add(latest)
    plugin.current_revision = latest
    session.commit()

    assert list_drafts(session, reader.id, plugin.id) == []
    first = create_draft(session, reader.id, plugin.id, parent.id)
    second = create_draft(session, reader.id, plugin.id, parent.id)
    assert first.id != second.id
    assert first.code == second.code == parent.code
    assert first.code is not second.code and first.code is not parent.code
    assert first.manifest == second.manifest == parent.manifest
    assert first.parent_revision_id == second.parent_revision_id == parent.id
    assert first.reader_id == second.reader_id == reader.id
    assert first.plugin_id == second.plugin_id == plugin.id
    assert first.version == second.version == 1
    ids = [first.id, second.id]
    # Services flush, but do not commit.
    with Session(engine) as outside:
        assert outside.scalar(select(func.count()).select_from(PluginDraft)) == 0
    session.commit()
    with Session(engine) as outside:
        assert [draft.id for draft in list_drafts(outside, reader.id, plugin.id)] == ids
        assert get_draft(outside, reader.id, plugin.id, first.id).code == parent.code
        assert outside.get_one(Plugin, plugin.id).current_revision_id == latest.id


@pytest.mark.parametrize(
    "target",
    [
        "unknown_plugin",
        "foreign_plugin",
        "builtin",
        "unknown_parent",
        "wrong_plugin",
        "foreign_parent",
    ],
)
def test_bad_targets_insert_nothing_before_rollback(
    session: Session,
    engine: Engine,
    target: str,
) -> None:
    reader, other = a_reader(session), a_reader(session, "other")
    parent = create_plugin(session, reader.id, "own")
    same_reader_other = create_plugin(session, reader.id, "other")
    foreign = create_plugin(session, other.id, "foreign")
    builtin = a_built_in_plugin_revision(session)
    plugin_id, parent_id = {
        "unknown_plugin": (uuid.uuid7(), parent.id),
        "foreign_plugin": (foreign.plugin_id, foreign.id),
        "builtin": (builtin.plugin_id, builtin.id),
        "unknown_parent": (parent.plugin_id, uuid.uuid7()),
        "wrong_plugin": (parent.plugin_id, same_reader_other.id),
        "foreign_parent": (parent.plugin_id, foreign.id),
    }[target]
    session.commit()
    with capture_logs() as logs, pytest.raises((DraftNotFound, ValidationRejected)):
        create_draft(session, reader.id, plugin_id, parent_id)
    assert not session.new and not session.dirty
    assert session.scalar(select(func.count()).select_from(PluginDraft)) == 0
    assert len(logs) == 1 and logs[0]["log_level"] == "info"
    session.commit()
    with Session(engine) as outside:
        assert outside.scalar(select(func.count()).select_from(PluginDraft)) == 0


def test_unknown_and_foreign_reads_and_lists_are_indistinguishable(session: Session) -> None:
    reader, other = a_reader(session), a_reader(session, "other")
    parent = create_plugin(session, reader.id, "own")
    draft = create_draft(session, reader.id, parent.plugin_id, parent.id)
    wrong = create_plugin(session, reader.id, "wrong")
    session.commit()
    messages: list[str] = []
    for actor, plugin_id, draft_id in [
        (other.id, parent.plugin_id, draft.id),
        (reader.id, wrong.plugin_id, draft.id),
        (reader.id, parent.plugin_id, uuid.uuid7()),
    ]:
        with pytest.raises(DraftNotFound) as raised:
            get_draft(session, actor, plugin_id, draft_id)
        messages.append(str(raised.value))
    assert len(set(messages)) == 1
    with pytest.raises(DraftNotFound):
        list_drafts(session, other.id, parent.plugin_id)
    with pytest.raises(DraftNotFound):
        list_drafts(session, uuid.uuid7(), parent.plugin_id)
    assert list_drafts(session, reader.id, wrong.plugin_id) == []
