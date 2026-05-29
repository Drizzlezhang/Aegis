"""backtest_v3_walkforward

Revision ID: c7d8e9f0a1b2
Revises: 5b3c8d9e1f2a
Create Date: 2026-05-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = '5b3c8d9e1f2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'backtest_v3_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(64), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('strategy', sa.String(100), nullable=False),
        sa.Column('mode', sa.String(20), nullable=False),
        sa.Column('train_window_days', sa.Integer(), nullable=False),
        sa.Column('test_window_days', sa.Integer(), nullable=False),
        sa.Column('step_size_days', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.String(10), nullable=False),
        sa.Column('end_date', sa.String(10), nullable=False),
        sa.Column('total_folds', sa.Integer(), nullable=False),
        sa.Column('oos_total_return', sa.Float(), nullable=True),
        sa.Column('oos_sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('oos_max_drawdown', sa.Float(), nullable=True),
        sa.Column('oos_win_rate', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id'),
    )
    op.create_index('idx_backtest_v3_runs_run_id', 'backtest_v3_runs', ['run_id'])
    op.create_index('idx_backtest_v3_runs_symbol', 'backtest_v3_runs', ['symbol'])

    op.create_table(
        'backtest_v3_folds',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('fold_index', sa.Integer(), nullable=False),
        sa.Column('train_start', sa.String(10), nullable=False),
        sa.Column('train_end', sa.String(10), nullable=False),
        sa.Column('test_start', sa.String(10), nullable=False),
        sa.Column('test_end', sa.String(10), nullable=False),
        sa.Column('train_sharpe', sa.Float(), nullable=True),
        sa.Column('test_sharpe', sa.Float(), nullable=True),
        sa.Column('test_return', sa.Float(), nullable=True),
        sa.Column('test_max_drawdown', sa.Float(), nullable=True),
        sa.Column('test_trades', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['backtest_v3_runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_backtest_v3_folds_run_id', 'backtest_v3_folds', ['run_id'])

    op.create_table(
        'backtest_v3_trades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('fold_index', sa.Integer(), nullable=True),
        sa.Column('entry_date', sa.String(10), nullable=False),
        sa.Column('exit_date', sa.String(10), nullable=True),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('shares', sa.Integer(), nullable=False),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('pnl_percent', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('entry_phase', sa.String(50), nullable=True),
        sa.Column('exit_phase', sa.String(50), nullable=True),
        sa.Column('entry_confidence', sa.Float(), nullable=True),
        sa.Column('exit_confidence', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['backtest_v3_runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_backtest_v3_trades_run_id', 'backtest_v3_trades', ['run_id'])


def downgrade() -> None:
    op.drop_index('idx_backtest_v3_trades_run_id', table_name='backtest_v3_trades')
    op.drop_table('backtest_v3_trades')
    op.drop_index('idx_backtest_v3_folds_run_id', table_name='backtest_v3_folds')
    op.drop_table('backtest_v3_folds')
    op.drop_index('idx_backtest_v3_runs_symbol', table_name='backtest_v3_runs')
    op.drop_index('idx_backtest_v3_runs_run_id', table_name='backtest_v3_runs')
    op.drop_table('backtest_v3_runs')
