"""Readers: the owners every record is scoped to (ADR 0007)."""

import uuid

from sqlalchemy.orm import Session

from news.service.models import Reader


def create_reader(session: Session, name: str) -> Reader:
    reader = Reader(id=uuid.uuid7(), name=name)
    session.add(reader)
    session.flush()
    return reader
