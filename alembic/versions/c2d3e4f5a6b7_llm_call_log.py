"""add llm_call_log table

Revision ID: c2d3e4f5a6b7
Revises: b1a2c3d4e5f6
Create Date: 2026-05-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "b1a2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_call_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(32), nullable=False, index=True),
        sa.Column("agent_name", sa.String(64), nullable=False, index=True),
        sa.Column("provider", sa.String(32), nullable=False, index=True),
        sa.Column("model", sa.String(64), nullable=False, index=True),
        sa.Column("prompt_hash", sa.String(64), nullable=False, index=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("output_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("cost_usd", sa.Float(), nullable=False, default=0.0),
        sa.Column("latency_ms", sa.Integer(), nullable=False, default=0),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, default=False),
        sa.Column("prompt_version", sa.String(32), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, default=True),
        sa.Column("error_msg", sa.String(512), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("llm_call_log")
