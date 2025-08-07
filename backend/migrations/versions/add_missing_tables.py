"""add_missing_tables

Revision ID: add_missing_tables
Revises: add_madlan_cols
Create Date: 2025-08-07 15:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_missing_tables'
down_revision: Union[str, None] = 'add_madlan_cols'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing tables with references to existing neighborhoods structure."""
    
    # Create a simple user_preferences table first (without enum columns for now)
    op.create_table('user_preferences',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('pace_of_life', sa.String(50), nullable=True),  # Simplified as string
    sa.Column('commute_pref_pt', sa.Boolean(), nullable=True),
    sa.Column('commute_pref_walk', sa.Boolean(), nullable=True),
    sa.Column('commute_pref_bike', sa.Boolean(), nullable=True),
    sa.Column('commute_pref_car', sa.Boolean(), nullable=True),
    sa.Column('commute_pref_wfh', sa.Boolean(), nullable=True),
    sa.Column('proximity_pref_shops', sa.Boolean(), nullable=True),
    sa.Column('proximity_pref_gym', sa.Boolean(), nullable=True),
    sa.Column('max_commute_time', sa.Integer(), nullable=True),
    sa.Column('dog_park_nearby', sa.String(50), nullable=True),  # Simplified as string
    sa.Column('learning_space_nearby', sa.String(50), nullable=True),  # Simplified as string
    sa.Column('proximity_beach_importance', sa.String(50), nullable=True),  # Simplified as string
    sa.Column('safety_importance', sa.String(50), nullable=True),  # Simplified as string
    sa.Column('green_spaces_importance', sa.String(50), nullable=True),  # Simplified as string
    sa.Column('medical_center_importance', sa.String(50), nullable=True),  # Simplified as string
    sa.Column('schools_importance', sa.String(50), nullable=True),  # Simplified as string
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index(op.f('ix_user_preferences_user_id'), 'user_preferences', ['user_id'], unique=True)
    
    # Create neighborhood tables that reference the current neighborhoods table structure
    # Using yad2_hood_id as the foreign key reference (existing primary key)
    op.create_table('neighborhood_metadata',
    sa.Column('neighborhood_id', sa.Integer(), nullable=False),
    sa.Column('overview', sa.TEXT(), nullable=True),
    sa.Column('external_city_id', sa.Integer(), nullable=True),
    sa.Column('external_area_id', sa.Integer(), nullable=True),
    sa.Column('external_top_area_id', sa.Integer(), nullable=True),
    sa.Column('external_doc_count', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['neighborhood_id'], ['neighborhoods.yad2_hood_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('neighborhood_id')
    )
    
    op.create_table('neighborhood_metrics',
    sa.Column('neighborhood_id', sa.Integer(), nullable=False),
    sa.Column('avg_sale_price', sa.DECIMAL(precision=15, scale=2), nullable=True),
    sa.Column('avg_rental_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
    sa.Column('social_economic_index', sa.Float(), nullable=True),
    sa.Column('popular_political_party', sa.String(length=100), nullable=True),
    sa.Column('school_rating', sa.Float(), nullable=True),
    sa.Column('beach_distance_km', sa.DECIMAL(precision=10, scale=2), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['neighborhood_id'], ['neighborhoods.yad2_hood_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('neighborhood_id')
    )
    
    # Add missing columns to existing tables
    try:
        op.add_column('neighborhood_features', sa.Column('nightlife_level', sa.Float(), nullable=True))
    except:
        print("nightlife_level column may already exist in neighborhood_features")
        
    try:
        op.add_column('user_preference_vectors', sa.Column('nightlife_level', sa.Float(), nullable=False))
    except:
        print("nightlife_level column may already exist in user_preference_vectors")


def downgrade() -> None:
    """Remove added tables."""
    op.drop_table('neighborhood_metrics')
    op.drop_table('neighborhood_metadata')
    op.drop_index(op.f('ix_user_preferences_user_id'), table_name='user_preferences')
    op.drop_table('user_preferences')
    
    try:
        op.drop_column('neighborhood_features', 'nightlife_level')
    except:
        pass
    try:
        op.drop_column('user_preference_vectors', 'nightlife_level')
    except:
        pass 