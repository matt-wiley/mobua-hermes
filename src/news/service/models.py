"""The revisioned Channel and Plugin records (ADRs 0016, 0018, 0019).

Every table declares its scope in `Table.info`: `app`, `reader` or `channel` (ADR 0007).
A `reader` table carries a Reader id, and a `channel` table carries a Channel id as well.
The `reader` and `channel` tables are scoped by their own `id`. Plugin and Plugin Revision rows
of Built-in Plugins leave the Reader id empty (ADR 0019). The schema tests check these rules.

Plugin Revisions, Channel Revisions and Plugin Bindings are never updated once written, and Plugin
Revisions are never deleted (ADR 0024): a flush or ORM statement that would do so raises
ImmutableRevisionError. Migrations are the explicit schema-transition boundary and bypass it.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    LargeBinary,
    MetaData,
    Text,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    ORMExecuteState,
    Session,
    mapped_column,
    relationship,
)

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


class ReaderDataKey(Base):
    __tablename__ = "reader_data_key"
    __table_args__ = scoped("reader")

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    reader_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reader.id"), unique=True)
    encrypted_key: Mapped[bytes] = mapped_column(LargeBinary)


class Secret(Base):
    __tablename__ = "secret"
    __table_args__ = (UniqueConstraint("reader_id", "name"), scoped("reader"))

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    reader_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reader.id"), index=True)
    name: Mapped[str]
    encrypted_value: Mapped[bytes] = mapped_column(LargeBinary)


class LLMProvider(Base):
    __tablename__ = "llm_provider"
    __table_args__ = (UniqueConstraint("reader_id", "name"), scoped("reader"))

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    reader_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reader.id"), index=True)
    name: Mapped[str]
    url: Mapped[str]
    encrypted_credential: Mapped[bytes] = mapped_column(LargeBinary)


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
    # No FK: global Built-in ancestry may refer to implementations absent locally (ADR 0025).
    # Reader-owned parent eligibility is enforced by the service. Legacy ancestry is unknown.
    parent_revision_id: Mapped[uuid.UUID | None]
    manifest: Mapped[str] = mapped_column(Text)
    code: Mapped[dict[str, str]] = mapped_column(JSON)
    # A Reader id, or "system" for seeded Built-in Plugin Revisions. Provenance only.
    created_by: Mapped[str]
    note: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PluginDraft(Base):
    __tablename__ = "plugin_draft"
    __table_args__ = scoped("reader")

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    reader_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reader.id"), index=True)
    plugin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plugin.id"), index=True)
    parent_revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plugin_revision.id"))
    version: Mapped[int] = mapped_column(default=1)
    manifest: Mapped[str] = mapped_column(Text)
    code: Mapped[dict[str, str]] = mapped_column(JSON)
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


# Never updated once written: edits insert a new Revision instead (ADRs 0016, 0018). The
# current-Revision pointers on Plugin and Channel rows are left alone.
IMMUTABLE_MODELS = (PluginRevision, ChannelRevision, PluginBinding)
# Never deleted (ADR 0024). Channel Revision and Binding deletion has no policy yet.
PERMANENT_MODELS = (PluginRevision,)


class ImmutableRevisionError(Exception):
    """A write would update a Revision or Plugin Binding row, or delete a Plugin Revision row.

    A programming error: no service offers either.
    """

    def __init__(
        self, table: str, attributes: list[str], operation: Literal["update", "delete"] = "update"
    ) -> None:
        if operation == "delete":
            message = f"{table} rows are permanent; delete rejected"
        elif attributes:
            message = f"{table} rows are immutable; changed: {', '.join(attributes)}"
        else:
            message = f"{table} rows are immutable; bulk update rejected"
        super().__init__(message)
        self.table = table
        self.attributes = attributes
        self.operation = operation


@event.listens_for(Session, "before_flush")
def _reject_revision_changes(session: Session, _flush_context: Any, _instances: Any) -> None:
    # Registered on the Session class, so every session the CLI or API opens is guarded.
    # In-place changes inside a JSON value aren't tracked, so they never reach this check.
    for instance in session.deleted:
        if isinstance(instance, PERMANENT_MODELS):
            raise ImmutableRevisionError(instance.__tablename__, [], "delete")
    for instance in session.dirty:
        if not isinstance(instance, IMMUTABLE_MODELS):
            continue
        state = inspect(instance)
        # Relationships too: reassigning one sets its foreign key only later, during the flush.
        changed = sorted(attr.key for attr in state.attrs if attr.history.has_changes())
        if changed:
            raise ImmutableRevisionError(instance.__tablename__, changed)


@event.listens_for(Session, "do_orm_execute")
def _reject_bulk_revision_changes(state: ORMExecuteState) -> None:
    # ORM-enabled update() and delete() statements skip the flush, so they are checked here.
    if state.bind_mapper is None:
        return
    model = state.bind_mapper.class_
    if state.is_delete and issubclass(model, PERMANENT_MODELS):
        raise ImmutableRevisionError(model.__tablename__, [], "delete")
    if state.is_update and issubclass(model, IMMUTABLE_MODELS):
        raise ImmutableRevisionError(model.__tablename__, [])
