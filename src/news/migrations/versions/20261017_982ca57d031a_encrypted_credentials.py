"""Reader Data Keys, Secrets and LLM Provider credentials.

Revision ID: 982ca57d031a
Revises: d2ebcc45139c
"""

import sqlalchemy as sa
from alembic import op

revision = "982ca57d031a"
down_revision = "d2ebcc45139c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reader_data_key",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reader_id", sa.Uuid(), sa.ForeignKey("reader.id"), nullable=False),
        sa.Column("encrypted_key", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint("reader_id"),
    )
    for name, encrypted_column in (
        ("secret", "encrypted_value"),
        ("llm_provider", "encrypted_credential"),
    ):
        columns = [
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("reader_id", sa.Uuid(), sa.ForeignKey("reader.id"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column(encrypted_column, sa.LargeBinary(), nullable=False),
        ]
        if name == "llm_provider":
            columns.append(sa.Column("url", sa.String(), nullable=False))
        op.create_table(name, *columns, sa.UniqueConstraint("reader_id", "name"))
        op.create_index(f"ix_{name}_reader_id", name, ["reader_id"])


def downgrade() -> None:
    op.drop_table("llm_provider")
    op.drop_table("secret")
    op.drop_table("reader_data_key")
