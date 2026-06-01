"""sprint16 schema — signal_events + push_dedup + decisions columns

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-06-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | Sequence[str] | None = ("d3e4f5a6b7c8", "6b74deb35a5f", "c7d8e9f0a1b2")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # B branch: signal storage
    op.create_table(
        "signal_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("signal_type", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("symbols", sa.Text(), nullable=False),  # JSON list
        sa.Column("sentiment", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("raw_url", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),  # JSON
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_signal_events_timestamp", "signal_events", ["timestamp"])
    op.create_index("ix_signal_events_source", "signal_events", ["source"])

    # D branch: push dedup
    op.create_table(
        "push_dedup",
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("pushed_at", sa.DateTime(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_push_dedup_pushed_at", "push_dedup", ["pushed_at"])

    # C branch: decisions trace columns (idempotent — skip if columns exist)
    conn = op.get_bind()
    col_check = conn.execute(sa.text("PRAGMA table_info(decisions)"))
    existing = {row[1] for row in col_check.fetchall()}

    if "signal_sources_json" not in existing:
        op.add_column(
            "decisions",
            sa.Column("signal_sources_json", sa.Text(), nullable=False, server_default="[]"),
        )
    if "fused_signal_json" not in existing:
        op.add_column(
            "decisions",
            sa.Column("fused_signal_json", sa.Text(), nullable=False, server_default="{}"),
        )
    if "context_snapshot_json" not in existing:
        op.add_column(
            "decisions",
            sa.Column("context_snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    op.drop_column("decisions", "context_snapshot_json")
    op.drop_column("decisions", "fused_signal_json")
    op.drop_column("decisions", "signal_sources_json")
    op.drop_table("push_dedup")
    op.drop_table("signal_events")
