"""Readers: the owners every record is scoped to (ADR 0007)."""

import uuid

import structlog
from sqlalchemy.orm import Session

from news.service.models import Reader

log = structlog.get_logger(__name__)


class ReaderNotFound(LookupError):
    pass


def create_reader(session: Session, name: str) -> Reader:
    reader = Reader(id=uuid.uuid7(), name=name)
    session.add(reader)
    session.flush()
    return reader


def require_reader(session: Session, reader_id: uuid.UUID) -> Reader:
    """Return the Reader, or raise ReaderNotFound before anything is written for it."""
    reader = session.get(Reader, reader_id)
    if reader is None:
        log.info("reader.not_found", reader_id=str(reader_id))
        raise ReaderNotFound(f"no Reader {reader_id}")
    return reader
