import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from news.service.channels import create_channel
from news.service.models import Channel, ChannelRevision, Plugin, PluginRevision
from news.service.plugins import create_plugin
from news.service.readers import ReaderNotFound, require_reader
from tests.service.factories import a_reader


def row_count(session: Session, model: type[object]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_an_existing_reader_is_returned(session: Session) -> None:
    reader = a_reader(session)

    assert require_reader(session, reader.id) is reader


def test_an_unknown_reader_is_not_found_and_logged(session: Session) -> None:
    unknown = uuid.uuid7()

    with capture_logs() as logs, pytest.raises(ReaderNotFound) as raised:
        require_reader(session, unknown)

    assert str(raised.value) == f"no Reader {unknown}"
    assert logs == [{"event": "reader.not_found", "log_level": "info", "reader_id": str(unknown)}]


def test_reader_not_found_is_a_lookup_error() -> None:
    assert issubclass(ReaderNotFound, LookupError)


def test_a_plugin_for_an_unknown_reader_is_rejected_and_nothing_is_written(
    session: Session,
) -> None:
    unknown = uuid.uuid7()

    with capture_logs() as logs, pytest.raises(ReaderNotFound):
        create_plugin(session, unknown, "starter")

    assert not session.new
    assert row_count(session, Plugin) == 0
    assert row_count(session, PluginRevision) == 0
    assert [log["event"] for log in logs] == ["reader.not_found"]
    assert logs[0]["reader_id"] == str(unknown)


def test_a_channel_for_an_unknown_reader_is_rejected_and_nothing_is_written(
    session: Session,
) -> None:
    unknown = uuid.uuid7()

    with capture_logs() as logs, pytest.raises(ReaderNotFound):
        create_channel(session, unknown, "Local news")

    assert not session.new
    assert row_count(session, Channel) == 0
    assert row_count(session, ChannelRevision) == 0
    assert [log["event"] for log in logs] == ["reader.not_found"]
    assert logs[0]["reader_id"] == str(unknown)
