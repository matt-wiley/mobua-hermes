import json
import uuid
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

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
    return str(uuid.UUID(result.stdout.strip()))


def bind(database_url: str, reader: str, channel: str, plugin_revision: str, config: str) -> Result:
    return news(
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
        config,
    )


def log_lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


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


def test_log_lines_go_to_the_file_named_by_the_environment_and_stdout_has_none(
    database_url: str, plugin_files: tuple[Path, Path], log_file: Path
) -> None:
    reader, plugin_revision, channel = setup_channel(database_url, plugin_files)

    result = bind(database_url, reader, channel, plugin_revision, "{}")

    assert result.exit_code == 1
    assert result.stdout == ""
    [line] = log_lines(log_file)
    assert line["event"] == "channel_revision.rejected"
    assert line["level"] == "info"
    assert line["channel_id"] == channel
    assert "timestamp" in line


def test_the_log_file_option_wins_over_the_environment(
    database_url: str, plugin_files: tuple[Path, Path], log_file: Path, tmp_path: Path
) -> None:
    reader, plugin_revision, channel = setup_channel(database_url, plugin_files)
    log_file.unlink()
    option_file = tmp_path / "option" / "cli.log"

    result = runner.invoke(
        app,
        [
            "--database-url",
            database_url,
            "--log-file",
            str(option_file),
            *["channel", "bind", "--reader", reader, "--channel", channel],
            *["--plugin-revision", plugin_revision, "--config", "{}"],
        ],
    )

    assert result.exit_code == 1
    assert [line["event"] for line in log_lines(option_file)] == ["channel_revision.rejected"]
    assert not log_file.exists()


def test_logs_default_to_the_xdg_state_directory(
    database_url: str,
    plugin_files: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader, plugin_revision, channel = setup_channel(database_url, plugin_files)
    monkeypatch.delenv("NEWS_CLI_LOG_FILE")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    bind(database_url, reader, channel, plugin_revision, "{}")

    lines = log_lines(tmp_path / "state" / "news" / "cli.log")
    assert [line["event"] for line in lines] == ["channel_revision.rejected"]


def test_logs_fall_back_to_local_state_under_home_without_xdg_state_home(
    database_url: str,
    plugin_files: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader, plugin_revision, channel = setup_channel(database_url, plugin_files)
    monkeypatch.delenv("NEWS_CLI_LOG_FILE")
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    bind(database_url, reader, channel, plugin_revision, "{}")

    lines = log_lines(tmp_path / "home" / ".local" / "state" / "news" / "cli.log")
    assert [line["event"] for line in lines] == ["channel_revision.rejected"]


def test_a_second_command_appends_to_the_log_file(
    database_url: str, plugin_files: tuple[Path, Path], log_file: Path
) -> None:
    reader, plugin_revision, channel = setup_channel(database_url, plugin_files)
    bind(database_url, reader, channel, plugin_revision, "{}")
    [first] = log_file.read_text().splitlines()

    bind(database_url, reader, channel, plugin_revision, "{}")

    lines = log_file.read_text().splitlines()
    assert len(lines) == 2
    assert lines[0] == first
    for line in log_lines(log_file):
        assert {"event", "level", "timestamp"} <= line.keys()


@pytest.fixture
def read_only_dir(tmp_path: Path) -> Iterator[Path]:
    directory = tmp_path / "ro"
    directory.mkdir(mode=0o500)
    yield directory
    directory.chmod(0o700)


def test_an_unopenable_log_file_fails_before_touching_the_database(
    tmp_path: Path, read_only_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = read_only_dir / "logs" / "cli.log"
    monkeypatch.setenv("NEWS_CLI_LOG_FILE", str(path))
    database = tmp_path / "fresh.db"

    result = news(f"sqlite:///{database}", "db", "upgrade")

    assert result.exit_code == 1
    assert result.stdout == ""
    assert str(path) in result.stderr
    assert "Permission denied" in result.stderr
    assert "--log-file" in result.stderr
    assert "NEWS_CLI_LOG_FILE" in result.stderr
    assert not database.exists()


def test_a_log_file_path_that_is_a_directory_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "a-directory"
    path.mkdir()
    monkeypatch.setenv("NEWS_CLI_LOG_FILE", str(path))
    database = tmp_path / "fresh.db"

    result = news(f"sqlite:///{database}", "db", "upgrade")

    assert result.exit_code == 1
    assert str(path) in result.stderr
    assert not database.exists()


def test_creating_a_channel_for_an_unknown_reader_is_reported_without_a_traceback(
    database_url: str,
) -> None:
    unknown = str(uuid.uuid7())

    result = news(database_url, "channel", "create", "--reader", unknown, "Local")

    assert result.exit_code == 1
    assert result.stderr.splitlines()[0] == f"no Reader {unknown}"
    assert result.stdout == ""
    assert isinstance(result.exception, SystemExit)


def test_creating_a_plugin_for_an_unknown_reader_is_reported_without_a_traceback(
    database_url: str, plugin_files: tuple[Path, Path]
) -> None:
    manifest, code = plugin_files
    unknown = str(uuid.uuid7())

    result = news(
        database_url,
        "plugin",
        "create",
        "--reader",
        unknown,
        "--manifest",
        str(manifest),
        "--code",
        str(code),
    )

    assert result.exit_code == 1
    assert result.stderr.splitlines()[0] == f"no Reader {unknown}"
    assert result.stdout == ""
    assert isinstance(result.exception, SystemExit)
