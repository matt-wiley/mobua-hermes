"""The permanent Revision tree and current selection of Reader-owned Plugins (AC-67)."""

import uuid

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from news.service.drafts import create_draft, promote_draft
from news.service.models import Plugin, PluginRevision
from news.service.plugins import create_plugin
from news.service.revision_history import (
    CurrentSelectionConflict,
    PluginNotFound,
    list_revisions,
    select_current_revision,
    selection_problem,
)
from news.service.validation import ValidationRejected
from tests.service.factories import a_built_in_plugin_revision, a_reader
from tests.service.test_promotion import Lifecycle, committed_state

A, B = uuid.uuid7(), uuid.uuid7()


@pytest.mark.parametrize(
    "current,confirmed,needs_confirmation,problem",
    [
        (A, None, False, None),
        (A, A, False, None),
        (A, B, False, "stale_current_selection"),
        (A, None, True, "confirmation_required"),
        (A, A, True, None),
        (A, B, True, "stale_current_selection"),
        (None, A, True, "stale_current_selection"),
    ],
)
def test_selection_problem(
    current: uuid.UUID | None,
    confirmed: uuid.UUID | None,
    needs_confirmation: bool,
    problem: str | None,
) -> None:
    assert selection_problem(current, confirmed, needs_confirmation=needs_confirmation) == problem


@pytest.fixture
def lifecycle(session: Session) -> Lifecycle:
    return Lifecycle(session)


def promote_from(session: Session, lifecycle: Lifecycle, parent_id: uuid.UUID) -> PluginRevision:
    draft = create_draft(session, lifecycle.reader_id, lifecycle.plugin_id, parent_id)
    current = session.get_one(Plugin, lifecycle.plugin_id).current_revision_id
    return promote_draft(
        session, lifecycle.reader_id, lifecycle.plugin_id, draft.id, draft.version, current
    )


def test_history_lists_the_whole_tree_in_number_order_with_the_current_selection(
    session: Session, lifecycle: Lifecycle
) -> None:
    second = promote_from(session, lifecycle, lifecycle.starter.id)
    third = promote_from(session, lifecycle, lifecycle.starter.id)
    fourth = promote_from(session, lifecycle, second.id)
    session.commit()

    history = list_revisions(session, lifecycle.reader_id, lifecycle.plugin_id)

    assert history.plugin_id == lifecycle.plugin_id
    assert history.current_revision_id == fourth.id
    assert [(r.number, r.parent_revision_id) for r in history.revisions] == [
        (1, None),
        (2, lifecycle.starter.id),
        (3, lifecycle.starter.id),
        (4, second.id),
    ]
    assert [r.id for r in history.revisions] == [
        lifecycle.starter.id,
        second.id,
        third.id,
        fourth.id,
    ]
    assert history.revisions[0].manifest == lifecycle.starter.manifest
    assert history.revisions[0].code == lifecycle.starter.code
    assert history.revisions[0].created_by == str(lifecycle.reader_id)
    assert all(revision.created_at.tzinfo is not None for revision in history.revisions)


def test_selecting_an_older_revision_creates_nothing_and_moves_no_bindings(
    engine: Engine, session: Session, lifecycle: Lifecycle
) -> None:
    newer = promote_from(session, lifecycle, lifecycle.starter.id)
    session.commit()
    before = committed_state(engine)

    plugin = select_current_revision(
        session, lifecycle.reader_id, lifecycle.plugin_id, lifecycle.starter.id, newer.id
    )
    session.commit()

    assert plugin.current_revision_id == lifecycle.starter.id
    after = committed_state(engine)
    assert after["current"] == [(lifecycle.plugin_id, lifecycle.starter.id)]
    assert {k: v for k, v in after.items() if k != "current"} == {
        k: v for k, v in before.items() if k != "current"
    }


def test_selecting_the_current_revision_again_is_allowed(
    session: Session, lifecycle: Lifecycle
) -> None:
    plugin = select_current_revision(
        session,
        lifecycle.reader_id,
        lifecycle.plugin_id,
        lifecycle.starter.id,
        lifecycle.starter.id,
    )

    assert plugin.current_revision_id == lifecycle.starter.id


def test_a_stale_confirmation_is_a_logged_conflict_without_changes(
    engine: Engine, session: Session, lifecycle: Lifecycle
) -> None:
    newer = promote_from(session, lifecycle, lifecycle.starter.id)
    session.commit()
    before = committed_state(engine)

    with capture_logs() as logs, pytest.raises(CurrentSelectionConflict) as raised:
        select_current_revision(
            session,
            lifecycle.reader_id,
            lifecycle.plugin_id,
            lifecycle.starter.id,
            lifecycle.starter.id,
        )

    assert (raised.value.expected, raised.value.actual) == (lifecycle.starter.id, newer.id)
    session.rollback()
    assert committed_state(engine) == before
    assert logs == [
        {
            "event": "plugin_draft.conflict",
            "log_level": "info",
            "reader_id": str(lifecycle.reader_id),
            "plugin_id": str(lifecycle.plugin_id),
            "operation": "select_current",
            "expected_current_revision_id": str(lifecycle.starter.id),
            "actual_current_revision_id": str(newer.id),
            "reason": "stale_current_selection",
        }
    ]


@pytest.mark.parametrize("target", ["unknown", "other_plugin", "foreign", "builtin"])
def test_revisions_outside_the_plugin_cannot_be_selected(
    engine: Engine, session: Session, lifecycle: Lifecycle, target: str
) -> None:
    other_plugin = create_plugin(session, lifecycle.reader_id, "Other")
    foreign = create_plugin(session, a_reader(session, "Mallory").id, "Theirs")
    builtin = a_built_in_plugin_revision(session)
    session.commit()
    revision_id = {
        "unknown": uuid.uuid7(),
        "other_plugin": other_plugin.id,
        "foreign": foreign.id,
        "builtin": builtin.id,
    }[target]
    before = committed_state(engine)

    with capture_logs() as logs, pytest.raises(ValidationRejected) as raised:
        select_current_revision(
            session, lifecycle.reader_id, lifecycle.plugin_id, revision_id, lifecycle.starter.id
        )

    assert [error.field for error in raised.value.errors] == ["revision_id"]
    assert committed_state(engine) == before
    assert [log["event"] for log in logs] == ["plugin_revision.selection_rejected"]


@pytest.mark.parametrize("target", ["foreign", "builtin", "unknown"])
def test_only_the_readers_own_plugins_have_history_or_selection(
    session: Session, lifecycle: Lifecycle, target: str
) -> None:
    other = a_reader(session, "Mallory")
    builtin = a_built_in_plugin_revision(session)
    session.commit()
    reader_id, plugin_id, revision_id = {
        "foreign": (other.id, lifecycle.plugin_id, lifecycle.starter.id),
        "builtin": (lifecycle.reader_id, builtin.plugin_id, builtin.id),
        "unknown": (lifecycle.reader_id, uuid.uuid7(), lifecycle.starter.id),
    }[target]

    with pytest.raises(PluginNotFound):
        list_revisions(session, reader_id, plugin_id)
    with pytest.raises(PluginNotFound):
        select_current_revision(session, reader_id, plugin_id, revision_id, revision_id)

    session.expire_all()
    assert session.scalar(select(func.count()).select_from(PluginRevision)) == 2
    assert session.get_one(Plugin, builtin.plugin_id).current_revision_id == builtin.id
