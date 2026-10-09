"""add_document_chunks_table

Revision ID: d05335a73981
Revises: add_document_ownership
Create Date: 2026-10-09 20:12:55.761323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = 'd05335a73981'
down_revision: Union[str, None] = 'add_document_ownership'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('start_char', sa.Integer(), nullable=True),
        sa.Column('end_char', sa.Integer(), nullable=True),
        sa.Column('chunk_metadata', JSONB(), nullable=True),
        sa.Column('embedding', sa.Text(), nullable=True),  # Store as text for flexibility; pgvector.Vector(dim) when model finalized
        sa.Column('embedding_model', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create unique constraint on (document_id, chunk_index)
    op.create_unique_constraint('uq_document_chunk_index', 'document_chunks', ['document_id', 'chunk_index'])
    
    # Create index on document_id for efficient lookups (if not exists via raw SQL)
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id ON document_chunks (document_id)")


def downgrade() -> None:
    # Drop unique constraint first
    op.drop_constraint('uq_document_chunk_index', 'document_chunks', type_='unique')
    
    # Drop index
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_document_id")
    
    # Drop table
    op.drop_table('document_chunks')