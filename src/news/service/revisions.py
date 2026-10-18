"""Rules for creating immutable Revisions (ADRs 0016, 0018)."""

import uuid

# Creator of Built-in Plugin Revisions added by seeding (ADR 0019).
SYSTEM_CREATOR = "system"


def creator_of(reader_id: uuid.UUID | None) -> str:
    return SYSTEM_CREATOR if reader_id is None else str(reader_id)


def next_revision_number(latest: int | None) -> int:
    return 1 if latest is None else latest + 1
