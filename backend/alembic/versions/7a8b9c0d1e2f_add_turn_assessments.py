"""add_turn_assessments

Revision ID: 7a8b9c0d1e2f
Revises: 602e5c00140b
Create Date: 2026-09-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a8b9c0d1e2f'
down_revision: Union[str, None] = '602e5c00140b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "turn_assessments",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("message_id", sa.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("session_id", sa.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("learning_assessment", sa.JSON(), nullable=True),
        sa.Column("turn_interpretation", sa.JSON(), nullable=True),
        sa.Column("learning_objective", sa.JSON(), nullable=True),
        sa.Column("question_specification", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Composite indexes for common query patterns
    op.create_index("ix_turn_assessments_session_id_created_at", "turn_assessments", ["session_id", "created_at"])
    op.create_index("ix_turn_assessments_user_id_session_id", "turn_assessments", ["user_id", "session_id"])


def downgrade() -> None:
    op.drop_index("ix_turn_assessments_user_id_session_id", table_name="turn_assessments")
    op.drop_index("ix_turn_assessments_session_id_created_at", table_name="turn_assessments")
    op.drop_table("turn_assessments")