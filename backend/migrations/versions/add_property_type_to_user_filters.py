"""Add property_type column to user_filters table

Revision ID: add_property_type_filter
Revises: 
Create Date: 2025-01-19 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_property_type_filter'
down_revision = '86df95e786a2'
branch_labels = None
depends_on = None

def upgrade():
    # Add property_type column to user_filters table
    op.add_column('user_filters', sa.Column('property_type', sa.String(), nullable=True))

def downgrade():
    # Remove property_type column from user_filters table
    op.drop_column('user_filters', 'property_type')
