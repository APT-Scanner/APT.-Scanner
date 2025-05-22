"""adding field to state

Revision ID: a9f5414555fc
Revises: 6387474e5ed4
Create Date: 2025-05-22 14:17:59.829955

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9f5414555fc'
down_revision: Union[str, None] = '6387474e5ed4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('questionnaire_states', sa.Column('participating_questions_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('questionnaire_states', 'participating_questions_count')
