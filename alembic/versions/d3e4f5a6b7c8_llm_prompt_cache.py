"""add llm_prompt_cache table

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-05-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_prompt_cache",
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("cache_key"),
    )
    op.create_index("ix_llm_prompt_cache_expires", "llm_prompt_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_table("llm_prompt_cache")
