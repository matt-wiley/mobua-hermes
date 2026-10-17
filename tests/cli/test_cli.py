import uuid
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from news.cli.main import app
from news.service.db import create_engine_for
from news.service.models import ChannelRevision, PluginRevision
from tests.service.factories import URL_PLUGIN_MANIFEST

runner = CliRunner()


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    url = f"sqlite:///{tmp_path / 'news.db'}"
    result = runner.invoke(app, ["--database-url", url, "db", "upgrade"])
    assert result.exit_code == 0, result.output
    return url


@pytest.fixture
def plugin_files(tmp_path: Path) -> tuple[Path, Path]:
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(URL_PLUGIN_MANIFEST)
    code = tmp_path / "main.py"
    code.write_text("print('hi')\n")
    return manifest, code


@contextmanager
def open_session(database_url: str) -> Generator[Session]:
    engine = create_engine_for(database_url)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def news(database_url: str, *args: str) -> Result:
    return runner.invoke(app, ["--database-url", database_url, *args])


def created_id(result: Result) -> str:
    assert result.exit_code == 0, result.output
    return result.stdout.strip().splitlines()[-1]


def setup_channel(database_url: str, plugin_files: tuple[Path, Path]) -> tuple[str, str, str]:
    manifest, code = plugin_files
    reader = created_id(news(database_url, "reader", "create", "Ada"))
    plugin_revision = created_id(
        news(
            database_url,
            "plugin",
            "create",
            "--reader",
            reader,
            "--manifest",
            str(manifest),
            "--code",
            str(code),
        )
    )
    channel = created_id(news(database_url, "channel", "create", "--reader", reader, "Local"))
    return reader, plugin_revision, channel


def test_plugin_is_created_from_a_manifest_and_code_files(
    database_url: str, plugin_files: tuple[Path, Path]
) -> None:
    _, plugin_revision, _ = setup_channel(database_url, plugin_files)

    with open_session(database_url) as session:
        revision = session.get_one(PluginRevision, uuid.UUID(plugin_revision))
        assert revision.code == {"main.py": "print('hi')\n"}
        assert revision.manifest == URL_PLUGIN_MANIFEST


def test_binding_with_valid_config_creates_a_channel_revision(
    database_url: str, plugin_files: tuple[Path, Path]
) -> None:
    reader, plugin_revision, channel = setup_channel(database_url, plugin_files)

    result = news(
        database_url,
        "channel",
        "bind",
        "--reader",
        reader,
        "--channel",
        channel,
        "--plugin-revision",
        plugin_revision,
        "--config",
        '{"url": "https://example.com/rss"}',
    )

    assert result.exit_code == 0, result.output
    assert "Channel Revision 2" in result.stdout


def test_binding_with_invalid_config_reports_field_errors_and_saves_nothing(
    database_url: str, plugin_files: tuple[Path, Path]
) -> None:
    reader, plugin_revision, channel = setup_channel(database_url, plugin_files)

    result = news(
        database_url,
        "channel",
        "bind",
        "--reader",
        reader,
        "--channel",
        channel,
        "--plugin-revision",
        plugin_revision,
        "--config",
        "{}",
    )

    assert result.exit_code == 1
    assert "bindings.0.url: 'url' is a required property" in result.stderr
    with open_session(database_url) as session:
        count = session.scalar(select(func.count()).select_from(ChannelRevision))
    assert count == 1


def test_config_that_is_not_json_is_a_usage_error(
    database_url: str, plugin_files: tuple[Path, Path]
) -> None:
    reader, plugin_revision, channel = setup_channel(database_url, plugin_files)

    result = news(
        database_url,
        "channel",
        "bind",
        "--reader",
        reader,
        "--channel",
        channel,
        "--plugin-revision",
        plugin_revision,
        "--config",
        "{url:",
    )

    assert result.exit_code == 2
    assert "not valid JSON" in result.stderr


def test_config_that_is_not_a_json_object_is_a_usage_error(
    database_url: str, plugin_files: tuple[Path, Path]
) -> None:
    reader, plugin_revision, channel = setup_channel(database_url, plugin_files)

    result = news(
        database_url,
        "channel",
        "bind",
        "--reader",
        reader,
        "--channel",
        channel,
        "--plugin-revision",
        plugin_revision,
        "--config",
        "[1]",
    )

    assert result.exit_code == 2
    assert "must be a JSON object" in result.stderr


def test_invalid_manifest_reports_field_errors(database_url: str, tmp_path: Path) -> None:
    reader = created_id(news(database_url, "reader", "create", "Ada"))
    manifest = tmp_path / "bad.toml"
    manifest.write_text('name = "x"\ncommand = "run"\ntimeout = 0\n[config_schema]\n')
    code = tmp_path / "main.py"
    code.write_text("")

    result = news(
        database_url,
        "plugin",
        "create",
        "--reader",
        reader,
        "--manifest",
        str(manifest),
        "--code",
        str(code),
    )

    assert result.exit_code == 1
    assert "timeout:" in result.stderr


def test_binding_to_an_unknown_channel_is_reported(
    database_url: str, plugin_files: tuple[Path, Path]
) -> None:
    reader, plugin_revision, _ = setup_channel(database_url, plugin_files)

    result = news(
        database_url,
        "channel",
        "bind",
        "--reader",
        reader,
        "--channel",
        str(uuid.uuid7()),
        "--plugin-revision",
        plugin_revision,
        "--config",
        '{"url": "https://x"}',
    )

    assert result.exit_code == 1
    assert "no Channel" in result.stderr
