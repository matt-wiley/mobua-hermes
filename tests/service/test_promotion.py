"""Promoting saved Drafts into permanent, current Plugin Revisions (AC-65, AC-66, AC-81)."""

import uuid
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, event, select, text
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from news.service.channels import bind_plugin, create_channel
from news.service.db import create_engine_for
from news.service.drafts import (
    DraftConflict,
    DraftNotFound,
    create_draft,
    promote_draft,
    save_draft,
)
from news.service.manifest import PluginRevisionRejected
from news.service.models import Plugin, PluginBinding, PluginDraft, PluginRevision
from news.service.plugins import create_plugin
from news.service.revision_history import CurrentSelectionConflict, select_current_revision
from tests.db_failures import fail_commits_on
from tests.service.factories import a_reader

SENSITIVE = "SENSITIVE_SOURCE_sk-live-sentinel"
UNPINNED = "# /// script\n# dependencies = ['feedparser>=6']\n# ///\n"


class Lifecycle:
    """A Reader-owned Plugin at its starter, bound into a Channel, with one fresh Draft."""

    def __init__(self, session: Session) -> None:
        reader = a_reader(session)
        self.reader_id = reader.id
        self.starter = create_plugin(session, reader.id, "Experiments")
        self.plugin_id = self.starter.plugin_id
        channel = create_channel(session, reader.id, "Local news")
        bind_plugin(session, reader.id, channel.id, self.starter.id, {})
        self.draft = self.new_draft(session, self.starter.id)
        session.commit()

    def new_draft(self, session: Session, parent_id: uuid.UUID) -> PluginDraft:
        return create_draft(session, self.reader_id, self.plugin_id, parent_id)

    def save(
        self, session: Session, draft: PluginDraft, manifest: str, code: dict[str, str]
    ) -> PluginDraft:
        return save_draft(
            session,
            self.reader_id,
            self.plugin_id,
            draft.id,
            draft.version,
            manifest,
            code,
        )

    def promote(
        self,
        session: Session,
        draft: PluginDraft,
        version: int | None = None,
        confirm: uuid.UUID | None = None,
    ) -> PluginRevision:
        return promote_draft(
            session,
            self.reader_id,
            self.plugin_id,
            draft.id,
            draft.version if version is None else version,
            confirm,
        )


@pytest.fixture
def lifecycle(session: Session) -> Lifecycle:
    return Lifecycle(session)


def state(session: Session) -> dict[str, Any]:
    """Every row promotion may touch, read through the given Session (pending changes too)."""
    fresh = {"populate_existing": True}
    return {
        "drafts": sorted(
            (d.id, d.version, d.manifest, tuple(sorted(d.code.items())))
            for d in session.scalars(select(PluginDraft).execution_options(**fresh))
        ),
        "revisions": sorted(
            (r.id, r.number, r.parent_revision_id, r.manifest, tuple(sorted(r.code.items())))
            for r in session.scalars(select(PluginRevision).execution_options(**fresh))
        ),
        "current": [
            (p.id, p.current_revision_id)
            for p in session.scalars(select(Plugin).execution_options(**fresh))
        ],
        "bindings": sorted(
            (b.id, b.plugin_revision_id, str(b.config))
            for b in session.scalars(select(PluginBinding).execution_options(**fresh))
        ),
    }


def committed_state(engine: Engine) -> dict[str, Any]:
    with Session(engine) as fresh:
        return state(fresh)


def test_promotion_creates_the_current_reader_created_revision_and_deletes_only_that_draft(
    engine: Engine, session: Session, lifecycle: Lifecycle
) -> None:
    sibling = lifecycle.new_draft(session, lifecycle.starter.id)
    code = {"main.py": "# /// script\n# dependencies = ['feedparser==6.0.11']\n# ///\n"}
    draft = lifecycle.save(session, lifecycle.draft, lifecycle.starter.manifest, code)
    session.commit()
    bindings_before = committed_state(engine)["bindings"]

    with capture_logs() as logs:
        revision = lifecycle.promote(session, draft)
    session.commit()

    assert revision.number == 2
    assert revision.parent_revision_id == lifecycle.starter.id
    assert revision.created_by == str(lifecycle.reader_id)
    assert (revision.manifest, revision.code) == (lifecycle.starter.manifest, code)
    after = committed_state(engine)
    assert after["current"] == [(lifecycle.plugin_id, revision.id)]
    assert [row[0] for row in after["drafts"]] == [sibling.id]
    assert after["bindings"] == bindings_before
    assert logs == [
        {
            "event": "plugin_draft.promoted",
            "log_level": "info",
            "reader_id": str(lifecycle.reader_id),
            "plugin_id": str(lifecycle.plugin_id),
            "draft_id": str(draft.id),
            "parent_revision_id": str(lifecycle.starter.id),
            "revision_id": str(revision.id),
        }
    ]


def test_promotion_is_flushed_but_not_committed_by_the_service(
    engine: Engine, session: Session, lifecycle: Lifecycle
) -> None:
    before = committed_state(engine)

    lifecycle.promote(session, lifecycle.draft)

    assert committed_state(engine) == before


@pytest.mark.parametrize(
    "manifest,code,fields",
    [
        ('name = "unfinished', {"main.py": ""}, ["manifest"]),
        (None, {"main.py": UNPINNED}, ["code[main.py].dependencies.0"]),
        (
            'name = ""\ncommand = "python main.py"\ntimeout = 60\nconfig_schema = {}\n',
            {"main.py": UNPINNED},
            ["manifest.name", "code[main.py].dependencies.0"],
        ),
    ],
    ids=["invalid-toml", "unpinned", "both"],
)
def test_an_invalid_draft_is_rejected_with_field_errors_and_nothing_changes(
    engine: Engine,
    session: Session,
    lifecycle: Lifecycle,
    manifest: str | None,
    code: dict[str, str],
    fields: list[str],
) -> None:
    draft = lifecycle.save(
        session, lifecycle.draft, manifest or lifecycle.starter.manifest, code | {"x": SENSITIVE}
    )
    session.commit()
    before = committed_state(engine)

    with capture_logs() as logs, pytest.raises(PluginRevisionRejected) as raised:
        lifecycle.promote(session, draft)

    assert [error.field for error in raised.value.errors] == fields
    assert state(session) == before
    session.rollback()
    assert committed_state(engine) == before
    assert logs == [
        {
            "event": "plugin_draft.rejected",
            "log_level": "info",
            "reader_id": str(lifecycle.reader_id),
            "plugin_id": str(lifecycle.plugin_id),
            "draft_id": str(draft.id),
            "reason": "invalid_implementation",
            "fields": fields,
        }
    ]
    assert SENSITIVE not in str(logs)


@pytest.mark.parametrize("version", [1, 3], ids=["stale", "future"])
def test_a_stale_expected_version_is_a_conflict_and_nothing_changes(
    engine: Engine, session: Session, lifecycle: Lifecycle, version: int
) -> None:
    lifecycle.save(session, lifecycle.draft, lifecycle.starter.manifest, {"main.py": SENSITIVE})
    session.commit()
    before = committed_state(engine)

    with capture_logs() as logs, pytest.raises(DraftConflict) as raised:
        lifecycle.promote(session, lifecycle.draft, version=version)

    assert (raised.value.expected, raised.value.actual) == (version, 2)
    assert state(session) == before
    session.rollback()
    assert committed_state(engine) == before
    assert logs == [
        {
            "event": "plugin_draft.conflict",
            "log_level": "info",
            "reader_id": str(lifecycle.reader_id),
            "plugin_id": str(lifecycle.plugin_id),
            "draft_id": str(lifecycle.draft.id),
            "operation": "promote",
            "expected_version": version,
            "actual_version": 2,
            "reason": "stale_version",
        }
    ]


def test_version_is_checked_before_validation(session: Session, lifecycle: Lifecycle) -> None:
    lifecycle.save(session, lifecycle.draft, "invalid", {})

    with pytest.raises(DraftConflict):
        lifecycle.promote(session, lifecycle.draft, version=1)


def test_unknown_and_foreign_drafts_are_not_found_without_changes(
    engine: Engine, session: Session, lifecycle: Lifecycle
) -> None:
    other = a_reader(session, "Other")
    session.commit()
    before = committed_state(engine)

    for reader_id, draft_id in [
        (other.id, lifecycle.draft.id),
        (lifecycle.reader_id, uuid.uuid7()),
    ]:
        with pytest.raises(DraftNotFound):
            promote_draft(session, reader_id, lifecycle.plugin_id, draft_id, 1)
        assert state(session) == before


def test_a_failed_commit_leaves_the_draft_revisions_pointer_and_bindings(
    engine: Engine, session: Session, lifecycle: Lifecycle
) -> None:
    before = committed_state(engine)
    fail_commits_on(engine, "plugin_draft", "DELETE")

    lifecycle.promote(session, lifecycle.draft)
    with pytest.raises(Exception, match="FOREIGN KEY"):
        session.commit()

    session.rollback()
    assert committed_state(engine) == before


def test_sibling_drafts_promote_to_distinct_revisions_sharing_their_parent(
    engine: Engine, session: Session, lifecycle: Lifecycle
) -> None:
    second = lifecycle.new_draft(session, lifecycle.starter.id)
    third = lifecycle.new_draft(session, lifecycle.starter.id)
    session.commit()

    first_revision = lifecycle.promote(session, lifecycle.draft)
    session.commit()
    second_revision = lifecycle.promote(session, second, confirm=first_revision.id)
    session.commit()

    assert (first_revision.number, second_revision.number) == (2, 3)
    assert first_revision.parent_revision_id == second_revision.parent_revision_id
    assert second_revision.parent_revision_id == lifecycle.starter.id
    saved = lifecycle.save(session, third, "still editable", {})
    session.commit()
    assert saved.version == 2
    assert committed_state(engine)["current"] == [(lifecycle.plugin_id, second_revision.id)]


def test_an_older_parent_draft_needs_confirmation_of_the_current_selection(
    engine: Engine, session: Session, lifecycle: Lifecycle
) -> None:
    older = lifecycle.save(session, lifecycle.draft, lifecycle.starter.manifest, {"main.py": "a"})
    newer = lifecycle.promote(session, lifecycle.new_draft(session, lifecycle.starter.id))
    session.commit()
    before = committed_state(engine)

    with capture_logs() as logs, pytest.raises(CurrentSelectionConflict) as raised:
        lifecycle.promote(session, older)

    assert raised.value.reason == "confirmation_required"
    assert (raised.value.expected, raised.value.actual) == (None, newer.id)
    assert state(session) == before
    session.rollback()
    assert logs == [
        {
            "event": "plugin_draft.conflict",
            "log_level": "info",
            "reader_id": str(lifecycle.reader_id),
            "plugin_id": str(lifecycle.plugin_id),
            "draft_id": str(older.id),
            "operation": "promote",
            "expected_current_revision_id": None,
            "actual_current_revision_id": str(newer.id),
            "reason": "confirmation_required",
        }
    ]

    replacement = lifecycle.promote(session, older, confirm=newer.id)
    session.commit()

    assert replacement.parent_revision_id == lifecycle.starter.id
    assert replacement.code == {"main.py": "a"}, "copied as-is, never merged with the current"
    assert committed_state(engine)["current"] == [(lifecycle.plugin_id, replacement.id)]


def test_a_changed_current_selection_requires_reconfirmation(
    engine: Engine, session: Session, lifecycle: Lifecycle
) -> None:
    newer = lifecycle.promote(session, lifecycle.new_draft(session, lifecycle.starter.id))
    session.commit()
    select_current_revision(
        session, lifecycle.reader_id, lifecycle.plugin_id, lifecycle.starter.id, newer.id
    )
    session.commit()
    before = committed_state(engine)

    with pytest.raises(CurrentSelectionConflict) as raised:
        lifecycle.promote(session, lifecycle.draft, confirm=newer.id)

    assert raised.value.reason == "stale_current_selection"
    assert (raised.value.expected, raised.value.actual) == (newer.id, lifecycle.starter.id)
    assert state(session) == before


def test_numbers_come_from_the_whole_history_after_a_current_pointer_rollback(
    session: Session, lifecycle: Lifecycle
) -> None:
    second = lifecycle.promote(session, lifecycle.draft)
    third = lifecycle.promote(session, lifecycle.new_draft(session, second.id))
    select_current_revision(
        session, lifecycle.reader_id, lifecycle.plugin_id, lifecycle.starter.id, third.id
    )

    fourth = lifecycle.promote(session, lifecycle.new_draft(session, lifecycle.starter.id))

    assert [second.number, third.number, fourth.number] == [2, 3, 4]
    assert third.parent_revision_id == second.id
    assert fourth.parent_revision_id == lifecycle.starter.id


@contextmanager
def concurrent_write_before(
    engine: Engine, statement_prefix: str, write: Callable[[Connection], None]
) -> Generator[None]:
    """Commit `write` on another connection just before this engine runs the given statement."""
    other = create_engine_for(str(engine.url))
    fired = False

    def interleave(_conn: Any, _cursor: Any, statement: str, *_args: Any) -> None:
        nonlocal fired
        if not fired and statement.startswith(statement_prefix):
            fired = True
            with other.begin() as connection:
                write(connection)

    event.listen(engine, "before_cursor_execute", interleave)
    try:
        yield
    finally:
        event.remove(engine, "before_cursor_execute", interleave)
        other.dispose()
    assert fired


def test_a_pointer_change_racing_the_promotion_is_a_conflict_after_rollback(
    engine: Engine, session: Session, lifecycle: Lifecycle
) -> None:
    newer = lifecycle.promote(session, lifecycle.new_draft(session, lifecycle.starter.id))
    select_current_revision(
        session, lifecycle.reader_id, lifecycle.plugin_id, lifecycle.starter.id, newer.id
    )
    session.commit()

    def select_newer(connection: Connection) -> None:
        connection.execute(
            text("UPDATE plugin SET current_revision_id = :id"), {"id": newer.id.hex}
        )

    with (
        concurrent_write_before(engine, "INSERT INTO plugin_revision", select_newer),
        pytest.raises(CurrentSelectionConflict) as raised,
    ):
        lifecycle.promote(session, lifecycle.draft)

    assert raised.value.reason == "stale_current_selection"
    assert raised.value.actual == newer.id
    session.rollback()
    after = committed_state(engine)
    assert after["current"] == [(lifecycle.plugin_id, newer.id)]
    assert lifecycle.draft.id in [row[0] for row in after["drafts"]]
    assert len(after["revisions"]) == 2


def test_a_save_racing_the_promotion_is_a_conflict_after_rollback(
    engine: Engine, session: Session, lifecycle: Lifecycle
) -> None:
    def save_elsewhere(connection: Connection) -> None:
        connection.execute(
            text("UPDATE plugin_draft SET version = 2, manifest = 'raced' WHERE id = :id"),
            {"id": lifecycle.draft.id.hex},
        )

    with (
        concurrent_write_before(engine, "INSERT INTO plugin_revision", save_elsewhere),
        pytest.raises(DraftConflict) as raised,
    ):
        lifecycle.promote(session, lifecycle.draft)

    assert (raised.value.expected, raised.value.actual) == (1, 2)
    session.rollback()
    after = committed_state(engine)
    assert after["current"] == [(lifecycle.plugin_id, lifecycle.starter.id)]
    assert [(row[0], row[1], row[2]) for row in after["drafts"]] == [
        (lifecycle.draft.id, 2, "raced")
    ]
    assert len(after["revisions"]) == 1


def test_promotion_does_not_require_a_successful_test_run(
    session: Session, lifecycle: Lifecycle
) -> None:
    """No Test Run exists yet; promotion depends only on saved contents (AC-69)."""
    assert lifecycle.promote(session, lifecycle.draft).number == 2
