"""Alembic environment. The app passes its own connection; the CLI fallback reads the URL."""

import os

from alembic import context
from sqlalchemy import Connection

from news.service.db import create_engine_for
from news.service.models import Base


def run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        # SQLite can't ALTER constraints in place; batch mode recreates tables instead.
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def main() -> None:
    connection: Connection | None = context.config.attributes.get("connection")
    if connection is not None:
        run_migrations(connection)
        return
    engine = create_engine_for(os.environ["NEWS_DATABASE_URL"])
    with engine.begin() as own_connection:
        run_migrations(own_connection)


main()
