"""The isolation level the promotion claim relies on (ticket 04's deferred decision)."""

from sqlalchemy import Engine

# Postgres re-reads a row it waited on only under READ COMMITTED; pysqlite reports SERIALIZABLE.
CLAIM_ISOLATION = {"postgresql": "READ COMMITTED", "sqlite": "SERIALIZABLE"}


def test_connections_run_at_the_isolation_level_the_promotion_claim_needs(
    engine: Engine,
) -> None:
    """Test databases on Postgres default to SERIALIZABLE, so this proves the engine's own pin."""
    with engine.connect() as connection:
        assert connection.get_isolation_level() == CLAIM_ISOLATION[engine.dialect.name]
