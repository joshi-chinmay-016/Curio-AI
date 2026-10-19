"""
Voice transcription router (Phase 1, Task 1.3).

Provides:
- POST /api/v1/voice/transcribe: Authenticated endpoint accepting an audio upload
  and returning transcribed text, detected language, and duration.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.app.api.deps import get_current_active_user
from backend.app.models.user import User
from backend.app.schemas.voice import TranscriptionResponse
from backend.app.services.voice_service import VoiceService, get_voice_service

router = APIRouter()


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe spoken audio question",
    description=(
        "Accepts a recorded audio file (e.g. WebM, Opus, WAV, MP3, OGG, M4A), "
        "validates its integrity and decodability, and transcribes the speech into text "
        "using Whisper."
    ),
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio recording file (multipart/form-data)"),
    current_user: User = Depends(get_current_active_user),
    voice_service: VoiceService = Depends(get_voice_service),
) -> TranscriptionResponse:
    """
    Transcribe uploaded audio file for authenticated users.
    
    Validations:
    - User must be authenticated and active.
    - File must be decodable audio format within configured size and duration limits.
    - Temporary staged files are automatically cleaned up.
    """
    return await voice_service.transcribe_upload(file)
