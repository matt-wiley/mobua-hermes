"""Plugins and their immutable Plugin Revisions (ADR 0018)."""

import uuid
from dataclasses import asdict

import structlog
from sqlalchemy.orm import Session

from news.service.manifest import PluginRevisionRejected, parse_manifest
from news.service.models import Plugin, PluginRevision
from news.service.readers import require_reader
from news.service.revisions import creator_of, next_revision_number

log = structlog.get_logger(__name__)


def create_plugin(
    session: Session, reader_id: uuid.UUID, manifest: str, code: dict[str, str]
) -> PluginRevision:
    """Create a Reader-owned Plugin with its first Revision.

    Raises ReaderNotFound for an unknown Reader, or PluginRevisionRejected if the Manifest is
    invalid, creating nothing in either case.
    """
    require_reader(session, reader_id)
    try:
        parsed = parse_manifest(manifest)
    except PluginRevisionRejected as rejected:
        log.info(
            "plugin_revision.rejected",
            reader_id=str(reader_id),
            errors=[asdict(error) for error in rejected.errors],
        )
        raise
    plugin = Plugin(id=uuid.uuid7(), reader_id=reader_id, name=parsed.name)
    revision = PluginRevision(
        id=uuid.uuid7(),
        plugin_id=plugin.id,
        reader_id=reader_id,
        number=next_revision_number(None),
        manifest=manifest,
        code=code,
        created_by=creator_of(reader_id),
    )
    session.add_all([plugin, revision])
    plugin.current_revision = revision
    session.flush()
    return revision
