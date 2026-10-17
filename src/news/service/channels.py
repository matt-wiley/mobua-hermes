"""Channels, their immutable Channel Revisions, and Plugin Bindings (ADRs 0016, 0018)."""

import uuid
from dataclasses import asdict, dataclass
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from news.service.binding_config import ConfigError, validate_binding_config
from news.service.manifest import parse_manifest
from news.service.models import Channel, ChannelRevision, PluginBinding, PluginRevision
from news.service.revisions import next_revision_number

log = structlog.get_logger(__name__)


class ChannelNotFound(LookupError):
    pass


class ChannelRevisionRejected(Exception):
    def __init__(self, errors: list[ConfigError]) -> None:
        super().__init__("; ".join(f"{error.field}: {error.message}" for error in errors))
        self.errors = errors


@dataclass(frozen=True)
class BindingSpec:
    plugin_revision_id: uuid.UUID
    config: dict[str, Any]


def create_channel(session: Session, reader_id: uuid.UUID, name: str) -> Channel:
    """Create a Channel whose first Revision has no Plugin Bindings yet."""
    channel = Channel(id=uuid.uuid7(), reader_id=reader_id, name=name)
    session.add(channel)
    session.flush()
    save_channel_revision(session, reader_id, channel.id, [])
    return channel


def save_channel_revision(
    session: Session,
    reader_id: uuid.UUID,
    channel_id: uuid.UUID,
    bindings: list[BindingSpec],
    note: str | None = None,
) -> ChannelRevision:
    """Save a new current Revision holding exactly these Bindings.

    Raises ChannelRevisionRejected, creating nothing, if any Binding's config is invalid.
    """
    channel = _get_channel(session, reader_id, channel_id)
    errors = [
        error
        for position, binding in enumerate(bindings)
        for error in _binding_errors(session, position, binding)
    ]
    if errors:
        log.info(
            "channel_revision.rejected",
            channel_id=str(channel.id),
            errors=[asdict(error) for error in errors],
        )
        raise ChannelRevisionRejected(errors)

    latest = session.scalar(
        select(func.max(ChannelRevision.number)).where(ChannelRevision.channel_id == channel.id)
    )
    revision = ChannelRevision(
        id=uuid.uuid7(),
        channel_id=channel.id,
        reader_id=reader_id,
        number=next_revision_number(latest),
        note=note,
        bindings=[
            PluginBinding(
                id=uuid.uuid7(),
                channel_id=channel.id,
                reader_id=reader_id,
                plugin_revision_id=binding.plugin_revision_id,
                position=position,
                config=binding.config,
            )
            for position, binding in enumerate(bindings)
        ],
    )
    session.add(revision)
    channel.current_revision = revision
    session.flush()
    return revision


def bind_plugin(
    session: Session,
    reader_id: uuid.UUID,
    channel_id: uuid.UUID,
    plugin_revision_id: uuid.UUID,
    config: dict[str, Any],
) -> ChannelRevision:
    """Save a new Revision with the current Bindings plus one to this Plugin Revision."""
    channel = _get_channel(session, reader_id, channel_id)
    current = channel.current_revision.bindings if channel.current_revision else []
    kept = [BindingSpec(binding.plugin_revision_id, binding.config) for binding in current]
    return save_channel_revision(
        session, reader_id, channel_id, [*kept, BindingSpec(plugin_revision_id, config)]
    )


def _get_channel(session: Session, reader_id: uuid.UUID, channel_id: uuid.UUID) -> Channel:
    channel = session.scalar(
        select(Channel).where(Channel.id == channel_id, Channel.reader_id == reader_id)
    )
    if channel is None:
        raise ChannelNotFound(f"no Channel {channel_id} for this Reader")
    return channel


def _binding_errors(session: Session, position: int, binding: BindingSpec) -> list[ConfigError]:
    prefix = f"bindings.{position}"
    plugin_revision = session.get(PluginRevision, binding.plugin_revision_id)
    if plugin_revision is None:
        return [ConfigError(f"{prefix}.plugin_revision_id", "no such Plugin Revision")]
    schema = parse_manifest(plugin_revision.manifest).config_schema
    return [
        ConfigError(f"{prefix}.{error.field}" if error.field else prefix, error.message)
        for error in validate_binding_config(schema, binding.config)
    ]
