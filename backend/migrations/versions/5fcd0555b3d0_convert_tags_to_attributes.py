"""convert_tags_to_attributes

Revision ID: 5fcd0555b3d0
Revises: add_property_type_filter
Create Date: 2025-08-21 15:06:56.283092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5fcd0555b3d0'
down_revision: Union[str, None] = 'add_property_type_filter'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Convert tags to attributes."""
    
    # Step 1: Rename tags table to attributes
    op.rename_table('tags', 'attributes')
    
    # Step 2: Rename columns in the attributes table
    op.alter_column('attributes', 'tag_id', new_column_name='attribute_id')
    op.alter_column('attributes', 'tag_name', new_column_name='attribute_name')
    
    # Step 3: Rename listing_tags table to listing_attributes
    op.rename_table('listing_tags', 'listing_attributes')
    
    # Step 4: Rename tag_id column in listing_attributes table
    op.alter_column('listing_attributes', 'tag_id', new_column_name='attribute_id')
    
    # Step 5: Drop and recreate foreign key constraints with new names
    op.drop_constraint('listing_tags_tag_id_fkey', 'listing_attributes', type_='foreignkey')
    op.create_foreign_key(
        'listing_attributes_attribute_id_fkey',
        'listing_attributes', 'attributes',
        ['attribute_id'], ['attribute_id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema - Convert attributes back to tags."""
    
    # Step 1: Drop and recreate foreign key constraints with old names
    op.drop_constraint('listing_attributes_attribute_id_fkey', 'listing_attributes', type_='foreignkey')
    op.create_foreign_key(
        'listing_tags_tag_id_fkey',
        'listing_attributes', 'attributes',
        ['attribute_id'], ['attribute_id'],  # Still pointing to current column names
        ondelete='CASCADE'
    )
    
    # Step 2: Rename attribute_id column back to tag_id in listing_attributes table
    op.alter_column('listing_attributes', 'attribute_id', new_column_name='tag_id')
    
    # Step 3: Rename listing_attributes table back to listing_tags
    op.rename_table('listing_attributes', 'listing_tags')
    
    # Step 4: Rename columns in the attributes table back to tags columns
    op.alter_column('attributes', 'attribute_id', new_column_name='tag_id')
    op.alter_column('attributes', 'attribute_name', new_column_name='tag_name')
    
    # Step 5: Rename attributes table back to tags
    op.rename_table('attributes', 'tags')
    
    # Step 6: Fix the foreign key constraint name after table rename
    op.drop_constraint('listing_tags_tag_id_fkey', 'listing_tags', type_='foreignkey')
    op.create_foreign_key(
        'listing_tags_tag_id_fkey',
        'listing_tags', 'tags',
        ['tag_id'], ['tag_id'],
        ondelete='CASCADE'
    )
