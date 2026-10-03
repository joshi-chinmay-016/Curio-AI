import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


class ReportEvidenceSnapshot(Base):
    __tablename__ = "report_evidence_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    report_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("session_report_versions.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    schema_version = Column(Integer, default=1, nullable=False)
    evidence_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    report_version = relationship(
        "SessionReportVersion",
        back_populates="evidence_snapshot",
        foreign_keys="ReportEvidenceSnapshot.report_version_id",
    )

    __table_args__ = (
        UniqueConstraint("report_version_id", name="uq_report_evidence_snapshot_version"),
    )