import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from news.service.manifest import PluginRevisionRejected
from news.service.models import Plugin, PluginRevision
from news.service.plugins import create_plugin
from news.service.revisions import SYSTEM_CREATOR, creator_of
from tests.service.factories import URL_PLUGIN_MANIFEST, a_reader


def test_created_plugin_is_owned_by_the_reader_with_a_first_revision(session: Session) -> None:
    reader = a_reader(session)

    revision = create_plugin(session, reader.id, URL_PLUGIN_MANIFEST, {"main.py": "print(1)"})
    session.commit()

    plugin = session.get_one(Plugin, revision.plugin_id)
    assert plugin.reader_id == reader.id
    assert plugin.name == "rss"
    assert plugin.current_revision_id == revision.id
    assert revision.number == 1
    assert revision.reader_id == reader.id
    assert revision.manifest == URL_PLUGIN_MANIFEST
    assert revision.code == {"main.py": "print(1)"}


def test_revision_created_by_a_reader_records_that_readers_id(session: Session) -> None:
    """AC-5, Reader path."""
    reader = a_reader(session)

    revision = create_plugin(session, reader.id, URL_PLUGIN_MANIFEST, {"main.py": ""})
    session.commit()
    session.expire_all()

    assert session.get_one(PluginRevision, revision.id).created_by == str(reader.id)


def test_revision_created_without_a_reader_records_system_as_creator() -> None:
    """AC-5, seeding path: seeding itself is ticket 05, so the creator rule is tested directly."""
    assert creator_of(None) == SYSTEM_CREATOR == "system"


def test_plugin_with_an_invalid_manifest_is_rejected_and_not_saved(session: Session) -> None:
    reader = a_reader(session)

    with pytest.raises(PluginRevisionRejected):
        create_plugin(session, reader.id, 'name = "broken', {"main.py": ""})

    assert session.scalar(select(func.count()).select_from(Plugin)) == 0
    assert session.scalar(select(func.count()).select_from(PluginRevision)) == 0


def test_rejected_manifest_is_logged_with_the_reader_and_errors(session: Session) -> None:
    """AC-15."""
    reader = a_reader(session)
    zero_timeout = URL_PLUGIN_MANIFEST.replace("timeout = 60", "timeout = 0")

    with capture_logs() as logs, pytest.raises(PluginRevisionRejected) as raised:
        create_plugin(session, reader.id, zero_timeout, {"main.py": ""})

    assert not session.new
    assert session.scalar(select(func.count()).select_from(Plugin)) == 0
    assert session.scalar(select(func.count()).select_from(PluginRevision)) == 0
    assert logs == [
        {
            "event": "plugin_revision.rejected",
            "log_level": "info",
            "reader_id": str(reader.id),
            "errors": [
                {"field": "timeout", "message": "Input should be greater than 0"},
            ],
        }
    ]
    assert [error.field for error in raised.value.errors] == ["timeout"]


def test_malformed_manifest_is_logged_with_its_root_error(session: Session) -> None:
    reader = a_reader(session)

    with capture_logs() as logs, pytest.raises(PluginRevisionRejected):
        create_plugin(session, reader.id, 'name = "broken', {"main.py": ""})

    [event] = logs
    assert event["event"] == "plugin_revision.rejected"
    assert [error["field"] for error in event["errors"]] == [""]
