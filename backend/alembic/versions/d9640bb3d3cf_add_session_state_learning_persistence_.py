"""add_session_state_learning_persistence_fields

Revision ID: d9640bb3d3cf
Revises: b4e440204004
Create Date: 2026-09-25 19:22:56.777062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9640bb3d3cf'
down_revision: Union[str, None] = 'b4e440204004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('session_states', sa.Column('concept_mastery', sa.JSON(), server_default='{}', nullable=False))
    op.add_column('session_states', sa.Column('misconception_counts', sa.JSON(), server_default='{}', nullable=False))
    op.add_column('session_states', sa.Column('recent_strategy_history', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('session_states', sa.Column('mode_switch_history', sa.JSON(), server_default='[]', nullable=False))


def downgrade() -> None:
    op.drop_column('session_states', 'mode_switch_history')
    op.drop_column('session_states', 'recent_strategy_history')
    op.drop_column('session_states', 'misconception_counts')
    op.drop_column('session_states', 'concept_mastery')
