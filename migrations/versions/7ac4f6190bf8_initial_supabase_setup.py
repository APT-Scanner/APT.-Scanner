"""initial_supabase_setup

Revision ID: 7ac4f6190bf8
Revises: 9cd6f5e0574f
Create Date: 2025-05-08 14:01:08.991081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ac4f6190bf8'
down_revision: Union[str, None] = '9cd6f5e0574f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
