"""merge user_id primary key with existing heads

Revision ID: 6f3b967c859e
Revises: a9f5414555fc, bf7c3e4d8a92
Create Date: 2025-05-22 16:12:50.518647

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f3b967c859e'
down_revision: Union[str, None] = ('a9f5414555fc', 'bf7c3e4d8a92')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
