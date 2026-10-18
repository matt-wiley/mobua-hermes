from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import URL, Engine
from sqlalchemy.orm import Session

from news.service.db import create_engine_for, migrate
from tests.databases import configured_url, migrated_template, postgres_database


@pytest.fixture(scope="session")
def postgres_server() -> URL | None:
    url = configured_url()
    if url is not None and url.get_backend_name() != "postgresql":
        raise pytest.UsageError(f"NEWS_TEST_DATABASE_URL must name Postgres, not {url.drivername}")
    return url


@pytest.fixture(scope="session")
def postgres_template(postgres_server: URL | None) -> Iterator[str | None]:
    if postgres_server is None:
        yield None
        return
    with migrated_template(postgres_server) as template:
        yield template


@pytest.fixture
def database_url(
    tmp_path: Path, postgres_server: URL | None, postgres_template: str | None
) -> Iterator[str]:
    """A migrated database: SQLite by default, Postgres under NEWS_TEST_DATABASE_URL (AC-58)."""
    if postgres_server is None or postgres_template is None:
        url = f"sqlite:///{tmp_path / 'news.db'}"
        engine = create_engine_for(url)
        migrate(engine)
        engine.dispose()
        yield url
        return
    with postgres_database(postgres_server, postgres_template) as url:
        yield url


@pytest.fixture
def engine(database_url: str) -> Iterator[Engine]:
    engine = create_engine_for(database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session
