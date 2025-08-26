"""add_madlan_columns_only

Revision ID: add_madlan_cols
Revises: b80ac323252f
Create Date: 2025-08-06 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_madlan_cols'
down_revision: Union[str, None] = 'b80ac323252f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Madlan metrics columns to neighborhoods table."""
    # Add Madlan columns to neighborhoods table
    op.add_column('neighborhoods', sa.Column('madlan_name', sa.String(length=200), nullable=True))
    op.add_column('neighborhoods', sa.Column('madlan_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('neighborhoods', sa.Column('madlan_overview', sa.TEXT(), nullable=True))
    op.add_column('neighborhoods', sa.Column('madlan_avg_price_per_sqm', sa.Float(), nullable=True))
    op.add_column('neighborhoods', sa.Column('madlan_price_trend', sa.String(length=50), nullable=True))
    op.add_column('neighborhoods', sa.Column('madlan_demand_level', sa.String(length=50), nullable=True))
    op.add_column('neighborhoods', sa.Column('madlan_supply_level', sa.String(length=50), nullable=True))
    op.add_column('neighborhoods', sa.Column('madlan_last_scraped', sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove Madlan metrics columns from neighborhoods table."""
    op.drop_column('neighborhoods', 'madlan_last_scraped')
    op.drop_column('neighborhoods', 'madlan_supply_level')
    op.drop_column('neighborhoods', 'madlan_demand_level')
    op.drop_column('neighborhoods', 'madlan_price_trend')
    op.drop_column('neighborhoods', 'madlan_avg_price_per_sqm')
    op.drop_column('neighborhoods', 'madlan_overview')
    op.drop_column('neighborhoods', 'madlan_metrics')
    op.drop_column('neighborhoods', 'madlan_name') 