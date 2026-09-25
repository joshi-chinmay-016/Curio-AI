import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Float, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


class UserConceptProgress(Base):
    __tablename__ = "user_concept_progress"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        index=True,
    )
    concept = Column(String, nullable=False, primary_key=True)
    mastery_score = Column(Float, default=0.0, nullable=False)
    total_attempts = Column(Integer, default=0, nullable=False)
    successful_attempts = Column(Integer, default=0, nullable=False)
    last_practiced_at = Column(DateTime(timezone=True), nullable=True)
    last_difficulty = Column(Integer, default=1, nullable=False)
    misconception_count = Column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="concept_progress")

    __table_args__ = (
        UniqueConstraint("user_id", "concept", name="uq_user_concept"),
    )