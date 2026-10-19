"""add_concept_model_to_session_states

Revision ID: e5f6a7b8c9d0
Revises: 6b4da17ad0d5
Create Date: 2026-10-19 20:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = '6b4da17ad0d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nullable concept_model JSON column to session_states table
    op.add_column(
        'session_states',
        sa.Column('concept_model', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    # Remove concept_model column from session_states table
    op.drop_column('session_states', 'concept_model')
