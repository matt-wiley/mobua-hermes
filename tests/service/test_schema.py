"""AC-53: every table is scoped by Reader, and by Channel where its rows belong to one."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect, text

from news.service.db import alembic_config
from news.service.models import READER_SCOPE_EXEMPT_TABLES, Base

CHANNEL_TABLES = {"channel", "channel_revision"}


def test_migration_creates_the_revisioned_channel_and_plugin_tables(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())

    assert {
        "reader",
        "plugin",
        "plugin_revision",
        "channel",
        "channel_revision",
        "plugin_binding",
    } <= tables


def test_every_table_has_a_reader_id_except_declared_exemptions(engine: Engine) -> None:
    schema = inspect(engine)
    unscoped = [
        table
        for table in schema.get_table_names()
        if table not in READER_SCOPE_EXEMPT_TABLES
        and "reader_id" not in {column["name"] for column in schema.get_columns(table)}
    ]

    assert unscoped == []


def test_every_exemption_names_a_real_table(engine: Engine) -> None:
    assert set(READER_SCOPE_EXEMPT_TABLES) <= set(inspect(engine).get_table_names())


def test_tables_referencing_a_channel_or_its_revisions_have_a_channel_id(engine: Engine) -> None:
    schema = inspect(engine)
    channel_owned = [
        table
        for table in schema.get_table_names()
        if table not in CHANNEL_TABLES
        and any(fk["referred_table"] in CHANNEL_TABLES for fk in schema.get_foreign_keys(table))
    ]
    missing_channel_id = [
        table
        for table in channel_owned
        if "channel_id" not in {column["name"] for column in schema.get_columns(table)}
    ]

    assert channel_owned, "expected at least one Channel-owned table"
    assert missing_channel_id == []


def test_migrated_schema_matches_the_models(engine: Engine) -> None:
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    assert differences == []


def test_sqlite_runs_in_wal_mode(engine: Engine) -> None:
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA journal_mode")).scalar_one() == "wal"


def test_sqlite_enforces_foreign_keys(engine: Engine) -> None:
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1


def test_migration_downgrades_to_an_empty_database(engine: Engine) -> None:
    config = alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")

    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
