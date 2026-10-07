import uuid
from sqlalchemy import Column, DateTime, String, Integer, Text, ForeignKey, func
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
