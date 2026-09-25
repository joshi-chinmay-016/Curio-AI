"""add_user_concept_progress

Revision ID: d3c4dafb5201
Revises: d9640bb3d3cf
Create Date: 2026-09-25 20:09:22.860087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3c4dafb5201'
down_revision: Union[str, None] = 'd9640bb3d3cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_concept_progress",
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("concept", sa.String(), primary_key=True, nullable=False),
        sa.Column("mastery_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("total_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("successful_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_practiced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_difficulty", sa.Integer(), server_default="1", nullable=False),
        sa.Column("misconception_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_unique_constraint("uq_user_concept", "user_concept_progress", ["user_id", "concept"])


def downgrade() -> None:
    op.drop_constraint("uq_user_concept", "user_concept_progress", type_="unique")
    op.drop_table("user_concept_progress")
