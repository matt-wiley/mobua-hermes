import uuid

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from news.service.credentials import load_data_key, read_secret, save_provider, save_secret
from news.service.encryption import decrypt
from news.service.models import Base, ReaderDataKey
from news.service.readers import ReaderNotFound, create_reader

MASTER = b"m" * 32
SENTINEL = "sentinel-provider-key-keep-out-of-logs"


def test_credentials_have_reader_scoped_tables(engine: Engine) -> None:
    for name in ("reader_data_key", "secret", "llm_provider"):
        assert name in Base.metadata.tables
        assert Base.metadata.tables[name].info["scope"] == "reader"
    with engine.connect() as connection:
        for name in ("reader_data_key", "secret", "llm_provider"):
            assert connection.execute(text(f"SELECT count(*) FROM {name}")).scalar_one() == 0


def test_provider_and_secret_use_one_wrapped_reader_key(session: Session) -> None:
    reader = create_reader(session, "Ada")
    with capture_logs() as logs:
        secret = save_secret(session, reader.id, "FEED_TOKEN", SENTINEL, lambda: MASTER)
        provider = save_provider(
            session, reader.id, "Local", "https://example.test/v1", SENTINEL, lambda: MASTER
        )
        key = load_data_key(session, reader.id, lambda: MASTER)
        assert read_secret(session, reader.id, secret.id, lambda: MASTER) == SENTINEL
    session.commit()
    session.expire_all()

    assert key != MASTER
    assert secret.encrypted_value != SENTINEL.encode()
    assert provider.encrypted_credential != SENTINEL.encode()
    assert (
        decrypt(
            key, provider.encrypted_credential, f"provider:{reader.id}:{provider.id}".encode()
        ).decode()
        == SENTINEL
    )
    wrapped = session.execute(text("SELECT encrypted_key FROM reader_data_key")).scalar_one()
    assert wrapped != key and wrapped != MASTER
    assert decrypt(MASTER, wrapped, f"data-key:{reader.id}".encode()) == key
    assert SENTINEL not in repr(logs)
    assert session.execute(text("SELECT count(*) FROM reader_data_key")).scalar_one() == 1


def test_wrong_master_key_fails_without_replacing_the_reader_key(session: Session) -> None:
    reader = create_reader(session, "Ada")
    save_secret(session, reader.id, "TOKEN", SENTINEL, lambda: MASTER)
    with capture_logs() as logs, pytest.raises(ValueError, match="Cannot decrypt"):
        save_secret(session, reader.id, "OTHER", SENTINEL, lambda: b"x" * 32)
    assert [entry["event"] for entry in logs] == ["credentials.decrypt_failed"]
    assert SENTINEL not in repr(logs)
    assert session.execute(text("SELECT count(*) FROM secret")).scalar_one() == 1
    assert session.execute(text("SELECT count(*) FROM reader_data_key")).scalar_one() == 1


def test_readers_cannot_read_each_others_secrets_or_use_each_others_keys(session: Session) -> None:
    first, second = create_reader(session, "Ada"), create_reader(session, "Grace")
    secret = save_secret(session, first.id, "TOKEN", SENTINEL, lambda: MASTER)
    save_secret(session, second.id, "TOKEN", SENTINEL, lambda: MASTER)
    first_key = load_data_key(session, first.id, lambda: MASTER)
    second_key = load_data_key(session, second.id, lambda: MASTER)
    assert first_key != second_key
    with capture_logs() as logs, pytest.raises(LookupError):
        read_secret(session, second.id, secret.id, lambda: MASTER)
    assert logs[0]["event"] == "credentials.secret_not_found"
    with pytest.raises(ValueError, match="Cannot decrypt"):
        decrypt(second_key, secret.encrypted_value, f"secret:{first.id}:{secret.id}".encode())


@pytest.mark.parametrize("kind", ["secret", "provider"])
def test_unknown_readers_are_rejected_before_key_creation(session: Session, kind: str) -> None:
    with pytest.raises(ReaderNotFound):
        if kind == "secret":
            save_secret(session, uuid.uuid7(), "TOKEN", SENTINEL, lambda: MASTER)
        else:
            save_provider(
                session, uuid.uuid7(), "Local", "https://example.test", SENTINEL, lambda: MASTER
            )
    assert session.execute(text("SELECT count(*) FROM reader_data_key")).scalar_one() == 0


def test_ciphertexts_cannot_be_swapped_between_secret_records(session: Session) -> None:
    reader = create_reader(session, "Ada")
    first = save_secret(session, reader.id, "ONE", SENTINEL, lambda: MASTER)
    second = save_secret(session, reader.id, "TWO", "another", lambda: MASTER)
    first.encrypted_value = second.encrypted_value
    with capture_logs() as logs, pytest.raises(ValueError, match="Cannot decrypt"):
        read_secret(session, reader.id, first.id, lambda: MASTER)
    assert logs[0]["event"] == "credentials.decrypt_failed"
    assert SENTINEL not in repr(logs)


def test_secret_updates_reuse_key_and_keep_only_ciphertext(session: Session) -> None:
    reader = create_reader(session, "Ada")
    first = save_secret(session, reader.id, "TOKEN", "old", lambda: MASTER)
    original_ciphertext = first.encrypted_value
    second = save_secret(session, reader.id, "TOKEN", SENTINEL, lambda: MASTER)
    assert second.id == first.id
    assert second.encrypted_value != original_ciphertext
    assert read_secret(session, reader.id, first.id, lambda: MASTER) == SENTINEL
    assert len(session.scalars(select(type(first))).all()) == 1


def test_provider_updates_and_identical_names_remain_reader_scoped(session: Session) -> None:
    first, second = create_reader(session, "Ada"), create_reader(session, "Grace")
    first_provider = save_provider(
        session, first.id, "Local", "https://old.test", "old", lambda: MASTER
    )
    provider_id = first_provider.id
    other_provider = save_provider(
        session, second.id, "Local", "https://other.test", "other", lambda: MASTER
    )
    updated = save_provider(
        session, first.id, "Local", "https://new.test", SENTINEL, lambda: MASTER
    )
    session.commit()
    session.expire_all()
    assert updated.id == provider_id
    assert updated.url == "https://new.test"
    assert other_provider.id != updated.id
    assert other_provider.url == "https://other.test"
    key = load_data_key(session, first.id, lambda: MASTER)
    context = f"provider:{first.id}:{updated.id}".encode()
    assert decrypt(key, updated.encrypted_credential, context).decode() == SENTINEL
    with pytest.raises(ValueError, match="Cannot decrypt"):
        decrypt(
            load_data_key(session, second.id, lambda: MASTER), updated.encrypted_credential, context
        )


def test_wrapped_data_keys_cannot_be_swapped_between_readers(session: Session) -> None:
    first, second = create_reader(session, "Ada"), create_reader(session, "Grace")
    save_secret(session, first.id, "TOKEN", SENTINEL, lambda: MASTER)
    save_secret(session, second.id, "TOKEN", "other", lambda: MASTER)
    first_wrapped = session.scalars(
        select(ReaderDataKey).where(ReaderDataKey.reader_id == first.id)
    ).one()
    second_wrapped = session.scalars(
        select(ReaderDataKey).where(ReaderDataKey.reader_id == second.id)
    ).one()
    first_wrapped.encrypted_key = second_wrapped.encrypted_key
    with capture_logs() as logs, pytest.raises(ValueError, match="Cannot decrypt"):
        load_data_key(session, first.id, lambda: MASTER)
    assert logs[0]["event"] == "credentials.decrypt_failed"
