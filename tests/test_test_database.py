"""AC-58: repository tests run on the database NEWS_TEST_DATABASE_URL names, else SQLite."""

import os

from sqlalchemy import Engine, make_url


def test_the_engine_fixture_uses_the_configured_database(engine: Engine) -> None:
    configured = make_url(os.environ.get("NEWS_TEST_DATABASE_URL") or "sqlite://")

    assert engine.dialect.name == configured.get_backend_name()
