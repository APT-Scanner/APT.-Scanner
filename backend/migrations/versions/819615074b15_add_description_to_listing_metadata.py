"""add_description_to_listing_metadata

Revision ID: 819615074b15
Revises: 5fcd0555b3d0
Create Date: 2025-08-21 15:58:46.543060

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '819615074b15'
down_revision: Union[str, None] = '5fcd0555b3d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add description column to listing_metadata."""
    op.add_column('listing_metadata', sa.Column('description', sa.TEXT(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - Remove description column from listing_metadata."""
    op.drop_column('listing_metadata', 'description')
