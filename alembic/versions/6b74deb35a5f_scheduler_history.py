"""scheduler_history

Revision ID: 6b74deb35a5f
Revises: 4aa2f52baa41
Create Date: 2026-05-28 15:04:34.469322

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b74deb35a5f'
down_revision: Union[str, Sequence[str], None] = '4aa2f52baa41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "scheduler_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_scheduler_history_job_id", "scheduler_history", ["job_id"])
    op.create_index("idx_scheduler_history_start_at", "scheduler_history", ["start_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_scheduler_history_start_at", table_name="scheduler_history")
    op.drop_index("idx_scheduler_history_job_id", table_name="scheduler_history")
    op.drop_table("scheduler_history")
