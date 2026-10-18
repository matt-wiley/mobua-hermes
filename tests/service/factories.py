"""Small builders for service-layer tests."""

import uuid

from sqlalchemy.orm import Session

from news.service.manifest import parse_manifest
from news.service.models import Plugin, PluginRevision, Reader
from news.service.readers import create_reader
from news.service.revisions import creator_of

URL_PLUGIN_MANIFEST = """
name = "rss"
command = "python main.py"
timeout = 60

[config_schema]
type = "object"
required = ["url"]
additionalProperties = false

[config_schema.properties.url]
type = "string"
"""

OPEN_PLUGIN_MANIFEST = """
name = "scraper"
command = "python main.py"
timeout = 60

[config_schema]
type = "object"
"""


def a_reader(session: Session, name: str = "Ada") -> Reader:
    return create_reader(session, name)


def a_plugin_revision(
    session: Session, reader: Reader, manifest: str = URL_PLUGIN_MANIFEST
) -> PluginRevision:
    """A pre-Draft implementation fixture; promotion belongs to ticket 04."""
    plugin = Plugin(id=uuid.uuid7(), reader_id=reader.id, name=parse_manifest(manifest).name)
    revision = PluginRevision(
        id=uuid.uuid7(),
        plugin_id=plugin.id,
        reader_id=reader.id,
        number=1,
        manifest=manifest,
        code={"main.py": "print('hi')"},
        created_by=str(reader.id),
    )
    session.add_all([plugin, revision])
    plugin.current_revision = revision
    session.flush()
    return revision


def a_built_in_plugin_revision(session: Session) -> PluginRevision:
    """A system-owned Plugin Revision with no Reader id; seeding itself is ticket 05."""
    plugin = Plugin(id=uuid.uuid7(), reader_id=None, name="rss")
    revision = PluginRevision(
        id=uuid.uuid7(),
        plugin_id=plugin.id,
        reader_id=None,
        number=1,
        manifest=URL_PLUGIN_MANIFEST,
        code={"main.py": ""},
        created_by=creator_of(None),
    )
    session.add_all([plugin, revision])
    plugin.current_revision = revision
    session.flush()
    return revision
