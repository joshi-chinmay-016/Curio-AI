import uuid
import sqlalchemy as sa
from sqlalchemy import Column, DateTime, String, Integer, Text, ForeignKey, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    status = Column(String, default="UPLOADED", nullable=False)
    storage_path = Column(String, nullable=True)
    content_hash = Column(String, nullable=True)
    page_count = Column(Integer, nullable=True)
    processing_error = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    embedding_model = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan", lazy="dynamic")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    chunk_metadata = Column(JSON, nullable=True)
    embedding = Column(Text, nullable=True)  # Store as text for flexibility; pgvector.Vector(dim) can be used when model is finalized
    embedding_model = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    document = relationship("Document", back_populates="chunks")

    # Ensure unique chunk_index per document
    __table_args__ = (
        sa.UniqueConstraint('document_id', 'chunk_index', name='uq_document_chunk_index'),
    )
