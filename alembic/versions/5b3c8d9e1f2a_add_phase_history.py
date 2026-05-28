"""add_phase_history

Revision ID: 5b3c8d9e1f2a
Revises: 4aa2f52baa41
Create Date: 2026-05-28 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b3c8d9e1f2a'
down_revision: Union[str, Sequence[str], None] = '4aa2f52baa41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'phase_history',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('phase', sa.String(), nullable=False),
        sa.Column('composite_score', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_phase_history_symbol_ts', 'phase_history', ['symbol', 'timestamp'])


def downgrade() -> None:
    op.drop_index('idx_phase_history_symbol_ts', table_name='phase_history')
    op.drop_table('phase_history')
