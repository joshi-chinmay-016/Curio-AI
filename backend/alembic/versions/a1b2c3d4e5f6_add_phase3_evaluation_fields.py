"""add_phase3_evaluation_fields

Revision ID: a1b2c3d4e5f6
Revises: 6cfd93685f71
Create Date: 2026-09-20 20:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '6cfd93685f71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('session_reports', sa.Column('evidence_confidence', sa.Float(), server_default='0.0', nullable=False))
    op.add_column('session_reports', sa.Column('concept_assessments', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('session_reports', sa.Column('resolved_gaps', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('session_reports', sa.Column('unresolved_gaps', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('session_reports', sa.Column('resolved_misconceptions', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('session_reports', sa.Column('unresolved_misconceptions', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('session_reports', sa.Column('session_evaluation', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('session_reports', 'session_evaluation')
    op.drop_column('session_reports', 'unresolved_misconceptions')
    op.drop_column('session_reports', 'resolved_misconceptions')
    op.drop_column('session_reports', 'unresolved_gaps')
    op.drop_column('session_reports', 'resolved_gaps')
    op.drop_column('session_reports', 'concept_assessments')
    op.drop_column('session_reports', 'evidence_confidence')
