"""drop_evidence_snapshot_id_from_report_versions

Revision ID: 9b3012f5a0bb
Revises: a1b2c3d4e5f7
Create Date: 2026-10-03 21:53:44.192278

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b3012f5a0bb'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_session_report_versions_snapshot', table_name='session_report_versions')
    op.drop_column('session_report_versions', 'evidence_snapshot_id')


def downgrade() -> None:
    op.add_column(
        'session_report_versions',
        sa.Column('evidence_snapshot_id', sa.UUID(as_uuid=True), sa.ForeignKey('report_evidence_snapshots.id', ondelete='RESTRICT'), nullable=True, unique=True)
    )
    op.create_index('ix_session_report_versions_snapshot', 'session_report_versions', ['evidence_snapshot_id'])
