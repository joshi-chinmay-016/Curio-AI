import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Float, Integer, String, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

class SessionReport(Base):
    __tablename__ = "session_reports"

    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True, index=True)
    understanding_score = Column(Float, default=0.0, nullable=False)
    mastery_level = Column(String, default="BEGINNER", nullable=False)  # BEGINNER, DEVELOPING, PROFICIENT, MASTERY
    strengths = Column(JSON, default=list, nullable=False)  # list[str]
    high_priority_learning_gaps = Column(JSON, default=list, nullable=False)  # list[str]
    medium_priority_learning_gaps = Column(JSON, default=list, nullable=False)  # list[str]
    low_priority_learning_gaps = Column(JSON, default=list, nullable=False)  # list[str]
    misconceptions_detected = Column(JSON, default=list, nullable=False)  # list[str]
    concepts_mastered = Column(JSON, default=list, nullable=False)  # list[str]
    teacher_interventions_required = Column(Integer, default=0, nullable=False)
    difficulty_achieved = Column(Integer, default=1, nullable=False)
    personalized_roadmap = Column(JSON, default=list, nullable=False)  # list[str]
    recommended_exercises = Column(JSON, default=list, nullable=False)  # list[str]
    evidence_confidence = Column(Float, default=0.0, nullable=False)
    concept_assessments = Column(JSON, default=list, nullable=False)
    resolved_gaps = Column(JSON, default=list, nullable=False)
    unresolved_gaps = Column(JSON, default=list, nullable=False)
    resolved_misconceptions = Column(JSON, default=list, nullable=False)
    unresolved_misconceptions = Column(JSON, default=list, nullable=False)
    session_evaluation = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("Session", back_populates="report")
