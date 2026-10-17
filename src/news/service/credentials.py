"""Reader-scoped encrypted Secrets and Provider credentials (ADR 0009)."""

import os
import uuid
from collections.abc import Callable

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from news.service.encryption import EncryptionError, decrypt, encrypt
from news.service.models import LLMProvider, ReaderDataKey, Secret
from news.service.readers import require_reader

type KeySource = Callable[[], bytes]
log = structlog.get_logger(__name__)


class SecretNotFound(LookupError):
    pass


def load_data_key(session: Session, reader_id: uuid.UUID, key_source: KeySource) -> bytes:
    """Unwrap a Reader's key, creating it on the first credential save in this transaction."""
    require_reader(session, reader_id)
    master_key = key_source()
    record = session.scalar(select(ReaderDataKey).where(ReaderDataKey.reader_id == reader_id))
    context = f"data-key:{reader_id}".encode()
    if record is not None:
        return _decrypt(master_key, record.encrypted_key, context, reader_id)
    data_key = os.urandom(32)
    record = ReaderDataKey(
        reader_id=reader_id,
        encrypted_key=encrypt(master_key, data_key, context, os.urandom(12)),
    )
    session.add(record)
    session.flush()
    return data_key


def _decrypt(key: bytes, ciphertext: bytes, context: bytes, reader_id: uuid.UUID) -> bytes:
    try:
        return decrypt(key, ciphertext, context)
    except EncryptionError:
        log.warning("credentials.decrypt_failed", reader_id=str(reader_id))
        raise


def save_secret(
    session: Session, reader_id: uuid.UUID, name: str, value: str, key_source: KeySource
) -> Secret:
    key = load_data_key(session, reader_id, key_source)
    record = session.scalar(
        select(Secret).where(Secret.reader_id == reader_id, Secret.name == name)
    )
    if record is None:
        record = Secret(id=uuid.uuid7(), reader_id=reader_id, name=name)
    record.encrypted_value = encrypt(
        key, value.encode(), f"secret:{reader_id}:{record.id}".encode(), os.urandom(12)
    )
    session.add(record)
    session.flush()
    return record


def save_provider(
    session: Session,
    reader_id: uuid.UUID,
    name: str,
    url: str,
    api_key: str,
    key_source: KeySource,
) -> LLMProvider:
    key = load_data_key(session, reader_id, key_source)
    record = session.scalar(
        select(LLMProvider).where(LLMProvider.reader_id == reader_id, LLMProvider.name == name)
    )
    if record is None:
        record = LLMProvider(id=uuid.uuid7(), reader_id=reader_id, name=name)
    record.url = url
    record.encrypted_credential = encrypt(
        key, api_key.encode(), f"provider:{reader_id}:{record.id}".encode(), os.urandom(12)
    )
    session.add(record)
    session.flush()
    return record


def read_secret(
    session: Session, reader_id: uuid.UUID, secret_id: uuid.UUID, key_source: KeySource
) -> str:
    require_reader(session, reader_id)
    record = session.scalar(
        select(Secret).where(Secret.reader_id == reader_id, Secret.id == secret_id)
    )
    if record is None:
        log.info("credentials.secret_not_found", reader_id=str(reader_id), secret_id=str(secret_id))
        raise SecretNotFound(f"no Secret {secret_id}")
    key = load_data_key(session, reader_id, key_source)
    return _decrypt(
        key, record.encrypted_value, f"secret:{reader_id}:{record.id}".encode(), reader_id
    ).decode()
