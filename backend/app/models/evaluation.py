import uuid
from sqlalchemy import Column, ForeignKey, Float, Text, JSON, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

class TurnEvaluation(Base):
    __tablename__ = "turn_evaluations"

    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True, index=True)
    correctness = Column(Float, default=0.0, nullable=False)
    clarity = Column(Float, default=0.0, nullable=False)
    completeness = Column(Float, default=0.0, nullable=False)
    depth = Column(Float, default=0.0, nullable=False)
    relevance = Column(Float, default=0.0, nullable=False)
    stuck_probability = Column(Float, default=0.0, nullable=False)
    misconceptions = Column(JSON, default=list, nullable=False)  # list[str]
    missing_concepts = Column(JSON, default=list, nullable=False)  # list[str]
    undefined_terms = Column(JSON, default=list, nullable=False)  # list[str]
    mastered_concepts = Column(JSON, default=list, nullable=False)  # list[str]
    knowledge_gap = Column(Text, nullable=True)
    recommended_strategy = Column(String, nullable=False)
    recommended_difficulty = Column(Integer, default=1, nullable=False)

    message = relationship("Message", back_populates="evaluation")
