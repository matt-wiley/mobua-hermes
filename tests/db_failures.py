"""Real SQLite deferred constraints to verify surface commit/rollback ordering."""

from typing import Literal

from sqlalchemy import Engine


def fail_commits_on(
    engine: Engine, table: str, operation: Literal["INSERT", "UPDATE", "DELETE"]
) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE commit_parent (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql(
            "CREATE TABLE commit_failure (parent_id INTEGER REFERENCES commit_parent (id) "
            "DEFERRABLE INITIALLY DEFERRED)"
        )
        connection.exec_driver_sql(
            f"CREATE TRIGGER reject_commit AFTER {operation} ON {table} "
            "BEGIN INSERT INTO commit_failure (parent_id) VALUES (1); END"
        )
