"""Add is_active to listings

Revision ID: 64291517171d
Revises: 2e652011f1ca
Create Date: 2025-05-14 19:58:29.836904

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64291517171d'
down_revision: Union[str, None] = '2e652011f1ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('listings', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))



def downgrade() -> None:
    op.drop_column('listings', 'is_active')

