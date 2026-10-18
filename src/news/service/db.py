"""Database engine and migrations (ADR 0013: SQLite by default, Postgres-ready)."""

from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event, make_url


def create_engine_for(url: str) -> Engine:
    # A database error may reach the CLI traceback log; bound values include saved source
    # and credentials, so SQLAlchemy must omit parameters from its exception strings.
    options: dict[str, Any] = {"hide_parameters": True}
    if make_url(url).get_backend_name() == "postgresql":
        # Promotion's Plugin-row claim relies on a waiter re-reading the row it waited on,
        # which only READ COMMITTED does. A stricter server default would turn a lost race
        # into a serialization failure instead of a conflict.
        options["isolation_level"] = "READ COMMITTED"
    engine = create_engine(url, **options)
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
