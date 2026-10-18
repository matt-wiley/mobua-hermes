"""AC-60: additive Draft migration, including databases with non-linear legacy history."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from sqlalchemy import Engine, MetaData, inspect, select

from news.service.db import alembic_config, create_engine_for, migrate

LEGACY_HEAD = "982ca57d031a"


def snapshot(engine: Engine) -> dict[str, list[dict[str, object]]]:
    metadata = MetaData()
    metadata.reflect(engine)
    with engine.connect() as connection:
        return {
            name: [dict(row) for row in connection.execute(select(table)).mappings()]
            for name, table in metadata.tables.items()
            if name != "alembic_version"
        }


def test_upgrade_preserves_legacy_history_without_inventing_ancestry(tmp_path: Path) -> None:
    engine = create_engine_for(f"sqlite:///{tmp_path / 'legacy.db'}")
    config = alembic_config()
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, LEGACY_HEAD)
        metadata = MetaData()
        metadata.reflect(engine)
        reader, plugin, first, later, channel, channel_revision, binding = [
            uuid.uuid7().hex for _ in range(7)
        ]
        now = datetime.now(UTC)
        with engine.begin() as connection:
            connection.execute(
                metadata.tables["reader"].insert(), {"id": reader, "name": "Ada", "created_at": now}
            )
            connection.execute(
                metadata.tables["plugin"].insert(),
                {"id": plugin, "reader_id": reader, "name": "legacy", "created_at": now},
            )
            for revision_id, number in [(first, 1), (later, 4)]:
                connection.execute(
                    metadata.tables["plugin_revision"].insert(),
                    {
                        "id": revision_id,
                        "plugin_id": plugin,
                        "reader_id": reader,
                        "number": number,
                        "manifest": "original\r\n",
                        "code": {"nested/code.py": "original π\n"},
                        "created_by": reader,
                        "note": "retained",
                        "created_at": now,
                    },
                )
            connection.execute(metadata.tables["plugin"].update().values(current_revision_id=first))
            connection.execute(
                metadata.tables["channel"].insert(),
                {"id": channel, "reader_id": reader, "name": "bound", "created_at": now},
            )
            connection.execute(
                metadata.tables["channel_revision"].insert(),
                {
                    "id": channel_revision,
                    "channel_id": channel,
                    "reader_id": reader,
                    "number": 1,
                    "created_at": now,
                },
            )
            connection.execute(
                metadata.tables["channel"].update().values(current_revision_id=channel_revision)
            )
            connection.execute(
                metadata.tables["plugin_binding"].insert(),
                {
                    "id": binding,
                    "channel_id": channel,
                    "reader_id": reader,
                    "channel_revision_id": channel_revision,
                    "plugin_revision_id": later,
                    "position": 0,
                    "config": {"x": 2},
                },
            )
        before = snapshot(engine)

        migrate(engine)

        assert "plugin_draft" in inspect(engine).get_table_names()
        after = snapshot(engine)
        assert after.pop("plugin_draft") == []
        assert all(row.pop("parent_revision_id") is None for row in after["plugin_revision"])
        assert after == before
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.downgrade(config, LEGACY_HEAD)
        assert snapshot(engine) == before
        migrate(engine)
        assert snapshot(engine)["plugin_draft"] == []
    finally:
        engine.dispose()
