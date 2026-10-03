"""add_report_versions

Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-10-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b9c0d1e2f3a'
down_revision: Union[str, None] = '7a8b9c0d1e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add version_number column to session_reports table for latest cache tracking
    op.add_column(
        'session_reports',
        sa.Column('version_number', sa.Integer(), server_default='1', nullable=False)
    )

    # 2. Create immutable session_report_versions table
    op.create_table(
        'session_report_versions',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', sa.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('understanding_score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('mastery_level', sa.String(), server_default='BEGINNER', nullable=False),
        sa.Column('strengths', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('high_priority_learning_gaps', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('medium_priority_learning_gaps', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('low_priority_learning_gaps', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('misconceptions_detected', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('concepts_mastered', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('teacher_interventions_required', sa.Integer(), server_default='0', nullable=False),
        sa.Column('difficulty_achieved', sa.Integer(), server_default='1', nullable=False),
        sa.Column('personalized_roadmap', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('recommended_exercises', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('evidence_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('concept_assessments', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('resolved_gaps', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('unresolved_gaps', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('resolved_misconceptions', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('unresolved_misconceptions', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('session_evaluation', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('session_id', 'version_number', name='uq_session_report_version'),
    )

    # 3. Create composite indexes for version history retrieval and pagination
    op.create_index(
        'ix_session_report_versions_session_version',
        'session_report_versions',
        ['session_id', 'version_number'],
    )
    op.create_index(
        'ix_session_report_versions_session_created',
        'session_report_versions',
        ['session_id', 'created_at'],
    )

    # 4. Backfill existing session_reports rows as Version 1
    op.execute("""
        INSERT INTO session_report_versions (
            id,
            session_id,
            version_number,
            understanding_score,
            mastery_level,
            strengths,
            high_priority_learning_gaps,
            medium_priority_learning_gaps,
            low_priority_learning_gaps,
            misconceptions_detected,
            concepts_mastered,
            teacher_interventions_required,
            difficulty_achieved,
            personalized_roadmap,
            recommended_exercises,
            evidence_confidence,
            concept_assessments,
            resolved_gaps,
            unresolved_gaps,
            resolved_misconceptions,
            unresolved_misconceptions,
            session_evaluation,
            created_at
        )
        SELECT
            gen_random_uuid(),
            session_id,
            1,
            understanding_score,
            mastery_level,
            strengths,
            high_priority_learning_gaps,
            medium_priority_learning_gaps,
            low_priority_learning_gaps,
            misconceptions_detected,
            concepts_mastered,
            teacher_interventions_required,
            difficulty_achieved,
            personalized_roadmap,
            recommended_exercises,
            evidence_confidence,
            concept_assessments,
            resolved_gaps,
            unresolved_gaps,
            resolved_misconceptions,
            unresolved_misconceptions,
            session_evaluation,
            created_at
        FROM session_reports
        ON CONFLICT (session_id, version_number) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_index('ix_session_report_versions_session_created', table_name='session_report_versions')
    op.drop_index('ix_session_report_versions_session_version', table_name='session_report_versions')
    op.drop_table('session_report_versions')
    op.drop_column('session_reports', 'version_number')
