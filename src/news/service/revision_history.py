"""A Reader-owned Plugin's permanent Revision tree and its current selection (ADR 0024)."""

import uuid
from typing import Literal, NoReturn

import structlog
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from news.service.models import Plugin, PluginRevision
from news.service.plugin_data import RevisionDetails, RevisionHistory
from news.service.validation import FieldError, ValidationRejected

log = structlog.get_logger(__name__)

type SelectionProblem = Literal["confirmation_required", "stale_current_selection"]


class PluginNotFound(LookupError):
    pass


class CurrentSelectionConflict(ValidationRejected):
    def __init__(
        self, reason: SelectionProblem, expected: uuid.UUID | None, actual: uuid.UUID | None
    ) -> None:
        self.reason = reason
        self.expected = expected
        self.actual = actual
        message = {
            "confirmation_required": (
                f"the current Revision is {actual}, not this Draft's parent; "
                "confirm it to replace that selection"
            ),
            "stale_current_selection": (
                f"expected current Revision {expected}, but it is {actual}; "
                "review the history and confirm again"
            ),
        }[reason]
        super().__init__([FieldError("expected_current_revision_id", message)])


def selection_problem(
    current_id: uuid.UUID | None,
    confirmed_id: uuid.UUID | None,
    *,
    needs_confirmation: bool,
) -> SelectionProblem | None:
    """Why a change to the current selection must not go ahead, if it must not."""
    if confirmed_id is None:
        return "confirmation_required" if needs_confirmation else None
    return None if confirmed_id == current_id else "stale_current_selection"


def list_revisions(session: Session, reader_id: uuid.UUID, plugin_id: uuid.UUID) -> RevisionHistory:
    plugin = require_owned_plugin(session, reader_id, plugin_id)
    revisions = session.scalars(
        select(PluginRevision)
        .where(PluginRevision.plugin_id == plugin.id)
        .order_by(PluginRevision.number)
    )
    return RevisionHistory(
        plugin_id=plugin.id,
        current_revision_id=plugin.current_revision_id,
        revisions=[RevisionDetails.model_validate(revision) for revision in revisions],
    )


def select_current_revision(
    session: Session,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    revision_id: uuid.UUID,
    expected_current_revision_id: uuid.UUID,
) -> Plugin:
    """Make an existing Revision current; no Revision is created and no Binding moves."""
    plugin = require_owned_plugin(session, reader_id, plugin_id)
    target = session.scalar(
        select(PluginRevision.id).where(
            PluginRevision.id == revision_id,
            PluginRevision.plugin_id == plugin.id,
            PluginRevision.reader_id == reader_id,
        )
    )
    if target is None:
        log.info(
            "plugin_revision.selection_rejected",
            reader_id=str(reader_id),
            plugin_id=str(plugin_id),
            fields=["revision_id"],
        )
        raise ValidationRejected([FieldError("revision_id", "no such Plugin Revision")])
    current = plugin.current_revision_id
    problem = selection_problem(current, expected_current_revision_id, needs_confirmation=True)
    if problem is None and move_current_pointer(session, plugin.id, current, target):
        session.flush()
        return plugin
    selection_conflict(
        reader_id,
        plugin_id,
        "select_current",
        problem or "stale_current_selection",
        expected_current_revision_id,
        current_revision_id(session, plugin_id),
    )


def move_current_pointer(
    session: Session,
    plugin_id: uuid.UUID,
    observed: uuid.UUID | None,
    revision_id: uuid.UUID,
) -> bool:
    """Point the Plugin at the Revision unless another writer moved it since it was read."""
    moved = session.scalar(
        update(Plugin)
        .where(Plugin.id == plugin_id, Plugin.current_revision_id.is_not_distinct_from(observed))
        .values(current_revision_id=revision_id)
        .returning(Plugin.id)
    )
    return moved is not None


def current_revision_id(session: Session, plugin_id: uuid.UUID) -> uuid.UUID | None:
    return session.scalar(select(Plugin.current_revision_id).where(Plugin.id == plugin_id))


def selection_conflict(
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    operation: str,
    reason: SelectionProblem,
    expected: uuid.UUID | None,
    actual: uuid.UUID | None,
    draft_id: uuid.UUID | None = None,
) -> NoReturn:
    log.info(
        "plugin_draft.conflict",
        reader_id=str(reader_id),
        plugin_id=str(plugin_id),
        **({"draft_id": str(draft_id)} if draft_id else {}),
        operation=operation,
        expected_current_revision_id=str(expected) if expected else None,
        actual_current_revision_id=str(actual) if actual else None,
        reason=reason,
    )
    raise CurrentSelectionConflict(reason, expected, actual)


def require_owned_plugin(session: Session, reader_id: uuid.UUID, plugin_id: uuid.UUID) -> Plugin:
    plugin = session.scalar(
        select(Plugin)
        .where(Plugin.id == plugin_id, Plugin.reader_id == reader_id)
        .execution_options(populate_existing=True)
    )
    if plugin is None:
        log.info("plugin.not_found", reader_id=str(reader_id), plugin_id=str(plugin_id))
        raise PluginNotFound("no such Reader-owned Plugin")
    return plugin
