"""The guard against updating Plugin Revisions, Channel Revisions and Plugin Bindings (D-4)."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, delete, select, update
from sqlalchemy.orm import Session

from news.service.channels import bind_plugin, create_channel
from news.service.models import (
    Base,
    Channel,
    ChannelRevision,
    ImmutableRevisionError,
    Plugin,
    PluginBinding,
    PluginRevision,
)
from news.service.plugins import create_plugin
from tests.service.factories import URL_PLUGIN_MANIFEST, a_plugin_revision, a_reader


def a_bound_channel(session: Session) -> tuple[PluginRevision, Channel]:
    """A committed Channel at Revision 2, holding one Binding to a Plugin Revision."""
    reader = a_reader(session)
    plugin_revision = a_plugin_revision(session, reader)
    channel = create_channel(session, reader.id, "Local news")
    bind_plugin(session, reader.id, channel.id, plugin_revision.id, {"url": "https://a"})
    session.commit()
    return plugin_revision, channel


def stored_columns(engine: Engine, model: type[Base], row_id: uuid.UUID) -> dict[str, object]:
    """The row as the database holds it, read on a fresh connection."""
    with engine.connect() as connection:
        row = connection.execute(select(model.__table__).where(model.__table__.c.id == row_id))
        return dict(row.mappings().one())


type GuardedRow = PluginRevision | ChannelRevision | PluginBinding


def the_plugin_revision(plugin_revision: PluginRevision, _channel: Channel) -> GuardedRow:
    return plugin_revision


def the_current_channel_revision(_plugin_revision: PluginRevision, channel: Channel) -> GuardedRow:
    assert channel.current_revision is not None
    return channel.current_revision


def the_current_binding(_plugin_revision: PluginRevision, channel: Channel) -> PluginBinding:
    assert channel.current_revision is not None
    return channel.current_revision.bindings[0]


@pytest.mark.parametrize(
    ("table", "row_of", "attribute", "value"),
    [
        ("plugin_revision", the_plugin_revision, "note", "edited"),
        ("channel_revision", the_current_channel_revision, "note", "edited"),
        ("plugin_binding", the_current_binding, "config", {"url": "https://b"}),
    ],
    ids=["plugin_revision", "channel_revision", "plugin_binding"],
)
def test_changing_a_committed_row_is_rejected_and_leaves_it_stored_unchanged(
    engine: Engine,
    session: Session,
    table: str,
    row_of: Callable[[PluginRevision, Channel], GuardedRow],
    attribute: str,
    value: object,
) -> None:
    plugin_revision, channel = a_bound_channel(session)
    row = row_of(plugin_revision, channel)
    before = stored_columns(engine, type(row), row.id)

    setattr(row, attribute, value)
    with pytest.raises(ImmutableRevisionError) as raised:
        session.flush()

    assert raised.value.table == table
    assert raised.value.attributes == [attribute]
    assert table in str(raised.value)
    assert attribute in str(raised.value)
    session.rollback()
    assert stored_columns(engine, type(row), row.id) == before


@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("code", {"main.py": "print('edited')"}),
        ("parent_revision_id", uuid.uuid7()),
        ("created_by", "someone-else"),
        ("created_at", datetime(2000, 1, 1, tzinfo=UTC)),
    ],
)
def test_plugin_revision_code_ancestry_and_metadata_cannot_change(
    engine: Engine, session: Session, attribute: str, value: object
) -> None:
    """AC-68: Manifest, code, ancestry and metadata stay as promoted."""
    plugin_revision, _ = a_bound_channel(session)
    before = stored_columns(engine, PluginRevision, plugin_revision.id)

    setattr(plugin_revision, attribute, value)
    with pytest.raises(ImmutableRevisionError) as raised:
        session.flush()

    assert raised.value.attributes == [attribute]
    session.rollback()
    assert stored_columns(engine, PluginRevision, plugin_revision.id) == before


def test_every_changed_attribute_is_named(session: Session) -> None:
    plugin_revision, _ = a_bound_channel(session)

    plugin_revision.note = "edited"
    plugin_revision.manifest = "name = 'other'"
    with pytest.raises(ImmutableRevisionError) as raised:
        session.flush()

    assert raised.value.attributes == ["manifest", "note"]


def test_repointing_a_binding_through_its_relationship_is_rejected(
    engine: Engine, session: Session
) -> None:
    """The foreign key changes only during the flush, so the relationship itself is checked."""
    plugin_revision, channel = a_bound_channel(session)
    assert plugin_revision.reader_id is not None
    other = create_plugin(session, plugin_revision.reader_id, "other")
    session.commit()
    binding = the_current_binding(plugin_revision, channel)

    binding.plugin_revision = other
    with pytest.raises(ImmutableRevisionError) as raised:
        session.flush()

    assert raised.value.attributes == ["plugin_revision"]
    session.rollback()
    stored = stored_columns(engine, PluginBinding, binding.id)
    assert stored["plugin_revision_id"] == plugin_revision.id


def test_setting_an_attribute_to_its_current_value_is_not_a_change(session: Session) -> None:
    plugin_revision, _ = a_bound_channel(session)

    plugin_revision.number = plugin_revision.number
    session.flush()


def test_a_row_still_pending_insert_can_be_changed_before_it_is_flushed(session: Session) -> None:
    reader = a_reader(session)
    revision = create_plugin(session, reader.id, "starter")
    session.commit()
    new_revision = PluginRevision(
        id=uuid.uuid7(),
        plugin_id=revision.plugin_id,
        reader_id=reader.id,
        number=2,
        manifest=URL_PLUGIN_MANIFEST,
        code={},
        created_by=str(reader.id),
    )
    session.add(new_revision)

    new_revision.note = "set before the insert"
    session.flush()

    assert new_revision.note == "set before the insert"


def test_creating_and_binding_still_succeed_with_the_guard_active(session: Session) -> None:
    _, channel = a_bound_channel(session)

    assert channel.current_revision is not None
    assert channel.current_revision.number == 2


def test_a_channels_current_revision_can_be_moved_to_an_existing_revision(
    engine: Engine, session: Session
) -> None:
    _, channel = a_bound_channel(session)
    first = session.scalars(
        select(ChannelRevision).where(
            ChannelRevision.channel_id == channel.id, ChannelRevision.number == 1
        )
    ).one()

    channel.current_revision = first
    session.commit()

    assert stored_columns(engine, Channel, channel.id)["current_revision_id"] == first.id


def test_a_plugins_current_revision_can_be_moved_to_an_existing_revision(
    engine: Engine, session: Session
) -> None:
    reader = a_reader(session)
    first = create_plugin(session, reader.id, "starter")
    plugin = session.get_one(Plugin, first.plugin_id)
    second = PluginRevision(
        id=uuid.uuid7(),
        plugin_id=plugin.id,
        reader_id=reader.id,
        number=2,
        manifest=URL_PLUGIN_MANIFEST,
        code={},
        created_by=str(reader.id),
    )
    session.add(second)
    plugin.current_revision = second
    session.commit()

    plugin.current_revision = first
    session.commit()

    assert stored_columns(engine, Plugin, plugin.id)["current_revision_id"] == first.id


def test_deleting_channel_revision_and_binding_rows_is_not_blocked(session: Session) -> None:
    """Only Plugin Revisions are declared permanent (AC-68); no Channel deletion policy exists."""
    plugin_revision, channel = a_bound_channel(session)
    binding = the_current_binding(plugin_revision, channel)
    first = session.scalars(
        select(ChannelRevision).where(
            ChannelRevision.channel_id == channel.id, ChannelRevision.number == 1
        )
    ).one()

    session.delete(binding)
    session.delete(first)
    session.commit()

    assert session.get(PluginBinding, binding.id) is None
    assert session.get(ChannelRevision, first.id) is None


def test_a_changed_row_that_is_then_deleted_is_not_blocked(session: Session) -> None:
    """The update never reaches the database, since the row is deleted instead."""
    plugin_revision, channel = a_bound_channel(session)
    binding = the_current_binding(plugin_revision, channel)

    binding.config = {"url": "https://b"}
    session.delete(binding)
    session.commit()

    assert session.get(PluginBinding, binding.id) is None


def test_deleting_a_committed_plugin_revision_is_rejected_and_keeps_it_stored(
    engine: Engine, session: Session
) -> None:
    plugin_revision = an_unreferenced_plugin_revision(session)
    before = stored_columns(engine, PluginRevision, plugin_revision.id)

    session.delete(plugin_revision)
    with pytest.raises(ImmutableRevisionError) as raised:
        session.flush()

    assert raised.value.table == "plugin_revision"
    assert raised.value.operation == "delete"
    assert "permanent" in str(raised.value)
    session.rollback()
    assert stored_columns(engine, PluginRevision, plugin_revision.id) == before


def test_a_plugin_revision_still_pending_insert_can_be_discarded(session: Session) -> None:
    reader = a_reader(session)
    revision = create_plugin(session, reader.id, "starter")
    session.commit()
    pending = PluginRevision(
        id=uuid.uuid7(),
        plugin_id=revision.plugin_id,
        reader_id=reader.id,
        number=2,
        manifest=URL_PLUGIN_MANIFEST,
        code={},
        created_by=str(reader.id),
    )
    session.add(pending)

    session.expunge(pending)
    session.flush()

    assert session.get(PluginRevision, pending.id) is None


def an_unreferenced_plugin_revision(session: Session) -> PluginRevision:
    """A committed, non-current Revision that no Binding pins, so only the guard can refuse."""
    reader = a_reader(session, "Bulk")
    starter = create_plugin(session, reader.id, "bulk")
    revision = PluginRevision(
        id=uuid.uuid7(),
        plugin_id=starter.plugin_id,
        reader_id=reader.id,
        number=2,
        manifest=URL_PLUGIN_MANIFEST,
        code={},
        created_by=str(reader.id),
    )
    session.add(revision)
    session.commit()
    return revision


@pytest.mark.parametrize(
    ("model", "operation", "values"),
    [
        (PluginRevision, "delete", None),
        (PluginRevision, "update", {"note": "edited"}),
        (ChannelRevision, "update", {"note": "edited"}),
        (PluginBinding, "update", {"config": {"url": "https://b"}}),
    ],
    ids=[
        "delete-plugin_revision",
        "update-plugin_revision",
        "update-channel_revision",
        "update-plugin_binding",
    ],
)
def test_bulk_orm_statements_cannot_bypass_the_guard(
    engine: Engine,
    session: Session,
    model: type[GuardedRow],
    operation: str,
    values: dict[str, object] | None,
) -> None:
    a_bound_channel(session)
    unreferenced = an_unreferenced_plugin_revision(session)
    with engine.connect() as connection:
        before = connection.execute(select(model.__table__)).all()
    statement = (
        delete(PluginRevision).where(PluginRevision.id == unreferenced.id)
        if values is None
        else update(model).values(values)
    )

    with pytest.raises(ImmutableRevisionError) as raised:
        session.execute(statement)

    assert raised.value.table == model.__tablename__
    assert raised.value.operation == operation
    session.rollback()
    with engine.connect() as connection:
        assert connection.execute(select(model.__table__)).all() == before


def test_bulk_deletes_of_channel_revisions_and_bindings_are_not_blocked(session: Session) -> None:
    _, channel = a_bound_channel(session)

    session.execute(delete(PluginBinding).where(PluginBinding.channel_id == channel.id))
    session.rollback()
