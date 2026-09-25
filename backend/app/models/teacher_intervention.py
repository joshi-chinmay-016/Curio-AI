import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


class TeacherInterventionLog(Base):
    __tablename__ = "teacher_intervention_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gap = Column(Text, nullable=False)
    attempt_count = Column(Integer, default=1, nullable=False)
    teacher_explanation = Column(Text, nullable=True)
    verification_question = Column(Text, nullable=True)
    verification_answer = Column(Text, nullable=True)
    verification_passed = Column(Integer, nullable=True)  # 0/1, nullable if not yet verified
    intervention_type = Column(String, nullable=True)  # enter, continue, exit, limit_fallback
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("Session", back_populates="intervention_logs")
    user = relationship("User")