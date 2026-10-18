import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from news.service.manifest import parse_manifest
from news.service.models import Plugin, PluginRevision
from news.service.plugins import create_plugin
from news.service.revisions import SYSTEM_CREATOR, creator_of
from news.service.validation import ValidationRejected
from tests.service.factories import a_built_in_plugin_revision, a_reader


def test_created_plugin_is_owned_by_the_reader_with_a_first_revision(session: Session) -> None:
    reader = a_reader(session)

    revision = create_plugin(session, reader.id, "rss")
    session.commit()

    plugin = session.get_one(Plugin, revision.plugin_id)
    assert plugin.reader_id == reader.id
    assert plugin.name == "rss"
    assert plugin.current_revision_id == revision.id
    assert revision.number == 1
    assert revision.reader_id == reader.id
    assert parse_manifest(revision.manifest).name == "rss"
    assert "main.py" in revision.code


def test_revision_created_by_a_reader_records_that_readers_id(session: Session) -> None:
    """AC-5, Reader path."""
    reader = a_reader(session)

    revision = create_plugin(session, reader.id, "rss")
    session.commit()
    session.expire_all()

    assert session.get_one(PluginRevision, revision.id).created_by == str(reader.id)


def test_revision_created_without_a_reader_records_system_as_creator() -> None:
    """AC-5, seeding path: seeding itself is ticket 05, so the creator rule is tested directly."""
    assert creator_of(None) == SYSTEM_CREATOR == "system"


def test_built_in_revision_reads_back_as_system_created_with_no_reader(session: Session) -> None:
    """AC-21."""
    revision = a_built_in_plugin_revision(session)
    session.commit()
    session.expire_all()

    stored = session.get_one(PluginRevision, revision.id)
    assert stored.created_by == "system"
    assert stored.reader_id is None
    assert session.get_one(Plugin, stored.plugin_id).reader_id is None


def test_plugin_with_a_blank_name_is_rejected_and_not_saved(session: Session) -> None:
    reader = a_reader(session)

    with pytest.raises(ValidationRejected):
        create_plugin(session, reader.id, "")

    assert session.scalar(select(func.count()).select_from(Plugin)) == 0
    assert session.scalar(select(func.count()).select_from(PluginRevision)) == 0


def test_rejected_name_is_logged_with_the_reader_and_field_codes(session: Session) -> None:
    """Creation now takes a name; unfinished Manifests are accepted through Draft saves."""
    reader = a_reader(session)
    with capture_logs() as logs, pytest.raises(ValidationRejected) as raised:
        create_plugin(session, reader.id, " ")

    assert not session.new
    assert session.scalar(select(func.count()).select_from(Plugin)) == 0
    assert session.scalar(select(func.count()).select_from(PluginRevision)) == 0
    assert logs == [
        {
            "event": "plugin.rejected",
            "log_level": "info",
            "reader_id": str(reader.id),
            "fields": ["name"],
        }
    ]
    assert [error.field for error in raised.value.errors] == ["name"]


def test_whitespace_name_is_logged_without_supplied_payload(session: Session) -> None:
    reader = a_reader(session)

    with capture_logs() as logs, pytest.raises(ValidationRejected):
        create_plugin(session, reader.id, "\n\t")

    [event] = logs
    assert event["event"] == "plugin.rejected"
    assert event["fields"] == ["name"]
    assert set(event) == {"event", "log_level", "fields", "reader_id"}
