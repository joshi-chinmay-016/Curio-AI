"""
Voice transcription service using faster-whisper.

Production-conscious service providing:
- Lazy, thread-safe Whisper model initialization (never loaded at import time)
- Memory and CPU resource throttling via concurrency semaphore
- Robust audio format and decodability validation via PyAV container probing
- Maximum upload size and audio duration enforcement
- Secure temporary file handling with guaranteed cleanup on success and failure
- Zero logging of sensitive audio bytes or raw transcripts
- Dependency-injection friendly architecture for mockable testing
"""

import io
import logging
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, Tuple, Any

import av
from fastapi import HTTPException, UploadFile, status

from backend.app.core.config import settings
from backend.app.schemas.voice import TranscriptionResponse

logger = logging.getLogger("curio_voice")


class VoiceService:
    def __init__(
        self,
        model: Optional[Any] = None,
        model_size: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
        max_upload_size: Optional[int] = None,
        max_duration_seconds: Optional[float] = None,
        concurrent_limit: Optional[int] = None,
    ):
        """
        Initialize VoiceService.
        
        If a model is injected (e.g. for testing), it is used directly.
        Otherwise, model loading is deferred until the first transcription request.
        """
        self._model = model
        self._model_size = model_size or settings.VOICE_WHISPER_MODEL
        self._device = device or settings.VOICE_DEVICE
        self._compute_type = compute_type or settings.VOICE_COMPUTE_TYPE
        self._max_upload_size = max_upload_size or settings.VOICE_MAX_UPLOAD_SIZE
        self._max_duration_seconds = max_duration_seconds or settings.VOICE_MAX_AUDIO_DURATION_SECONDS
        
        self._model_lock = threading.Lock()
        limit = concurrent_limit or settings.VOICE_CONCURRENT_REQUEST_LIMIT
        self._concurrency_semaphore = threading.Semaphore(limit)

    def _get_model(self) -> Any:
        """
        Thread-safe lazy initialization of faster-whisper WhisperModel.
        """
        if self._model is not None:
            return self._model

        with self._model_lock:
            if self._model is not None:
                return self._model

            try:
                from faster_whisper import WhisperModel

                logger.info(
                    "Initializing WhisperModel (model=%s, device=%s, compute_type=%s)",
                    self._model_size,
                    self._device,
                    self._compute_type,
                )
                start_time = time.time()
                self._model = WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                logger.info("WhisperModel successfully initialized in %.2fs", time.time() - start_time)
                return self._model
            except Exception as e:
                logger.error("Failed to load WhisperModel: %s", str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Voice transcription model failed to initialize.",
                )

    def probe_and_validate_audio(self, file_path: str) -> float:
        """
        Inspect the audio container using PyAV to ensure:
        1. Container is valid and readable (not corrupted or disguised non-audio file)
        2. At least one valid audio stream is present
        3. Duration does not exceed maximum duration limit
        
        Returns the duration in seconds (or 0.0 if not strictly determinable).
        """
        try:
            container = av.open(file_path)
        except Exception as e:
            logger.warning("Audio decoding validation failed: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed or unsupported audio format.",
            )

        try:
            audio_streams = container.streams.audio
            if not audio_streams:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No audio streams found in uploaded file.",
                )

            # Determine duration
            duration_sec = 0.0
            if container.duration is not None:
                duration_sec = float(container.duration) / 1000000.0
            elif audio_streams[0].duration is not None and audio_streams[0].time_base is not None:
                duration_sec = float(audio_streams[0].duration * audio_streams[0].time_base)

            if duration_sec > self._max_duration_seconds:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Audio duration ({duration_sec:.1f}s) exceeds the maximum allowed limit of {self._max_duration_seconds}s.",
                )

            return duration_sec
        finally:
            container.close()

    async def transcribe_upload(self, upload_file: UploadFile) -> TranscriptionResponse:
        """
        Process an uploaded audio file and return the transcription result.
        
        Guarantees:
        - Upload size validation while streaming
        - MIME type check
        - Audio stream decodability validation
        - Concurrency throttling
        - Safe temp file cleanup in finally block
        - No audio content or raw transcript logging
        """
        # Validate MIME type if provided
        content_type = (upload_file.content_type or "").lower().split(";")[0].strip()
        if content_type and content_type not in settings.VOICE_ALLOWED_MIME_TYPES:
            # We log a warning but proceed to probe container decodability,
            # as browsers sometimes send audio/webm with diverse codecs or octet-stream
            logger.warning("Unusual audio MIME type received: %s. Probing actual container.", content_type)

        # Derive safe file extension
        original_filename = upload_file.filename or "recording.webm"
        suffix = Path(original_filename).suffix.lower()
        if not suffix:
            suffix = ".webm"

        # Stream file to secure temporary location while checking size
        temp_fd, temp_path = tempfile.mkstemp(prefix="curio_voice_", suffix=suffix)
        total_bytes = 0

        try:
            with os.fdopen(temp_fd, "wb") as f:
                while True:
                    chunk = await upload_file.read(settings.UPLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > self._max_upload_size:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Audio file size exceeds the limit of {self._max_upload_size // (1024 * 1024)}MB.",
                        )
                    f.write(chunk)

            if total_bytes == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Audio file is empty (0 bytes).",
                )

            # Probe container and validate decodability & duration
            duration_sec = self.probe_and_validate_audio(temp_path)

            # Acquire concurrency semaphore to protect CPU/memory resources
            acquired = self._concurrency_semaphore.acquire(blocking=True, timeout=10.0)
            if not acquired:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Transcription service is busy. Please try again shortly.",
                )

            try:
                try:
                    model = self._get_model()
                except HTTPException:
                    raise
                except Exception as model_err:
                    logger.error("Failed to obtain Whisper model: %s", str(model_err))
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Voice transcription model failed to initialize.",
                    )

                start_infer = time.time()

                # Perform transcription
                # vad_filter=True strips silence and improves processing speed
                try:
                    segments, info = model.transcribe(
                        temp_path,
                        beam_size=1,
                        vad_filter=True,
                    )
                    # Segments is a generator; consume it to extract text
                    text_parts = [segment.text for segment in segments]
                    transcript = "".join(text_parts).strip()
                    detected_language = getattr(info, "language", "en") or "en"
                except Exception as infer_err:
                    logger.error("Inference execution failed: %s", str(infer_err))
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Voice transcription processing failed.",
                    )

                latency = time.time() - start_infer
                logger.info(
                    "Voice transcription completed: duration=%.2fs, size=%d bytes, language=%s, infer_time=%.2fs",
                    duration_sec,
                    total_bytes,
                    detected_language,
                    latency,
                )

                return TranscriptionResponse(
                    text=transcript,
                    language=detected_language,
                    duration_seconds=round(duration_sec, 2) if duration_sec > 0 else None,
                )
            finally:
                self._concurrency_semaphore.release()

        finally:
            # Guarantee temporary file is cleaned up on disk
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as cleanup_err:
                logger.warning("Failed to clean up temp voice file %s: %s", temp_path, str(cleanup_err))


# Singleton instance managed across application lifespan
_voice_service_instance: Optional[VoiceService] = None
_instance_lock = threading.Lock()


def get_voice_service() -> VoiceService:
    """
    Dependency provider for VoiceService.
    Ensures a single shared instance is reused across requests.
    """
    global _voice_service_instance
    if _voice_service_instance is None:
        with _instance_lock:
            if _voice_service_instance is None:
                _voice_service_instance = VoiceService()
    return _voice_service_instance
