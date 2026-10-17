"""The `news` command line: thin commands over the service layer (ADR 0017)."""

import json
import os
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any, TextIO, cast

import structlog
import typer
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from typer.core import TyperGroup

from news.cli.log_file import resolve_log_path
from news.cli.messages import EXPECTED_FAILURES, expected_failure_lines, unexpected_error_line
from news.service.channels import bind_plugin, create_channel
from news.service.credentials import save_provider, save_secret
from news.service.db import create_engine_for, migrate
from news.service.keys import generate_master_key, read_master_key
from news.service.observability import configure_logging
from news.service.plugins import create_plugin
from news.service.readers import create_reader

log = structlog.get_logger(__name__)

# Keys in Click's `ctx.meta`, which every context of one invocation shares.
_LOG_PATH = "news.log_path"
# Only the names resolved so far: a failure in the root callback records just the group.
_COMMAND_NAMES = "news.command_names"


# These methods receive Typer's vendored Click Context, which has no public import path,
# hence `Any`.
class _CommandGroup(TyperGroup):
    """Records the names of the subcommands being run, e.g. `channel bind`."""

    def resolve_command(self, ctx: Any, args: list[str]) -> Any:
        name, command, rest = super().resolve_command(ctx, args)
        ctx.meta.setdefault(_COMMAND_NAMES, []).append(name)
        return name, command, rest


class _TopLevelGroup(_CommandGroup):
    """Reports every command's failures in one place, pointing to the log file."""

    def invoke(self, ctx: Any) -> Any:
        try:
            return super().invoke(ctx)
        except typer.Exit, typer.Abort, typer.TyperException:
            raise
        except EXPECTED_FAILURES as error:
            for line in expected_failure_lines(error, ctx.meta[_LOG_PATH]):
                typer.echo(line, err=True)
            raise typer.Exit(code=1) from error
        except Exception as error:
            # The path is unset only if working it out failed, before logging was configured.
            log_path: Path | None = ctx.meta.get(_LOG_PATH)
            if log_path is not None:
                log.error(
                    "cli.unexpected_error",
                    command=" ".join(ctx.meta.get(_COMMAND_NAMES, [])),
                    exc_info=error,
                )
            typer.echo(unexpected_error_line(error, log_path), err=True)
            raise typer.Exit(code=1) from error


app = typer.Typer(cls=_TopLevelGroup, no_args_is_help=True, help="Manage the news app's data.")
db_app = typer.Typer(cls=_CommandGroup, no_args_is_help=True, help="The database.")
reader_app = typer.Typer(cls=_CommandGroup, no_args_is_help=True, help="Readers.")
plugin_app = typer.Typer(
    cls=_CommandGroup, no_args_is_help=True, help="Plugins and their Revisions."
)
channel_app = typer.Typer(
    cls=_CommandGroup, no_args_is_help=True, help="Channels and their Plugin Bindings."
)
app.add_typer(db_app, name="db")
app.add_typer(reader_app, name="reader")
app.add_typer(plugin_app, name="plugin")
app.add_typer(channel_app, name="channel")
secret_app = typer.Typer(cls=_CommandGroup, no_args_is_help=True, help="Encrypted Source Secrets.")
provider_app = typer.Typer(cls=_CommandGroup, no_args_is_help=True, help="LLM Providers.")
key_app = typer.Typer(cls=_CommandGroup, no_args_is_help=True, help="Initial Master Key setup.")
app.add_typer(secret_app, name="secret")
app.add_typer(provider_app, name="provider")
app.add_typer(key_app, name="key")

ReaderOption = Annotated[uuid.UUID, typer.Option("--reader", help="The Reader acting.")]


@key_app.command("generate")
def key_generate(ctx: typer.Context) -> None:
    """Print a new Master Key once. Save it outside the database before adding credentials."""
    with _transaction(ctx) as session:
        encoded = generate_master_key(session, os.environ)
    typer.echo(encoded)


@secret_app.command("set")
def secret_set(ctx: typer.Context, reader: ReaderOption, name: str) -> None:
    """Add or replace a Secret, prompting privately for its value."""
    value = typer.prompt("Secret value", hide_input=True, confirmation_prompt=True)
    with _transaction(ctx) as session:
        secret_id = save_secret(
            session, reader, name, value, lambda: read_master_key(os.environ)
        ).id
    typer.echo(secret_id)


@provider_app.command("add")
def provider_add(
    ctx: typer.Context,
    reader: ReaderOption,
    name: str,
    url: Annotated[str, typer.Option("--url", help="Provider API base URL.")],
) -> None:
    """Add or update a named LLM Provider, prompting privately for its credential."""
    api_key = typer.prompt("Provider API key", hide_input=True, confirmation_prompt=True)
    with _transaction(ctx) as session:
        provider_id = save_provider(
            session, reader, name, url, api_key, lambda: read_master_key(os.environ)
        ).id
    typer.echo(provider_id)


@app.callback()
def main(
    ctx: typer.Context,
    database_url: Annotated[
        str, typer.Option(envvar="NEWS_DATABASE_URL", help="SQLAlchemy database URL.")
    ] = "sqlite:///news.db",
    log_file: Annotated[
        Path | None,
        typer.Option(
            envvar="NEWS_CLI_LOG_FILE",
            help="Where to append JSON log lines. [default: $XDG_STATE_HOME/news/cli.log]",
        ),
    ] = None,
) -> None:
    configure_logging(stream=_open_log_file(ctx, log_file))
    engine = create_engine_for(database_url)
    ctx.call_on_close(engine.dispose)
    ctx.obj = engine


def _open_log_file(ctx: typer.Context, log_file: Path | None) -> TextIO:
    """Open the log file for appending, or exit before any work if it can't be opened."""
    path = resolve_log_path(log_file, os.environ.get("XDG_STATE_HOME"), Path.home())
    ctx.meta[_LOG_PATH] = path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        stream = path.open("a", encoding="utf-8")
    except OSError as error:
        typer.echo(
            f"Cannot open log file {path}: {error.strerror}. "
            "Choose another with --log-file or NEWS_CLI_LOG_FILE.",
            err=True,
        )
        raise typer.Exit(code=1) from error
    return ctx.with_resource(stream)


@contextmanager
def _transaction(ctx: typer.Context) -> Generator[Session]:
    """Commit on exit. Commands print their results after it, so output means committed."""
    engine: Engine = ctx.obj
    with Session(engine) as session, session.begin():
        yield session


def _parse_config(value: str) -> dict[str, Any]:
    try:
        config = json.loads(value)
    except json.JSONDecodeError as error:
        raise typer.BadParameter(f"not valid JSON: {error}") from error
    if not isinstance(config, dict):
        raise typer.BadParameter("must be a JSON object")
    return cast(dict[str, Any], config)


@db_app.command("upgrade")
def db_upgrade(ctx: typer.Context) -> None:
    """Apply all database migrations."""
    migrate(ctx.obj)
    typer.echo("Database is up to date.")


@reader_app.command("create")
def reader_create(ctx: typer.Context, name: str) -> None:
    """Create a Reader and print its id."""
    with _transaction(ctx) as session:
        reader_id = create_reader(session, name).id
    typer.echo(reader_id)


@plugin_app.command("create")
def plugin_create(
    ctx: typer.Context,
    reader: ReaderOption,
    manifest: Annotated[Path, typer.Option(exists=True, dir_okay=False, help="Manifest TOML.")],
    code: Annotated[
        list[Path], typer.Option(exists=True, dir_okay=False, help="A code file; repeatable.")
    ],
) -> None:
    """Create a Plugin from a Manifest and code files, and print its first Revision's id."""
    files = {path.name: path.read_text() for path in code}
    with _transaction(ctx) as session:
        revision_id = create_plugin(session, reader, manifest.read_text(), files).id
    typer.echo(revision_id)


@channel_app.command("create")
def channel_create(ctx: typer.Context, reader: ReaderOption, name: str) -> None:
    """Create a Channel with no Plugin Bindings and print its id."""
    with _transaction(ctx) as session:
        channel_id = create_channel(session, reader, name).id
    typer.echo(channel_id)


@channel_app.command("bind")
def channel_bind(
    ctx: typer.Context,
    reader: ReaderOption,
    channel: Annotated[uuid.UUID, typer.Option(help="The Channel to bind into.")],
    plugin_revision: Annotated[uuid.UUID, typer.Option(help="The exact Plugin Revision.")],
    config: Annotated[
        dict[str, Any],
        typer.Option(parser=_parse_config, help="The Binding's config, as a JSON object."),
    ],
) -> None:
    """Bind a Plugin Revision into a Channel, creating a new Channel Revision."""
    with _transaction(ctx) as session:
        revision_number = bind_plugin(session, reader, channel, plugin_revision, config).number
    typer.echo(f"Saved Channel Revision {revision_number}.")
