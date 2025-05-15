"""merge heads

Revision ID: 2e652011f1ca
Revises: 7ac4f6190bf8, 89e7ea94b9f5
Create Date: 2025-05-14 19:57:52.132892

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e652011f1ca'
down_revision: Union[str, None] = ('7ac4f6190bf8', '89e7ea94b9f5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
