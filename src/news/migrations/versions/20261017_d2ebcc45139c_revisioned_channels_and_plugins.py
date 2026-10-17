"""revisioned channels and plugins

Revision ID: d2ebcc45139c
Revises:
Create Date: 2026-10-17 13:08:53.805982
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2ebcc45139c"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reader",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reader")),
    )
    op.create_table(
        "channel",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reader_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("current_revision_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reader_id"], ["reader.id"], name=op.f("fk_channel_reader_id_reader")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_channel")),
    )
    with op.batch_alter_table("channel", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_channel_reader_id"), ["reader_id"], unique=False)

    op.create_table(
        "plugin",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reader_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("current_revision_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reader_id"], ["reader.id"], name=op.f("fk_plugin_reader_id_reader")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plugin")),
    )
    with op.batch_alter_table("plugin", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_plugin_reader_id"), ["reader_id"], unique=False)

    op.create_table(
        "channel_revision",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("reader_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["channel.id"], name=op.f("fk_channel_revision_channel_id_channel")
        ),
        sa.ForeignKeyConstraint(
            ["reader_id"], ["reader.id"], name=op.f("fk_channel_revision_reader_id_reader")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_channel_revision")),
        sa.UniqueConstraint(
            "channel_id", "number", name=op.f("uq_channel_revision_channel_id_number")
        ),
    )
    with op.batch_alter_table("channel_revision", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_channel_revision_reader_id"), ["reader_id"], unique=False
        )

    op.create_table(
        "plugin_revision",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plugin_id", sa.Uuid(), nullable=False),
        sa.Column("reader_id", sa.Uuid(), nullable=True),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("manifest", sa.Text(), nullable=False),
        sa.Column("code", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plugin_id"], ["plugin.id"], name=op.f("fk_plugin_revision_plugin_id_plugin")
        ),
        sa.ForeignKeyConstraint(
            ["reader_id"], ["reader.id"], name=op.f("fk_plugin_revision_reader_id_reader")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plugin_revision")),
        sa.UniqueConstraint(
            "plugin_id", "number", name=op.f("uq_plugin_revision_plugin_id_number")
        ),
    )
    with op.batch_alter_table("plugin_revision", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_plugin_revision_reader_id"), ["reader_id"], unique=False
        )

    op.create_table(
        "plugin_binding",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("channel_revision_id", sa.Uuid(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("reader_id", sa.Uuid(), nullable=False),
        sa.Column("plugin_revision_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["channel.id"], name=op.f("fk_plugin_binding_channel_id_channel")
        ),
        sa.ForeignKeyConstraint(
            ["channel_revision_id"],
            ["channel_revision.id"],
            name=op.f("fk_plugin_binding_channel_revision_id_channel_revision"),
        ),
        sa.ForeignKeyConstraint(
            ["plugin_revision_id"],
            ["plugin_revision.id"],
            name=op.f("fk_plugin_binding_plugin_revision_id_plugin_revision"),
        ),
        sa.ForeignKeyConstraint(
            ["reader_id"], ["reader.id"], name=op.f("fk_plugin_binding_reader_id_reader")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plugin_binding")),
    )
    with op.batch_alter_table("plugin_binding", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_plugin_binding_channel_id"), ["channel_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_plugin_binding_reader_id"), ["reader_id"], unique=False
        )

    # Identities point at their current Revision, a cycle, so these keys are added last.
    for identity in ("channel", "plugin"):
        with op.batch_alter_table(identity, schema=None) as batch_op:
            batch_op.create_foreign_key(
                batch_op.f(f"fk_{identity}_current_revision_id_{identity}_revision"),
                f"{identity}_revision",
                ["current_revision_id"],
                ["id"],
            )


def downgrade() -> None:
    for identity in ("channel", "plugin"):
        with op.batch_alter_table(identity, schema=None) as batch_op:
            batch_op.drop_constraint(
                batch_op.f(f"fk_{identity}_current_revision_id_{identity}_revision"),
                type_="foreignkey",
            )

    with op.batch_alter_table("plugin_binding", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_plugin_binding_reader_id"))
        batch_op.drop_index(batch_op.f("ix_plugin_binding_channel_id"))

    op.drop_table("plugin_binding")
    with op.batch_alter_table("plugin_revision", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_plugin_revision_reader_id"))

    op.drop_table("plugin_revision")
    with op.batch_alter_table("channel_revision", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_channel_revision_reader_id"))

    op.drop_table("channel_revision")
    with op.batch_alter_table("plugin", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_plugin_reader_id"))

    op.drop_table("plugin")
    with op.batch_alter_table("channel", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_channel_reader_id"))

    op.drop_table("channel")
    op.drop_table("reader")
