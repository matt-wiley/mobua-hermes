"""Shared saved-data projections for the CLI and API."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict


def _as_utc(value: datetime) -> datetime:
    # Times are stored in UTC, but SQLite returns them without a zone; Postgres keeps it.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


type UTCDateTime = Annotated[datetime, AfterValidator(_as_utc)]


class PluginStarter(BaseModel):
    plugin_id: uuid.UUID
    revision_id: uuid.UUID


class DraftDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: uuid.UUID
    reader_id: uuid.UUID
    plugin_id: uuid.UUID
    parent_revision_id: uuid.UUID
    version: int
    manifest: str
    code: dict[str, str]


class RevisionDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: uuid.UUID
    plugin_id: uuid.UUID
    number: int
    # Empty for a tree root: a starter, or legacy history whose ancestry was never recorded.
    parent_revision_id: uuid.UUID | None
    created_by: str
    created_at: UTCDateTime
    manifest: str
    code: dict[str, str]


class RevisionHistory(BaseModel):
    model_config = ConfigDict(frozen=True)

    plugin_id: uuid.UUID
    current_revision_id: uuid.UUID | None
    revisions: list[RevisionDetails]
