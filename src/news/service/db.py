"""Database engine and migrations (ADR 0013: SQLite by default, Postgres-ready)."""

from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event


def create_engine_for(url: str) -> Engine:
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _configure_sqlite_connection)
    return engine


def _configure_sqlite_connection(dbapi_connection: Any, _record: Any) -> None:
    # WAL lets the CLI and the server process share the file (ADR 0017); SQLite leaves foreign
    # keys off unless asked.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def alembic_config() -> Config:
    # Built in code from the package, so an installed wheel migrates without a source checkout.
    config = Config()
    config.set_main_option("script_location", "news:migrations")
    return config


def migrate(engine: Engine) -> None:
    config = alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
