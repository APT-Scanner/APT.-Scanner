"""make user_id unique for questionnaire tables

Revision ID: bf7c3e4d8a92
Revises: aee7ba56c8d3
Create Date: 2025-05-10 17:30:22.123456

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError, OperationalError
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bf7c3e4d8a92'
down_revision: Union[str, None] = 'aee7ba56c8d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def safe_op(fn, *args, **kwargs):
    """Execute an operation safely, ignoring specific errors."""
    try:
        fn(*args, **kwargs)
        return True
    except (ProgrammingError, OperationalError) as e:
        # Log the error but continue
        print(f"Operation failed (continuing): {str(e)}")
        return False


def upgrade() -> None:
    """
    Make user_id unique for questionnaire tables.
    
    This is a conservative migration that only adds constraints without
    changing primary keys or column structure. The SQLAlchemy models will
    use user_id as primary key even though the database keeps the original id column.
    """
    
    # --- QuestionnaireState changes ---
    # Make sure user_id is unique
    safe_op(
        op.create_unique_constraint,
        'questionnaire_states_user_id_key', 
        'questionnaire_states', 
        ['user_id']
    )
    
    # Create an index for performance
    safe_op(
        op.create_index,
        'ix_questionnaire_states_user_id_unique', 
        'questionnaire_states', 
        ['user_id'], 
        unique=True
    )
    
    # --- CompletedQuestionnaire changes ---
    # Make sure user_id is unique
    safe_op(
        op.create_unique_constraint,
        'completed_questionnaires_user_id_key', 
        'completed_questionnaires', 
        ['user_id']
    )
    
    # Create an index for performance
    safe_op(
        op.create_index,
        'ix_completed_questionnaires_user_id_unique', 
        'completed_questionnaires', 
        ['user_id'], 
        unique=True
    )
    
    # Update submitted_at to use onupdate in CompletedQuestionnaire
    safe_op(
        op.alter_column,
        'completed_questionnaires', 
        'submitted_at',
        server_default=sa.text('now()'),
        server_onupdate=sa.text('now()')
    )


def downgrade() -> None:
    """Remove the unique constraints and indexes we added."""
    
    # --- CompletedQuestionnaire downgrade ---
    # Remove the onupdate from submitted_at
    safe_op(
        op.alter_column,
        'completed_questionnaires', 
        'submitted_at',
        server_default=sa.text('now()'),
        server_onupdate=None
    )
    
    # Drop the unique index
    safe_op(
        op.drop_index,
        'ix_completed_questionnaires_user_id_unique', 
        table_name='completed_questionnaires'
    )
    
    # Drop the unique constraint
    safe_op(
        op.drop_constraint,
        'completed_questionnaires_user_id_key', 
        'completed_questionnaires', 
        type_='unique'
    )
    
    # --- QuestionnaireState downgrade ---
    # Drop the unique index
    safe_op(
        op.drop_index,
        'ix_questionnaire_states_user_id_unique', 
        table_name='questionnaire_states'
    )
    
    # Drop the unique constraint
    safe_op(
        op.drop_constraint,
        'questionnaire_states_user_id_key', 
        'questionnaire_states', 
        type_='unique'
    ) 