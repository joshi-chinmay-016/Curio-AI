"""add_teacher_mode_state_fields

Revision ID: 84274ca763eb
Revises: a1b2c3d4e5f6
Create Date: 2026-09-21 20:27:38.919237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84274ca763eb'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('session_states', sa.Column('teacher_attempt_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('session_states', sa.Column('teacher_intervention', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('session_states', 'teacher_intervention')
    op.drop_column('session_states', 'teacher_attempt_count')
