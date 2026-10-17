"""The revisioned Channel and Plugin records (ADRs 0016, 0018, 0019).

Every table declares its scope in `Table.info`: `app`, `reader` or `channel` (ADR 0007).
A `reader` table carries a Reader id, and a `channel` table carries a Channel id as well.
The `reader` and `channel` tables are scoped by their own `id`. Plugin and Plugin Revision rows
of Built-in Plugins leave the Reader id empty (ADR 0019). The schema tests check these rules.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import JSON, DateTime, ForeignKey, MetaData, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

type Scope = Literal["app", "reader", "channel"]


def scoped(scope: Scope) -> dict[str, Any]:
    """Table arguments declaring a table's scope; a fresh dict, since tables keep it as `info`."""
    return {"info": {"scope": scope}}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    # Named constraints keep Alembic batch migrations on SQLite deterministic.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Reader(Base):
    __tablename__ = "reader"
    __table_args__ = scoped("reader")

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Plugin(Base):
    __tablename__ = "plugin"
    __table_args__ = scoped("reader")

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    # Empty for Built-in Plugins, which are system-owned (ADR 0019).
    reader_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reader.id"), index=True)
    name: Mapped[str]
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("plugin_revision.id", use_alter=True)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    current_revision: Mapped[PluginRevision | None] = relationship(
        foreign_keys=[current_revision_id], post_update=True
    )


class PluginRevision(Base):
    __tablename__ = "plugin_revision"
    __table_args__ = (UniqueConstraint("plugin_id", "number"), scoped("reader"))

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    plugin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plugin.id"))
    # Copied from the Plugin so the row is scoped on its own; empty for Built-in Plugins.
    reader_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reader.id"), index=True)
    number: Mapped[int]
    manifest: Mapped[str] = mapped_column(Text)
    code: Mapped[dict[str, str]] = mapped_column(JSON)
    # A Reader id, or "system" for seeded Built-in Plugin Revisions. Provenance only.
    created_by: Mapped[str]
    note: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Channel(Base):
    __tablename__ = "channel"
    __table_args__ = scoped("channel")

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    reader_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reader.id"), index=True)
    name: Mapped[str]
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("channel_revision.id", use_alter=True)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    current_revision: Mapped[ChannelRevision | None] = relationship(
        foreign_keys=[current_revision_id], post_update=True
    )


class ChannelRevision(Base):
    __tablename__ = "channel_revision"
    __table_args__ = (UniqueConstraint("channel_id", "number"), scoped("channel"))

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    channel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("channel.id"))
    reader_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reader.id"), index=True)
    number: Mapped[int]
    note: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    bindings: Mapped[list[PluginBinding]] = relationship(order_by="PluginBinding.position")


class PluginBinding(Base):
    __tablename__ = "plugin_binding"
    __table_args__ = scoped("channel")

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    channel_revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("channel_revision.id"))
    channel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("channel.id"), index=True)
    reader_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reader.id"), index=True)
    # Pinned to one exact Plugin Revision, never the Plugin identity (ADR 0018).
    plugin_revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plugin_revision.id"))
    position: Mapped[int]
    config: Mapped[dict[str, Any]] = mapped_column(JSON)

    plugin_revision: Mapped[PluginRevision] = relationship()
