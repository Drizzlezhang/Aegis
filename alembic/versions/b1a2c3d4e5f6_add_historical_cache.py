"""add_historical_cache

Revision ID: b1a2c3d4e5f6
Revises: 4aa2f52baa41
Create Date: 2026-05-28 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1a2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '4aa2f52baa41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'historical_cache',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('data', sa.Text(), nullable=False),
        sa.Column('interval', sa.String(), nullable=False),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('expires_at', sa.Float(), nullable=False),
        sa.Column('access_count', sa.Integer(), server_default='0'),
        sa.Column('last_accessed_at', sa.Float(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )
    op.create_index('idx_historical_cache_expires', 'historical_cache', ['expires_at'])
    op.create_index('idx_historical_cache_last_accessed', 'historical_cache', ['last_accessed_at'])


def downgrade() -> None:
    op.drop_index('idx_historical_cache_last_accessed', table_name='historical_cache')
    op.drop_index('idx_historical_cache_expires', table_name='historical_cache')
    op.drop_table('historical_cache')
