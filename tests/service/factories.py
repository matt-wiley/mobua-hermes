"""Small builders for service-layer tests."""

from sqlalchemy.orm import Session

from news.service.models import PluginRevision, Reader
from news.service.plugins import create_plugin
from news.service.readers import create_reader

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
    return create_plugin(session, reader.id, manifest, {"main.py": "print('hi')"})
