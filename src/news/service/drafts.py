"""Saved Reader-owned Plugin Drafts and their promotion (ADR 0024). Services flush; callers commit.

A conflict raised after promotion has written leaves those writes to the caller's rollback,
which every surface performs on any exception.
"""

import uuid
from typing import NoReturn

import structlog
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from news.service.implementation import validate_implementation
from news.service.manifest import PluginRevisionRejected
from news.service.models import Plugin, PluginDraft, PluginRevision
from news.service.revision_history import (
    SelectionProblem,
    current_revision_id,
    move_current_pointer,
    selection_conflict,
    selection_problem,
)
from news.service.revisions import creator_of, next_revision_number
from news.service.validation import FieldError, ValidationRejected
from news.service.workspaces import implementation_files

log = structlog.get_logger(__name__)


class DraftNotFound(LookupError):
    pass


class DraftConflict(ValidationRejected):
    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            [
                FieldError(
                    "version",
                    f"expected {expected}, saved version is {actual}; "
                    "read or export the Draft again before saving",
                )
            ]
        )


def check_version(expected: int, actual: int) -> None:
    if expected != actual:
        raise DraftConflict(expected, actual)


def save_draft(
    session: Session,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID,
    expected_version: int,
    manifest: str,
    code: dict[str, str],
) -> PluginDraft:
    draft = get_draft(session, reader_id, plugin_id, draft_id)
    try:
        check_version(expected_version, draft.version)
    except DraftConflict:
        _conflict(reader_id, plugin_id, draft_id, "save", expected_version, draft.version)
    try:
        implementation_files(manifest, code)
    except ValidationRejected:
        log.info(
            "plugin_draft.save_rejected",
            reader_id=str(reader_id),
            plugin_id=str(plugin_id),
            draft_id=str(draft_id),
            fields=["code"],
        )
        raise
    # A conditional UPDATE also catches a competing writer after the read above. Returning
    # the updated row keeps the Session's identity map consistent without mutating it first.
    saved = session.scalar(
        update(PluginDraft)
        .where(
            PluginDraft.id == draft_id,
            PluginDraft.reader_id == reader_id,
            PluginDraft.plugin_id == plugin_id,
            PluginDraft.version == expected_version,
        )
        .values(manifest=manifest, code=dict(code), version=PluginDraft.version + 1)
        .returning(PluginDraft)
        .execution_options(synchronize_session=False, populate_existing=True)
    )
    if saved is None:
        actual = get_draft(session, reader_id, plugin_id, draft_id).version
        _conflict(reader_id, plugin_id, draft_id, "save", expected_version, actual)
    session.flush()
    return saved


def delete_draft(
    session: Session,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID,
) -> None:
    draft = get_draft(session, reader_id, plugin_id, draft_id)
    session.delete(draft)
    session.flush()
    log.info(
        "plugin_draft.deleted",
        reader_id=str(reader_id),
        plugin_id=str(plugin_id),
        draft_id=str(draft_id),
    )


def _conflict(
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID,
    operation: str,
    expected: int,
    actual: int,
) -> NoReturn:
    log.info(
        "plugin_draft.conflict",
        reader_id=str(reader_id),
        plugin_id=str(plugin_id),
        draft_id=str(draft_id),
        operation=operation,
        expected_version=expected,
        actual_version=actual,
        reason="stale_version",
    )
    raise DraftConflict(expected, actual)


def parent_is_eligible(
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    parent_reader_id: uuid.UUID | None,
    parent_plugin_id: uuid.UUID,
) -> bool:
    return parent_reader_id == reader_id and parent_plugin_id == plugin_id


def create_draft(
    session: Session,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    parent_revision_id: uuid.UUID,
) -> PluginDraft:
    _require_owned_plugin(session, reader_id, plugin_id)
    parent = session.get(PluginRevision, parent_revision_id)
    if parent is None or not parent_is_eligible(
        reader_id, plugin_id, parent.reader_id, parent.plugin_id
    ):
        log.info(
            "plugin_draft.parent_rejected",
            reader_id=str(reader_id),
            plugin_id=str(plugin_id),
            fields=["parent_revision_id"],
        )
        raise ValidationRejected([FieldError("parent_revision_id", "no such Plugin Revision")])
    draft = PluginDraft(
        id=uuid.uuid7(),
        reader_id=reader_id,
        plugin_id=plugin_id,
        parent_revision_id=parent.id,
        version=1,
        manifest=parent.manifest,
        code=dict(parent.code),
    )
    session.add(draft)
    session.flush()
    return draft


def list_drafts(session: Session, reader_id: uuid.UUID, plugin_id: uuid.UUID) -> list[PluginDraft]:
    _require_owned_plugin(session, reader_id, plugin_id)
    return list(
        session.scalars(
            select(PluginDraft)
            .where(
                PluginDraft.reader_id == reader_id,
                PluginDraft.plugin_id == plugin_id,
            )
            .order_by(PluginDraft.id)
            .execution_options(populate_existing=True)
        )
    )


def get_draft(
    session: Session,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID,
) -> PluginDraft:
    _require_owned_plugin(session, reader_id, plugin_id)
    draft = session.scalar(
        select(PluginDraft)
        .where(
            PluginDraft.id == draft_id,
            PluginDraft.reader_id == reader_id,
            PluginDraft.plugin_id == plugin_id,
        )
        .execution_options(populate_existing=True)
    )
    if draft is None:
        _not_found(reader_id, plugin_id, draft_id)
    return draft


def _require_owned_plugin(session: Session, reader_id: uuid.UUID, plugin_id: uuid.UUID) -> None:
    plugin = session.scalar(
        select(Plugin.id).where(
            Plugin.id == plugin_id,
            Plugin.reader_id == reader_id,
        )
    )
    if plugin is None:
        _not_found(reader_id, plugin_id)


def _not_found(
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID | None = None,
) -> NoReturn:
    log.info(
        "plugin_draft.not_found",
        reader_id=str(reader_id),
        plugin_id=str(plugin_id),
        draft_id=str(draft_id) if draft_id else None,
    )
    raise DraftNotFound("no such Reader-owned Plugin or Draft")


def promote_draft(
    session: Session,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID,
    expected_version: int,
    expected_current_revision_id: uuid.UUID | None = None,
) -> PluginRevision:
    """Copy a valid saved Draft into a new current Revision and delete the Draft.

    A Draft whose parent is not the current Revision replaces that selection only when the
    caller confirms it as `expected_current_revision_id`. Bindings never move.
    """
    draft = get_draft(session, reader_id, plugin_id, draft_id)
    try:
        check_version(expected_version, draft.version)
    except DraftConflict:
        _conflict(reader_id, plugin_id, draft_id, "promote", expected_version, draft.version)
    try:
        validate_implementation(draft.manifest, draft.code)
    except PluginRevisionRejected as rejected:
        log.info(
            "plugin_draft.rejected",
            reader_id=str(reader_id),
            plugin_id=str(plugin_id),
            draft_id=str(draft_id),
            reason="invalid_implementation",
            fields=[error.field for error in rejected.errors],
        )
        raise
    current = current_revision_id(session, plugin_id)
    problem = selection_problem(
        current,
        expected_current_revision_id,
        needs_confirmation=draft.parent_revision_id != current,
    )
    if problem is not None:
        _selection_conflict(draft, problem, expected_current_revision_id, current)

    # Numbered from the whole history: the current Revision may be an older one.
    latest = session.scalar(
        select(func.max(PluginRevision.number)).where(PluginRevision.plugin_id == plugin_id)
    )
    revision = PluginRevision(
        id=uuid.uuid7(),
        plugin_id=plugin_id,
        reader_id=reader_id,
        number=next_revision_number(latest),
        parent_revision_id=draft.parent_revision_id,
        manifest=draft.manifest,
        code=dict(draft.code),
        created_by=creator_of(reader_id),
    )
    session.add(revision)
    session.flush()
    # Conditional writes catch a competing writer that changed either row after the reads above.
    if not move_current_pointer(session, plugin_id, current, revision.id):
        _selection_conflict(
            draft,
            "stale_current_selection",
            expected_current_revision_id,
            current_revision_id(session, plugin_id),
        )
    deleted = session.scalar(
        delete(PluginDraft)
        .where(PluginDraft.id == draft_id, PluginDraft.version == expected_version)
        .returning(PluginDraft.id)
    )
    if deleted is None:
        actual = get_draft(session, reader_id, plugin_id, draft_id).version
        _conflict(reader_id, plugin_id, draft_id, "promote", expected_version, actual)
    session.flush()
    log.info(
        "plugin_draft.promoted",
        reader_id=str(reader_id),
        plugin_id=str(plugin_id),
        draft_id=str(draft_id),
        parent_revision_id=str(draft.parent_revision_id),
        revision_id=str(revision.id),
    )
    return revision


def _selection_conflict(
    draft: PluginDraft,
    problem: SelectionProblem,
    expected: uuid.UUID | None,
    actual: uuid.UUID | None,
) -> NoReturn:
    selection_conflict(
        draft.reader_id, draft.plugin_id, "promote", problem, expected, actual, draft.id
    )
