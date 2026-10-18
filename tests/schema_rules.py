"""Scope rules for the schema (ADR 0007, review-followups-01 D-2, D-3).

Each table declares its scope as `app`, `reader` or `channel`. A `reader` table carries a Reader id;
a `channel` table carries a Channel id and a Reader id. The `reader` and `channel` tables pass on
their own `id`. Only a `channel` table may hold a foreign key to another `channel` table.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import get_args

from sqlalchemy import Engine, MetaData, inspect

from news.service.models import Scope

SCOPES = frozenset(get_args(Scope.__value__))

# Alembic's own table is app-wide and has no model to declare it (D-3).
UNMODELLED_TABLE_SCOPES = {"alembic_version": "app"}


@dataclass(frozen=True)
class TableDescription:
    name: str
    columns: frozenset[str]
    foreign_key_targets: frozenset[str]
    scope: str | None


def scope_violations(tables: Sequence[TableDescription]) -> list[str]:
    channel_tables = {table.name for table in tables if table.scope == "channel"}
    violations: list[str] = []
    for table in tables:
        violations.extend(_violations_of(table, channel_tables))
    return violations


def _violations_of(table: TableDescription, channel_tables: set[str]) -> list[str]:
    if table.scope is None:
        return [f"{table.name}: no declared scope"]
    if table.scope not in SCOPES:
        return [f"{table.name}: unknown scope {table.scope!r}"]

    violations: list[str] = []
    if table.scope in {"reader", "channel"} and not _has_scope_column(table, "reader"):
        violations.append(f"{table.name}: declared {table.scope} but has no reader_id")
    if table.scope == "channel" and not _has_scope_column(table, "channel"):
        violations.append(f"{table.name}: declared channel but has no channel_id")
    if table.scope != "channel":
        violations.extend(
            f"{table.name}: references channel table {target} but is declared {table.scope}"
            for target in sorted(table.foreign_key_targets & channel_tables)
        )
    return violations


def _has_scope_column(table: TableDescription, owner: str) -> bool:
    """The `reader` and `channel` tables are scoped by their own `id` (D-2)."""
    return f"{owner}_id" in table.columns or (table.name == owner and "id" in table.columns)


def describe_tables(engine: Engine, metadata: MetaData) -> list[TableDescription]:
    """Describe every table in the database, with the scope its model declares."""
    schema = inspect(engine)
    return [
        TableDescription(
            name=name,
            columns=frozenset(column["name"] for column in schema.get_columns(name)),
            foreign_key_targets=frozenset(
                foreign_key["referred_table"] for foreign_key in schema.get_foreign_keys(name)
            ),
            scope=_declared_scope(name, metadata),
        )
        for name in schema.get_table_names()
    ]


def _declared_scope(name: str, metadata: MetaData) -> str | None:
    if name in UNMODELLED_TABLE_SCOPES:
        return UNMODELLED_TABLE_SCOPES[name]
    table = metadata.tables.get(name)
    return None if table is None else table.info.get("scope")
