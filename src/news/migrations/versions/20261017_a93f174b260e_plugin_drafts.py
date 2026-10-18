"""Plugin Drafts and recorded Revision ancestry.

Revision ID: a93f174b260e
Revises: 982ca57d031a
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a93f174b260e"
down_revision: str | None = "982ca57d031a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Additive only: never infer ancestry or synthesize a starter for existing history.
    op.add_column("plugin_revision", sa.Column("parent_revision_id", sa.Uuid(), nullable=True))
    op.create_table(
        "plugin_draft",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reader_id", sa.Uuid(), nullable=False),
        sa.Column("plugin_id", sa.Uuid(), nullable=False),
        sa.Column("parent_revision_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("manifest", sa.Text(), nullable=False),
        sa.Column("code", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plugin_draft")),
        sa.ForeignKeyConstraint(
            ["reader_id"], ["reader.id"], name=op.f("fk_plugin_draft_reader_id_reader")
        ),
        sa.ForeignKeyConstraint(
            ["plugin_id"], ["plugin.id"], name=op.f("fk_plugin_draft_plugin_id_plugin")
        ),
        sa.ForeignKeyConstraint(
            ["parent_revision_id"],
            ["plugin_revision.id"],
            name=op.f("fk_plugin_draft_parent_revision_id_plugin_revision"),
        ),
    )
    op.create_index("ix_plugin_draft_reader_id", "plugin_draft", ["reader_id"])
    op.create_index("ix_plugin_draft_plugin_id", "plugin_draft", ["plugin_id"])


def downgrade() -> None:
    op.drop_table("plugin_draft")
    op.drop_column("plugin_revision", "parent_revision_id")
