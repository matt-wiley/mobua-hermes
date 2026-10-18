"""Real deferred constraints, on SQLite or Postgres, to verify commit/rollback ordering."""

from typing import Literal

from sqlalchemy import Engine


def fail_commits_on(
    engine: Engine, table: str, operation: Literal["INSERT", "UPDATE", "DELETE"]
) -> None:
    """Make every commit that ran `operation` on `table` fail its deferred foreign key."""
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE commit_parent (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql(
            "CREATE TABLE commit_failure (parent_id INTEGER REFERENCES commit_parent (id) "
            "DEFERRABLE INITIALLY DEFERRED)"
        )
        if engine.dialect.name == "postgresql":
            connection.exec_driver_sql(
                "CREATE FUNCTION reject_commit() RETURNS trigger LANGUAGE plpgsql AS "
                "$$ BEGIN INSERT INTO commit_failure (parent_id) VALUES (1); RETURN NULL; END $$"
            )
            connection.exec_driver_sql(
                f"CREATE TRIGGER reject_commit AFTER {operation} ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION reject_commit()"
            )
        else:
            connection.exec_driver_sql(
                f"CREATE TRIGGER reject_commit AFTER {operation} ON {table} "
                "BEGIN INSERT INTO commit_failure (parent_id) VALUES (1); END"
            )
