"""Shared saved-data projections for the CLI and API."""

import uuid

from pydantic import BaseModel, ConfigDict


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
