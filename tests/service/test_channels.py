import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from news.service.binding_config import ConfigError
from news.service.channels import (
    BindingSpec,
    ChannelNotFound,
    ChannelRevisionRejected,
    bind_plugin,
    create_channel,
    save_channel_revision,
)
from news.service.models import Channel, ChannelRevision
from tests.service.factories import OPEN_PLUGIN_MANIFEST, a_plugin_revision, a_reader


def revision_count(session: Session, channel: Channel) -> int:
    count = session.scalar(
        select(func.count())
        .select_from(ChannelRevision)
        .where(ChannelRevision.channel_id == channel.id)
    )
    return count or 0


def test_new_channel_starts_at_revision_one_with_no_bindings(session: Session) -> None:
    reader = a_reader(session)

    channel = create_channel(session, reader.id, "Local news")
    session.commit()

    assert channel.reader_id == reader.id
    assert channel.current_revision is not None
    assert channel.current_revision.number == 1
    assert channel.current_revision.bindings == []


def test_binding_with_valid_config_creates_a_pinned_revision(session: Session) -> None:
    """AC-1 happy path."""
    reader = a_reader(session)
    plugin_revision = a_plugin_revision(session, reader)
    channel = create_channel(session, reader.id, "Local news")

    revision = bind_plugin(
        session, reader.id, channel.id, plugin_revision.id, {"url": "https://example.com/rss"}
    )
    session.commit()

    assert revision.number == 2
    assert channel.current_revision_id == revision.id
    [binding] = revision.bindings
    assert binding.plugin_revision_id == plugin_revision.id
    assert binding.config == {"url": "https://example.com/rss"}
    assert binding.channel_id == channel.id
    assert binding.reader_id == reader.id


def test_binding_missing_a_required_field_is_rejected_and_no_revision_is_created(
    session: Session,
) -> None:
    """AC-1 failure mode."""
    reader = a_reader(session)
    plugin_revision = a_plugin_revision(session, reader)
    channel = create_channel(session, reader.id, "Local news")
    session.commit()

    with pytest.raises(ChannelRevisionRejected) as raised:
        bind_plugin(session, reader.id, channel.id, plugin_revision.id, {})

    assert raised.value.errors == [
        ConfigError(field="bindings.0.url", message="'url' is a required property")
    ]
    session.rollback()
    assert revision_count(session, channel) == 1
    assert channel.current_revision is not None
    assert channel.current_revision.number == 1


def test_rejected_revision_is_logged_with_the_channel_and_errors(session: Session) -> None:
    reader = a_reader(session)
    plugin_revision = a_plugin_revision(session, reader)
    channel = create_channel(session, reader.id, "Local news")

    with capture_logs() as logs, pytest.raises(ChannelRevisionRejected):
        bind_plugin(session, reader.id, channel.id, plugin_revision.id, {})

    assert logs == [
        {
            "event": "channel_revision.rejected",
            "log_level": "info",
            "channel_id": str(channel.id),
            "errors": [{"field": "bindings.0.url", "message": "'url' is a required property"}],
        }
    ]


def test_unknown_field_is_rejected_when_the_schema_forbids_it(session: Session) -> None:
    """AC-1 boundary: additionalProperties = false."""
    reader = a_reader(session)
    plugin_revision = a_plugin_revision(session, reader)
    channel = create_channel(session, reader.id, "Local news")

    with pytest.raises(ChannelRevisionRejected) as raised:
        bind_plugin(
            session, reader.id, channel.id, plugin_revision.id, {"url": "https://x", "extra": 1}
        )

    assert [error.field for error in raised.value.errors] == ["bindings.0.extra"]


def test_unknown_field_is_kept_when_the_schema_allows_it(session: Session) -> None:
    """AC-1 boundary: additionalProperties unspecified."""
    reader = a_reader(session)
    plugin_revision = a_plugin_revision(session, reader, OPEN_PLUGIN_MANIFEST)
    channel = create_channel(session, reader.id, "Local news")

    revision = bind_plugin(session, reader.id, channel.id, plugin_revision.id, {"extra": 1})

    assert revision.bindings[0].config == {"extra": 1}


def test_binding_to_a_missing_plugin_revision_is_rejected(session: Session) -> None:
    reader = a_reader(session)
    channel = create_channel(session, reader.id, "Local news")

    with pytest.raises(ChannelRevisionRejected) as raised:
        bind_plugin(session, reader.id, channel.id, uuid.uuid7(), {})

    assert [error.field for error in raised.value.errors] == ["bindings.0.plugin_revision_id"]


def test_one_invalid_binding_rejects_the_whole_revision(session: Session) -> None:
    reader = a_reader(session)
    plugin_revision = a_plugin_revision(session, reader)
    channel = create_channel(session, reader.id, "Local news")
    session.commit()

    with pytest.raises(ChannelRevisionRejected) as raised:
        save_channel_revision(
            session,
            reader.id,
            channel.id,
            [
                BindingSpec(plugin_revision.id, {"url": "https://a"}),
                BindingSpec(plugin_revision.id, {"url": 5}),
            ],
        )

    assert [error.field for error in raised.value.errors] == ["bindings.1.url"]
    session.rollback()
    assert revision_count(session, channel) == 1


def test_binding_again_keeps_the_existing_bindings(session: Session) -> None:
    reader = a_reader(session)
    plugin_revision = a_plugin_revision(session, reader)
    channel = create_channel(session, reader.id, "Local news")
    bind_plugin(session, reader.id, channel.id, plugin_revision.id, {"url": "https://a"})

    revision = bind_plugin(session, reader.id, channel.id, plugin_revision.id, {"url": "https://b"})

    assert revision.number == 3
    assert [binding.config["url"] for binding in revision.bindings] == ["https://a", "https://b"]


def test_earlier_revisions_are_left_unchanged(session: Session) -> None:
    reader = a_reader(session)
    plugin_revision = a_plugin_revision(session, reader)
    channel = create_channel(session, reader.id, "Local news")
    first = channel.current_revision
    assert first is not None

    bind_plugin(session, reader.id, channel.id, plugin_revision.id, {"url": "https://a"})
    session.commit()
    session.expire_all()

    assert session.get_one(ChannelRevision, first.id).bindings == []


def test_saving_a_revision_with_zero_bindings_is_allowed(session: Session) -> None:
    reader = a_reader(session)
    channel = create_channel(session, reader.id, "Local news")

    revision = save_channel_revision(session, reader.id, channel.id, [], note="cleared")

    assert revision.number == 2
    assert revision.bindings == []
    assert revision.note == "cleared"


def test_another_readers_channel_cannot_be_revised(session: Session) -> None:
    owner = a_reader(session, "Ada")
    other = a_reader(session, "Grace")
    channel = create_channel(session, owner.id, "Local news")

    with pytest.raises(ChannelNotFound):
        save_channel_revision(session, other.id, channel.id, [])
