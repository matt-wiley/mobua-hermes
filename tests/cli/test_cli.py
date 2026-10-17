import json
import pwd
import sqlite3
import uuid
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
import typer
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from news.cli.main import app
from news.service.db import create_engine_for
from news.service.models import (
    Base,
    Channel,
    ChannelRevision,
    Plugin,
    PluginBinding,
    PluginRevision,
    Reader,
)
from tests.service.factories import URL_PLUGIN_MANIFEST

runner = CliRunner()


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "news.db"


@pytest.fixture
def database_url(database_path: Path) -> str:
    url = f"sqlite:///{database_path}"
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
    database_url: str, plugin_files: tuple[Path, Path], log_file: Path
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
    assert result.stderr.splitlines() == [
        "bindings.0.url: 'url' is a required property",
        f"Logged to {log_file}.",
    ]
    assert result.stdout == ""
    # A separate engine sees only what the command committed (AC-20).
    with open_session(database_url) as session:
        assert session.scalar(select(func.count()).select_from(ChannelRevision)) == 1
        assert session.scalar(select(func.count()).select_from(PluginBinding)) == 0
        stored_channel = session.get_one(Channel, uuid.UUID(channel))
        assert stored_channel.current_revision is not None
        assert stored_channel.current_revision.number == 1


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


def test_invalid_manifest_reports_field_errors(
    database_url: str, tmp_path: Path, log_file: Path
) -> None:
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
    assert result.stderr.splitlines()[-1] == f"Logged to {log_file}."


def test_binding_to_an_unknown_channel_is_reported(
    database_url: str, plugin_files: tuple[Path, Path], log_file: Path
) -> None:
    reader, plugin_revision, _ = setup_channel(database_url, plugin_files)
    unknown = str(uuid.uuid7())

    result = news(
        database_url,
        "channel",
        "bind",
        "--reader",
        reader,
        "--channel",
        unknown,
        "--plugin-revision",
        plugin_revision,
        "--config",
        '{"url": "https://x"}',
    )

    assert result.exit_code == 1
    assert result.stderr.splitlines() == [
        f"no Channel {unknown} for this Reader",
        f"Logged to {log_file}.",
    ]


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
    database_url: str, log_file: Path
) -> None:
    unknown = str(uuid.uuid7())

    result = news(database_url, "channel", "create", "--reader", unknown, "Local")

    assert result.exit_code == 1
    assert result.stderr.splitlines() == [f"no Reader {unknown}", f"Logged to {log_file}."]
    assert result.stdout == ""
    assert isinstance(result.exception, SystemExit)
    assert [line["event"] for line in log_lines(log_file)] == ["reader.not_found"]


def test_creating_a_plugin_for_an_unknown_reader_is_reported_without_a_traceback(
    database_url: str, plugin_files: tuple[Path, Path], log_file: Path
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
    assert result.stderr.splitlines() == [f"no Reader {unknown}", f"Logged to {log_file}."]
    assert result.stdout == ""
    assert isinstance(result.exception, SystemExit)
    assert [line["event"] for line in log_lines(log_file)] == ["reader.not_found"]


class WriteLock:
    """SQLite's write lock, held from a second connection until released."""

    def __init__(self, database: Path) -> None:
        self._connection: sqlite3.Connection | None = sqlite3.connect(
            database, isolation_level=None
        )
        self._connection.execute("BEGIN IMMEDIATE")

    def release(self) -> None:
        if self._connection is not None:
            self._connection.rollback()
            self._connection.close()
            self._connection = None


@pytest.fixture
def write_lock(database_path: Path, database_url: str) -> Iterator[WriteLock]:
    del database_url  # Requested only so the database is migrated, in WAL mode, before locking.
    lock = WriteLock(database_path)
    try:
        yield lock
    finally:
        lock.release()


@pytest.fixture
def impatient_url(database_url: str) -> str:
    """A URL whose connections give up on a held lock after 0.1 s instead of SQLite's 5 s."""
    return f"{database_url}?timeout=0.1"


@pytest.mark.usefixtures("write_lock")
def test_an_unexpected_error_is_logged_with_its_traceback_and_reported_in_one_line(
    impatient_url: str, log_file: Path
) -> None:
    result = news(impatient_url, "reader", "create", "Ada")

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert result.stderr.splitlines() == [
        "Unexpected error: OperationalError: (sqlite3.OperationalError) database is locked. "
        f"Details logged to {log_file}."
    ]
    assert "Traceback" not in result.output
    [entry] = [line for line in log_lines(log_file) if line["event"] == "cli.unexpected_error"]
    assert entry["level"] == "error"
    assert entry["command"] == "reader create"
    assert entry["exception"].startswith("Traceback")
    assert "database is locked" in entry["exception"]


def test_a_command_that_fails_at_flush_prints_nothing_and_saves_nothing(
    database_url: str, impatient_url: str, write_lock: WriteLock
) -> None:
    result = news(impatient_url, "reader", "create", "Ada")
    write_lock.release()

    assert result.exit_code == 1
    assert result.stdout == ""
    assert row_count(database_url, Reader) == 0


def test_an_unexpected_error_before_the_command_runs_is_reported_the_same_way(
    log_file: Path,
) -> None:
    result = news("not a database url", "reader", "create", "Ada")

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    [line] = result.stderr.splitlines()
    assert line.startswith("Unexpected error: ArgumentError: ")
    assert line.endswith(f"Details logged to {log_file}.")
    [entry] = log_lines(log_file)
    assert entry["event"] == "cli.unexpected_error"
    assert entry["command"] == "reader"


def test_an_error_before_the_log_file_is_known_is_reported_without_a_pointer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # With no HOME and no entry in the user database, Path.home() raises RuntimeError.
    monkeypatch.delenv("NEWS_CLI_LOG_FILE")
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.delenv("HOME")

    def no_such_user(uid: int) -> pwd.struct_passwd:
        raise KeyError(f"getpwuid(): uid not found: {uid}")

    monkeypatch.setattr(pwd, "getpwuid", no_such_user)

    result = news(f"sqlite:///{tmp_path / 'fresh.db'}", "db", "upgrade")

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert result.stdout == ""
    assert result.stderr.splitlines() == [
        "Unexpected error: RuntimeError: Could not determine home directory. "
        "No log file was open to record it."
    ]


def write_lock_is_free(database: Path) -> bool:
    connection = sqlite3.connect(database, isolation_level=None, timeout=0)
    try:
        connection.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError:
        return False
    else:
        connection.rollback()
        return True
    finally:
        connection.close()


def writing_command(
    command: str, ids: tuple[str, str, str], plugin_files: tuple[Path, Path]
) -> list[str]:
    reader, plugin_revision, channel = ids
    manifest, code = plugin_files
    return {
        "reader": ["reader", "create", "Ada"],
        "plugin": [
            *["plugin", "create", "--reader", reader],
            *["--manifest", str(manifest), "--code", str(code)],
        ],
        "channel": ["channel", "create", "--reader", reader, "Local"],
        "bind": [
            *["channel", "bind", "--reader", reader, "--channel", channel],
            *["--plugin-revision", plugin_revision, "--config", '{"url": "https://x"}'],
        ],
    }[command]


def fail_commits_that_insert_into(database: Path, table: str) -> None:
    """Make every transaction that inserts into `table` fail at COMMIT, after its flush succeeds.

    SQLite checks a deferred foreign key only at COMMIT, so a trigger that writes a dangling
    one lets the command's own INSERTs succeed and its commit fail.
    """
    connection = sqlite3.connect(database)
    try:
        connection.executescript(
            f"""
            CREATE TABLE commit_guard_parent (id INTEGER PRIMARY KEY);
            CREATE TABLE commit_guard (
                parent_id INTEGER REFERENCES commit_guard_parent (id) DEFERRABLE INITIALLY DEFERRED
            );
            CREATE TRIGGER commit_guard_on_{table} AFTER INSERT ON {table}
            BEGIN
                INSERT INTO commit_guard (parent_id) VALUES (1);
            END;
            """
        )
    finally:
        connection.close()


# Each writing command and the models it inserts into.
MODELS_INSERTED_BY: dict[str, tuple[type[Base], ...]] = {
    "reader": (Reader,),
    "plugin": (Plugin, PluginRevision),
    "channel": (Channel,),
    "bind": (ChannelRevision,),
}


def row_count(database_url: str, model: type[Base]) -> int:
    with open_session(database_url) as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


@pytest.mark.parametrize("command", MODELS_INSERTED_BY)
def test_a_command_whose_commit_fails_prints_nothing_and_saves_nothing(
    command: str,
    database_path: Path,
    database_url: str,
    plugin_files: tuple[Path, Path],
    log_file: Path,
) -> None:
    ids = setup_channel(database_url, plugin_files)
    models = MODELS_INSERTED_BY[command]
    rows_before = [row_count(database_url, model) for model in models]
    fail_commits_that_insert_into(database_path, models[0].__tablename__)

    result = news(database_url, *writing_command(command, ids, plugin_files))

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert result.stdout == ""
    assert result.stderr.splitlines() == [
        "Unexpected error: IntegrityError: (sqlite3.IntegrityError) FOREIGN KEY constraint "
        f"failed. Details logged to {log_file}."
    ]
    [entry] = [line for line in log_lines(log_file) if line["event"] == "cli.unexpected_error"]
    # SQLAlchemy's commit() flushes first; do_commit is the COMMIT statement itself.
    assert "do_commit" in entry["exception"]
    assert [row_count(database_url, model) for model in models] == rows_before


@pytest.mark.parametrize("command", MODELS_INSERTED_BY)
def test_output_is_printed_only_after_the_transaction_has_committed(
    command: str,
    database_path: Path,
    database_url: str,
    plugin_files: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = setup_channel(database_url, plugin_files)
    lock_free_when_printing: list[bool] = []
    echo = typer.echo

    def spying_echo(*echo_args: Any, **echo_kwargs: Any) -> None:
        lock_free_when_printing.append(write_lock_is_free(database_path))
        echo(*echo_args, **echo_kwargs)

    monkeypatch.setattr(typer, "echo", spying_echo)

    result = news(database_url, *writing_command(command, ids, plugin_files))

    assert result.exit_code == 0, result.output
    assert lock_free_when_printing == [True]
