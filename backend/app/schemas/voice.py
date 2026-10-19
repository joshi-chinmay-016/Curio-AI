from typing import Optional
from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    """
    Schema for successful voice transcription response.
    """
    text: str = Field(..., description="Recognized speech transcript text")
    language: str = Field(..., description="Detected ISO language code (e.g., 'en')")
    duration_seconds: Optional[float] = Field(
        None,
        description="Audio duration in seconds (if reliably determinable)"
    )
