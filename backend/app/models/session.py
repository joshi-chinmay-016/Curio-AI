import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Float, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic = Column(String, nullable=False, index=True)
    source_type = Column(String, default="GENERAL", nullable=False)  # GENERAL, DOCUMENT
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, default="ACTIVE", nullable=False)  # ACTIVE, PAUSED, COMPLETED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")
    state = relationship("SessionState", uselist=False, back_populates="session", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at")
    report = relationship("SessionReport", uselist=False, back_populates="session", cascade="all, delete-orphan")


class SessionState(Base):
    __tablename__ = "session_states"

    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True, index=True)
    current_mode = Column(String, default="STUDENT", nullable=False)  # STUDENT, TEACHER, EVALUATOR
    difficulty = Column(Integer, default=1, nullable=False)  # 1 to 5
    confidence = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    active_concept = Column(String, default="Core Definition", nullable=False)
    current_question_id = Column(UUID(as_uuid=True), nullable=True)
    interrupted_question_id = Column(UUID(as_uuid=True), nullable=True)
    consecutive_strong_answers = Column(Integer, default=0, nullable=False)
    consecutive_weak_answers = Column(Integer, default=0, nullable=False)
    unresolved_misconceptions = Column(JSON, default=list, nullable=False)  # list[str]
    mastered_concepts = Column(JSON, default=list, nullable=False)  # list[str]
    teacher_intervention_data = Column(JSON, default=dict, nullable=True)  # dict
    mode_switch_history = Column(JSON, default=list, nullable=True)  # list[dict]

    session = relationship("Session", back_populates="state")
