"""Plugins and their immutable Plugin Revisions (ADR 0018)."""

import uuid

import structlog
from sqlalchemy.orm import Session

from news.service.models import Plugin, PluginRevision
from news.service.readers import require_reader
from news.service.revisions import creator_of, next_revision_number
from news.service.validation import FieldError, ValidationRejected

log = structlog.get_logger(__name__)


def create_plugin(session: Session, reader_id: uuid.UUID, name: str) -> PluginRevision:
    """Create a Reader-owned Plugin with a valid, current no-op starter Revision 1."""
    require_reader(session, reader_id)
    if not name.strip():
        log.info("plugin.rejected", reader_id=str(reader_id), fields=["name"])
        raise ValidationRejected([FieldError("name", "must not be blank")])
    manifest = (
        f"name = {_toml_string(name)}\n"
        'command = "python main.py"\ntimeout = 60\n\n'
        '[config_schema]\ntype = "object"\nadditionalProperties = false\n'
    )
    plugin = Plugin(id=uuid.uuid7(), reader_id=reader_id, name=name)
    revision = PluginRevision(
        id=uuid.uuid7(),
        plugin_id=plugin.id,
        reader_id=reader_id,
        number=next_revision_number(None),
        manifest=manifest,
        code={"main.py": '# /// script\n# dependencies = []\n# ///\n\n"""Emit no News Items."""\n'},
        created_by=creator_of(reader_id),
    )
    session.add_all([plugin, revision])
    plugin.current_revision = revision
    session.flush()
    return revision


def _toml_string(value: str) -> str:
    # TOML basic strings forbid raw control characters, DEL included; JSON escaping misses DEL.
    escaped = "".join(
        f"\\u{ord(char):04X}" if ord(char) < 0x20 or char == "\x7f" else char
        for char in value.replace("\\", "\\\\").replace('"', '\\"')
    )
    return f'"{escaped}"'
