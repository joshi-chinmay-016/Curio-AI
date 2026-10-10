"""add_document_ownership_and_status

Revision ID: add_document_ownership
Revises: 9b3012f5a0bb
Create Date: 2026-10-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'add_document_ownership'
down_revision: Union[str, None] = '9b3012f5a0bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to documents table
    op.add_column('documents', sa.Column('user_id', UUID(as_uuid=True), nullable=True))
    op.add_column('documents', sa.Column('status', sa.String(), server_default='UPLOADED', nullable=False))
    op.add_column('documents', sa.Column('storage_path', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('content_hash', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('page_count', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('processing_error', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('chunk_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('documents', sa.Column('embedding_model', sa.String(), nullable=True))

    # Create index on user_id
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)

    # If there are existing documents, we need to handle them safely
    # Get a valid user_id to assign to orphaned documents (first user in system)
    # This is a safe approach - we assign existing documents to the first user
    # In production, this would need manual review, but for dev/test it's acceptable
    connection = op.get_bind()
    
    # Check if there are any existing documents without user_id
    result = connection.execute(sa.text("SELECT COUNT(*) FROM documents WHERE user_id IS NULL"))
    orphaned_count = result.scalar()
    
    if orphaned_count > 0:
        # Get the first user to assign orphaned documents
        user_result = connection.execute(sa.text("SELECT id FROM users ORDER BY created_at LIMIT 1"))
        first_user = user_result.fetchone()
        
        if first_user:
            # Assign orphaned documents to the first user
            connection.execute(
                sa.text("UPDATE documents SET user_id = :user_id WHERE user_id IS NULL"),
                {"user_id": first_user[0]}
            )
        else:
            # No users exist - delete orphaned documents (should not happen in practice)
            connection.execute(sa.text("DELETE FROM documents WHERE user_id IS NULL"))

    # Now make user_id NOT NULL and add FK constraint
    op.alter_column('documents', 'user_id', nullable=False)
    op.create_foreign_key(
        'fk_documents_user_id_users',
        'documents', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Drop FK constraint first
    op.drop_constraint('fk_documents_user_id_users', 'documents', type_='foreignkey')
    
    # Drop index
    op.drop_index(op.f('ix_documents_user_id'), table_name='documents')
    
    # Drop columns
    op.drop_column('documents', 'embedding_model')
    op.drop_column('documents', 'chunk_count')
    op.drop_column('documents', 'processing_error')
    op.drop_column('documents', 'page_count')
    op.drop_column('documents', 'content_hash')
    op.drop_column('documents', 'storage_path')
    op.drop_column('documents', 'status')
    op.drop_column('documents', 'user_id')