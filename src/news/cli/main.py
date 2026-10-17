"""The `news` command line: thin commands over the service layer (ADR 0017)."""

import json
import os
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any, TextIO

import typer
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from news.cli.log_file import resolve_log_path
from news.service.binding_config import ConfigError
from news.service.channels import (
    ChannelNotFound,
    ChannelRevisionRejected,
    bind_plugin,
    create_channel,
)
from news.service.db import create_engine_for, migrate
from news.service.manifest import ManifestError
from news.service.observability import configure_logging
from news.service.plugins import create_plugin
from news.service.readers import create_reader

app = typer.Typer(no_args_is_help=True, help="Manage the news app's data.")
db_app = typer.Typer(no_args_is_help=True, help="The database.")
reader_app = typer.Typer(no_args_is_help=True, help="Readers.")
plugin_app = typer.Typer(no_args_is_help=True, help="Plugins and their Revisions.")
channel_app = typer.Typer(no_args_is_help=True, help="Channels and their Plugin Bindings.")
app.add_typer(db_app, name="db")
app.add_typer(reader_app, name="reader")
app.add_typer(plugin_app, name="plugin")
app.add_typer(channel_app, name="channel")

ReaderOption = Annotated[uuid.UUID, typer.Option("--reader", help="The Reader acting.")]


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
    engine: Engine = ctx.obj
    with Session(engine) as session, session.begin():
        yield session


def _fail(errors: list[ConfigError]) -> typer.Exit:
    for error in errors:
        typer.echo(f"{error.field or '(root)'}: {error.message}", err=True)
    return typer.Exit(code=1)


def _parse_config(value: str) -> dict[str, Any]:
    try:
        config = json.loads(value)
    except json.JSONDecodeError as error:
        raise typer.BadParameter(f"not valid JSON: {error}") from error
    if not isinstance(config, dict):
        raise typer.BadParameter("must be a JSON object")
    return config  # pyright: ignore[reportUnknownVariableType]


@db_app.command("upgrade")
def db_upgrade(ctx: typer.Context) -> None:
    """Apply all database migrations."""
    migrate(ctx.obj)
    typer.echo("Database is up to date.")


@reader_app.command("create")
def reader_create(ctx: typer.Context, name: str) -> None:
    """Create a Reader and print its id."""
    with _transaction(ctx) as session:
        reader = create_reader(session, name)
        typer.echo(reader.id)


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
    try:
        with _transaction(ctx) as session:
            revision = create_plugin(session, reader, manifest.read_text(), files)
            typer.echo(revision.id)
    except ManifestError as error:
        raise _fail(error.errors) from error


@channel_app.command("create")
def channel_create(ctx: typer.Context, reader: ReaderOption, name: str) -> None:
    """Create a Channel with no Plugin Bindings and print its id."""
    with _transaction(ctx) as session:
        channel = create_channel(session, reader, name)
        typer.echo(channel.id)


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
    try:
        with _transaction(ctx) as session:
            revision = bind_plugin(session, reader, channel, plugin_revision, config)
            typer.echo(f"Saved Channel Revision {revision.number}.")
    except ChannelRevisionRejected as error:
        raise _fail(error.errors) from error
    except ChannelNotFound as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
