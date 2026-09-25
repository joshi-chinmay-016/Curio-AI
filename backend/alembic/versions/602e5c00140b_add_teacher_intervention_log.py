"""add_teacher_intervention_log

Revision ID: 602e5c00140b
Revises: d3c4dafb5201
Create Date: 2026-09-25 21:20:28.665122

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '602e5c00140b'
down_revision: Union[str, None] = 'd3c4dafb5201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teacher_intervention_logs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("gap", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("teacher_explanation", sa.Text(), nullable=True),
        sa.Column("verification_question", sa.Text(), nullable=True),
        sa.Column("verification_answer", sa.Text(), nullable=True),
        sa.Column("verification_passed", sa.Integer(), nullable=True),
        sa.Column("intervention_type", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("teacher_intervention_logs")
