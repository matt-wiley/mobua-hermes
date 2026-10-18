"""AC-53, review-followups-01 AC-1, AC-3: every table declares its scope, and keeps to it."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect, text

from news.service import models
from news.service.db import alembic_config
from news.service.models import Base
from tests.schema_rules import describe_tables, scope_violations


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


def test_every_migrated_table_declares_a_scope(engine: Engine) -> None:
    """AC-1."""
    undeclared = [
        table.name for table in describe_tables(engine, Base.metadata) if table.scope is None
    ]

    assert undeclared == []


def test_a_migrated_table_with_no_model_is_reported_as_undeclared(engine: Engine) -> None:
    """AC-1."""
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE stray (id INTEGER PRIMARY KEY)"))

    assert scope_violations(describe_tables(engine, Base.metadata)) == ["stray: no declared scope"]


def test_alembic_version_counts_as_app_wide(engine: Engine) -> None:
    """AC-1."""
    scopes = {table.name: table.scope for table in describe_tables(engine, Base.metadata)}

    assert scopes["alembic_version"] == "app"


def test_migrated_schema_has_no_scope_violations(engine: Engine) -> None:
    """AC-3."""
    assert scope_violations(describe_tables(engine, Base.metadata)) == []


def test_scopes_match_the_design(engine: Engine) -> None:
    """D-2, D-3: Plugin tables are Reader-scoped, with an empty Reader id for Built-ins."""
    scopes = {table.name: table.scope for table in describe_tables(engine, Base.metadata)}

    assert scopes == {
        "alembic_version": "app",
        "reader": "reader",
        "reader_data_key": "reader",
        "secret": "reader",
        "llm_provider": "reader",
        "plugin": "reader",
        "plugin_revision": "reader",
        "plugin_draft": "reader",
        "channel": "channel",
        "channel_revision": "channel",
        "plugin_binding": "channel",
    }


def test_foreign_key_targets_are_read_from_the_migrated_database(engine: Engine) -> None:
    """AC-3: the foreign-key rule sees the real schema's references to `channel` tables."""
    targets = {
        table.name: table.foreign_key_targets for table in describe_tables(engine, Base.metadata)
    }

    assert targets == {
        "alembic_version": set(),
        "reader": set(),
        "reader_data_key": {"reader"},
        "secret": {"reader"},
        "llm_provider": {"reader"},
        "plugin": {"reader", "plugin_revision"},
        "plugin_revision": {"reader", "plugin"},
        "plugin_draft": {"reader", "plugin", "plugin_revision"},
        "channel": {"reader", "channel_revision"},
        "channel_revision": {"reader", "channel"},
        "plugin_binding": {"reader", "channel", "channel_revision", "plugin_revision"},
    }


def test_the_reader_scope_exemption_list_is_gone() -> None:
    """AC-3."""
    assert not hasattr(models, "READER_SCOPE_EXEMPT_TABLES")


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
