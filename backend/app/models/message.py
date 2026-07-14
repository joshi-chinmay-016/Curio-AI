import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String, nullable=False)  # USER, AI
    content = Column(Text, nullable=False)
    input_type = Column(String, default="TEXT", nullable=False)  # TEXT, VOICE
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)

    session = relationship("Session", back_populates="messages")
    evaluation = relationship("TurnEvaluation", uselist=False, back_populates="message", cascade="all, delete-orphan")
