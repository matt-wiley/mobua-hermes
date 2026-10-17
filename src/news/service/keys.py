"""Deploy-time Master Key sources and explicit first-run generation."""

import base64
import binascii
import os
from collections.abc import Mapping
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from news.service.encryption import EncryptionError
from news.service.models import ReaderDataKey

log = structlog.get_logger(__name__)


def _source_failure(reason: str) -> EncryptionError:
    log.warning("keys.source_failed", reason=reason)
    return EncryptionError(f"Master Key: {reason}")


def read_master_key(environ: Mapping[str, str]) -> bytes:
    direct = environ.get("NEWS_MASTER_KEY")
    filename = environ.get("NEWS_MASTER_KEY_FILE")
    if direct is not None and filename is not None:
        raise _source_failure("set only NEWS_MASTER_KEY or NEWS_MASTER_KEY_FILE")
    if direct is None and filename is None:
        raise _source_failure(
            "supply NEWS_MASTER_KEY or NEWS_MASTER_KEY_FILE; initialize with key generate"
        )
    if filename is not None:
        try:
            direct = Path(filename).read_text(encoding="ascii").strip()
        except OSError, UnicodeError:
            raise _source_failure("cannot read NEWS_MASTER_KEY_FILE") from None
    try:
        key = base64.b64decode(direct or "", altchars=b"-_", validate=True)
    except ValueError, binascii.Error:
        raise _source_failure("expected a base64-encoded 32-byte key") from None
    if len(key) != 32:
        raise _source_failure("expected a base64-encoded 32-byte key")
    return key


def generate_master_key(session: Session, environ: Mapping[str, str]) -> str:
    """Generate only for initial setup; never replace a configured or previously used key."""
    if "NEWS_MASTER_KEY" in environ or "NEWS_MASTER_KEY_FILE" in environ:
        raise _source_failure("already configured; generation is only for initial setup")
    if session.scalar(select(ReaderDataKey.id).limit(1)) is not None:
        raise _source_failure("encrypted data already exists; supply the original key")
    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
