"""add_report_evidence_snapshots

Revision ID: a1b2c3d4e5f7
Revises: 8b9c0d1e2f3a
Create Date: 2026-10-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = '8b9c0d1e2f3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create report_evidence_snapshots table
    op.create_table(
        'report_evidence_snapshots',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('report_version_id', sa.UUID(as_uuid=True), sa.ForeignKey('session_report_versions.id', ondelete='RESTRICT'), nullable=False, unique=True, index=True),
        sa.Column('schema_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('evidence_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_unique_constraint('uq_report_evidence_snapshot_version', 'report_evidence_snapshots', ['report_version_id'])
    op.create_index('ix_report_evidence_snapshots_version', 'report_evidence_snapshots', ['report_version_id'])

    # 2. Add evidence_snapshot_id to session_report_versions
    op.add_column(
        'session_report_versions',
        sa.Column('evidence_snapshot_id', sa.UUID(as_uuid=True), sa.ForeignKey('report_evidence_snapshots.id', ondelete='RESTRICT'), nullable=True, unique=True, index=True),
    )
    op.create_index('ix_session_report_versions_snapshot', 'session_report_versions', ['evidence_snapshot_id'])


def downgrade() -> None:
    op.drop_index('ix_session_report_versions_snapshot', table_name='session_report_versions')
    op.drop_column('session_report_versions', 'evidence_snapshot_id')
    op.drop_index('ix_report_evidence_snapshots_version', table_name='report_evidence_snapshots')
    op.drop_constraint('uq_report_evidence_snapshot_version', 'report_evidence_snapshots', type_='unique')
    op.drop_table('report_evidence_snapshots')