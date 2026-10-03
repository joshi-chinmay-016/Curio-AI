from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class TimelineEvent(BaseModel):
    event_type: str
    timestamp: datetime
    session_id: UUID
    message_id: Optional[UUID] = None
    entity_id: Optional[UUID] = None
    metadata: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class TimelineListResponse(BaseModel):
    items: List[TimelineEvent]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int

    model_config = ConfigDict(from_attributes=True)


SUPPORTED_EVENT_TYPES = [
    "session_created",
    "user_message",
    "evaluation",
    "turn_assessment",
    "teacher_intervention",
    "report_generated",
    "session_ended",
]

DEFAULT_EVENT_TYPES = SUPPORTED_EVENT_TYPES