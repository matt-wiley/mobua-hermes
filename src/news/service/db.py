"""Database engine and migrations (ADR 0013: SQLite by default, Postgres-ready)."""

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event

# The Alembic project lives at the repository root, next to src/.
ALEMBIC_INI = Path(__file__).resolve().parents[3] / "alembic.ini"


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


def migrate(engine: Engine) -> None:
    config = Config(ALEMBIC_INI)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
