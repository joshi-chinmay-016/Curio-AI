import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Float, Integer, String, JSON, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.session import Base
from backend.app.models.report_evidence_snapshot import ReportEvidenceSnapshot


class SessionReportVersion(Base):
    __tablename__ = "session_report_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    # Parity with SessionReport fields
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
    personalized_roadmap = Column(JSON, default=list, nullable=False)  # list[dict]
    recommended_exercises = Column(JSON, default=list, nullable=False)  # list[str]
    evidence_confidence = Column(Float, default=0.0, nullable=False)
    concept_assessments = Column(JSON, default=list, nullable=False)
    resolved_gaps = Column(JSON, default=list, nullable=False)
    unresolved_gaps = Column(JSON, default=list, nullable=False)
    resolved_misconceptions = Column(JSON, default=list, nullable=False)
    unresolved_misconceptions = Column(JSON, default=list, nullable=False)
    session_evaluation = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("Session", back_populates="report_versions")
    evidence_snapshot = relationship(
        "ReportEvidenceSnapshot",
        back_populates="report_version",
        uselist=False,
        foreign_keys=ReportEvidenceSnapshot.report_version_id,
    )

    __table_args__ = (
        UniqueConstraint("session_id", "version_number", name="uq_session_report_version"),
    )