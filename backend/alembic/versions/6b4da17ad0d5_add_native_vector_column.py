"""add_native_vector_column

Revision ID: 6b4da17ad0d5
Revises: d05335a73981
Create Date: 2026-10-09 21:44:44.211490

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b4da17ad0d5'
down_revision: Union[str, None] = 'd05335a73981'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add native pgvector column for 1536-dimensional embeddings
    op.add_column(
        'document_chunks',
        sa.Column('embedding_vector', sa.Text(), nullable=True)  # Will be cast to vector(1536) below
    )
    
    # Convert the text column to native vector type
    op.execute("""
        ALTER TABLE document_chunks 
        ALTER COLUMN embedding_vector TYPE vector(1536) 
        USING CASE 
            WHEN embedding IS NOT NULL AND embedding != '' 
            THEN embedding::vector 
            ELSE NULL 
        END
    """)
    
    # Create HNSW index for cosine similarity search
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_vector_hnsw
        ON document_chunks 
        USING hnsw (embedding_vector vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    # Drop HNSW index
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_vector_hnsw")
    
    # Drop the vector column
    op.drop_column('document_chunks', 'embedding_vector')