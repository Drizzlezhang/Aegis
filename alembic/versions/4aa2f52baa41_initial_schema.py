"""initial_schema

Revision ID: 4aa2f52baa41
Revises: 
Create Date: 2026-05-17 21:52:32.618248

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4aa2f52baa41'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'decisions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('strategy_type', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('target_pct', sa.Float(), nullable=False),
        sa.Column('stop_loss_pct', sa.Float(), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'positions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('position_type', sa.String(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('current_price', sa.Float(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('entry_date', sa.DateTime(), nullable=False),
        sa.Column('exit_date', sa.DateTime(), nullable=True),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'execution_history',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('pipeline_run_id', sa.String(), nullable=False),
        sa.Column('execution_time_s', sa.Float(), nullable=False),
        sa.Column('agent_sequence', sa.JSON(), nullable=False),
        sa.Column('recommendations_count', sa.Integer(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('execution_history')
    op.drop_table('positions')
    op.drop_table('decisions')