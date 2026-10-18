"""Test databases: SQLite files by default, or Postgres when NEWS_TEST_DATABASE_URL names it.

Each Postgres test gets its own database, cloned from one migrated template per test session.
"""

import os
import uuid
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import URL, Engine, create_engine, make_url

from news.service.db import create_engine_for, migrate


def configured_url() -> URL | None:
    value = os.environ.get("NEWS_TEST_DATABASE_URL")
    return None if not value else make_url(value)


@contextmanager
def migrated_template(server: URL) -> Generator[str]:
    """A migrated database that per-test databases copy, dropped at the end of the session."""
    name = f"news_test_template_{uuid.uuid4().hex}"
    with _administered(server, name):
        engine = create_engine_for(_rendered(server.set(database=name)))
        migrate(engine)
        # CREATE DATABASE ... TEMPLATE fails while anyone is connected to the template.
        engine.dispose()
        yield name


@contextmanager
def postgres_database(server: URL, template: str) -> Generator[str]:
    """A fresh copy of the migrated template, as a URL with its password."""
    name = f"news_test_{uuid.uuid4().hex}"
    with _administered(server, name, template=template) as (admin, quoted):
        # A stricter default than Postgres's own, so the suite proves the engine pins its level.
        with admin.connect() as connection:
            connection.exec_driver_sql(
                f"ALTER DATABASE {quoted} SET default_transaction_isolation TO 'serializable'"
            )
        yield _rendered(server.set(database=name))


@contextmanager
def _administered(
    server: URL, name: str, template: str | None = None
) -> Generator[tuple[Engine, str]]:
    """Create the database, yield an admin engine and its quoted name, then drop it."""
    admin = create_engine(server, isolation_level="AUTOCOMMIT")
    # Database names are identifiers, which cannot be bound; these are generated, and quoted.
    quote = admin.dialect.identifier_preparer.quote
    copied = f" TEMPLATE {quote(template)}" if template else ""
    try:
        with admin.connect() as connection:
            connection.exec_driver_sql(f"CREATE DATABASE {quote(name)}{copied}")
        try:
            yield admin, quote(name)
        finally:
            with admin.connect() as connection:
                connection.exec_driver_sql(f"DROP DATABASE {quote(name)} WITH (FORCE)")
    finally:
        admin.dispose()


def _rendered(url: URL) -> str:
    return url.render_as_string(hide_password=False)
