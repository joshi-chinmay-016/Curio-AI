"""add_composite_indexes_for_performance

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-11-02 23:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Composite index for session history ordering by user
    op.create_index(
        'ix_sessions_user_created',
        'sessions',
        ['user_id', sa.text('created_at DESC')]
    )

    # 2. Composite index for message retrieval by session in chronological order
    op.create_index(
        'ix_messages_session_created',
        'messages',
        ['session_id', sa.text('created_at ASC')]
    )

    # 3. Composite index for teacher intervention logs by session in chronological order
    op.create_index(
        'ix_teacher_interventions_session_created',
        'teacher_intervention_logs',
        ['session_id', sa.text('created_at ASC')]
    )


def downgrade() -> None:
    op.drop_index('ix_teacher_interventions_session_created', table_name='teacher_intervention_logs')
    op.drop_index('ix_messages_session_created', table_name='messages')
    op.drop_index('ix_sessions_user_created', table_name='sessions')
