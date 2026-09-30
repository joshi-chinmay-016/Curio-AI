import uuid
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


class TurnAssessment(Base):
    __tablename__ = "turn_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    learning_assessment = Column(JSON, nullable=True)
    turn_interpretation = Column(JSON, nullable=True)
    learning_objective = Column(JSON, nullable=True)
    question_specification = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    message = relationship("Message", backref="turn_assessment")
    session = relationship("Session", backref="turn_assessments")
    user = relationship("User", backref="turn_assessments")


Index("ix_turn_assessments_session_id_created_at", TurnAssessment.session_id, TurnAssessment.created_at)
Index("ix_turn_assessments_user_id_session_id", TurnAssessment.user_id, TurnAssessment.session_id)