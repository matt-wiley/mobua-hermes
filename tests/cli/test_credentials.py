import base64
import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from news.cli.main import app
from news.service.credentials import load_data_key, read_secret
from news.service.db import create_engine_for, migrate
from news.service.encryption import decrypt
from news.service.models import LLMProvider, Secret
from news.service.readers import create_reader

MASTER = b"m" * 32
SENTINEL = "sentinel-cli-provider-key"
runner = CliRunner()


@pytest.fixture
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, uuid.UUID]:
    url = f"sqlite:///{tmp_path / 'news.db'}"
    engine = create_engine_for(url)
    migrate(engine)
    with Session(engine) as session, session.begin():
        reader_id = create_reader(session, "Ada").id
    engine.dispose()
    monkeypatch.setenv("NEWS_DATABASE_URL", url)
    monkeypatch.delenv("NEWS_MASTER_KEY", raising=False)
    monkeypatch.delenv("NEWS_MASTER_KEY_FILE", raising=False)
    return url, reader_id


def test_cli_saves_credentials_without_echoing_or_logging_them(
    database: tuple[str, uuid.UUID],
    monkeypatch: pytest.MonkeyPatch,
    log_file: Path,
) -> None:
    url, reader_id = database
    monkeypatch.setenv("NEWS_MASTER_KEY", base64.urlsafe_b64encode(MASTER).decode())
    secret_result = runner.invoke(
        app,
        ["secret", "set", "--reader", str(reader_id), "FEED_TOKEN"],
        input=SENTINEL + "\n" + SENTINEL + "\n",
    )
    provider_result = runner.invoke(
        app,
        [
            "provider",
            "add",
            "--reader",
            str(reader_id),
            "--url",
            "https://example.test/v1",
            "Local",
        ],
        input=SENTINEL + "\n" + SENTINEL + "\n",
    )
    assert secret_result.exit_code == 0, secret_result.output
    assert provider_result.exit_code == 0, provider_result.output
    assert SENTINEL not in secret_result.output + provider_result.output + log_file.read_text()
    engine = create_engine_for(url)
    with Session(engine) as session:
        secret = session.scalars(select(Secret)).one()
        provider = session.scalars(select(LLMProvider)).one()
        assert str(secret.id) in secret_result.stdout
        assert str(provider.id) in provider_result.stdout
        assert read_secret(session, reader_id, secret.id, lambda: MASTER) == SENTINEL
        key = load_data_key(session, reader_id, lambda: MASTER)
        assert (
            decrypt(
                key, provider.encrypted_credential, f"provider:{reader_id}:{provider.id}".encode()
            ).decode()
            == SENTINEL
        )
    engine.dispose()
    assert SENTINEL.encode() not in Path(url.removeprefix("sqlite:///")).read_bytes()


def test_first_run_generation_prints_one_key_and_stores_nothing(
    database: tuple[str, uuid.UUID],
    monkeypatch: pytest.MonkeyPatch,
    log_file: Path,
) -> None:
    url, _ = database
    result = runner.invoke(app, ["key", "generate"])
    assert result.exit_code == 0, result.output
    [encoded] = result.stdout.splitlines()
    assert len(base64.urlsafe_b64decode(encoded)) == 32
    assert encoded not in log_file.read_text()
    assert "NEWS_MASTER_KEY" not in os.environ
    engine = create_engine_for(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM reader_data_key")).scalar_one() == 0
    engine.dispose()
    monkeypatch.setenv("NEWS_MASTER_KEY", encoded)
    second = runner.invoke(app, ["key", "generate"])
    assert second.exit_code == 1
    assert second.stdout == ""


@pytest.mark.parametrize("wrong_key", [False, True])
def test_saving_with_a_missing_or_wrong_key_leaves_credentials_unchanged(
    database: tuple[str, uuid.UUID],
    monkeypatch: pytest.MonkeyPatch,
    log_file: Path,
    wrong_key: bool,
) -> None:
    url, reader_id = database
    args = ["secret", "set", "--reader", str(reader_id), "TOKEN"]
    if wrong_key:
        monkeypatch.setenv("NEWS_MASTER_KEY", base64.urlsafe_b64encode(MASTER).decode())
        assert runner.invoke(app, args, input="old\nold\n").exit_code == 0
        monkeypatch.setenv("NEWS_MASTER_KEY", base64.urlsafe_b64encode(b"x" * 32).decode())
    result = runner.invoke(app, args, input=SENTINEL + "\n" + SENTINEL + "\n")
    assert result.exit_code == 1
    assert "Logged to" in result.stderr
    assert SENTINEL not in result.output + log_file.read_text()
    engine = create_engine_for(url)
    with Session(engine) as session:
        secrets = session.scalars(select(Secret)).all()
        assert len(secrets) == int(wrong_key)
        if wrong_key:
            assert read_secret(session, reader_id, secrets[0].id, lambda: MASTER) == "old"
    engine.dispose()


def test_generation_refuses_to_replace_a_lost_key(
    database: tuple[str, uuid.UUID], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, reader_id = database
    monkeypatch.setenv("NEWS_MASTER_KEY", base64.urlsafe_b64encode(MASTER).decode())
    assert (
        runner.invoke(
            app, ["secret", "set", "--reader", str(reader_id), "TOKEN"], input="old\nold\n"
        ).exit_code
        == 0
    )
    monkeypatch.delenv("NEWS_MASTER_KEY")
    result = runner.invoke(app, ["key", "generate"])
    assert result.exit_code == 1
    assert "already" in result.stderr
    assert result.stdout == ""
