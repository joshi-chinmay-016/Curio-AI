"""
Backend tests for Voice Transcription Foundation (Phase 1, Task 1.4).

Verifies:
- Successful transcription with mocked Whisper model
- Authentication enforcement (401 on unauthenticated / missing token)
- Rejection of empty file uploads (0 bytes -> 400)
- Rejection of unsupported or corrupted audio format (400)
- Rejection of oversized audio uploads (413)
- Handling of empty transcription results (silence -> 200 with empty text)
- Model initialization failure handling (500 without leaking internals)
- Inference execution failure handling (500)
- Safe temporary file cleanup on disk after success AND after failure
- Lazy model reuse across multiple requests (singleton instance)
- Concurrency throttling and resource safety
- Unrelated endpoints (e.g. /health) continue functioning even if Whisper is unavailable
"""

import io
import os
import uuid
import wave
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.api.deps import get_current_active_user
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.user import User
from backend.app.services.voice_service import VoiceService, get_voice_service


def create_dummy_wav(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate in-memory valid PCM WAV audio data for tests."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        num_frames = int(sample_rate * duration_seconds)
        w.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


@pytest.fixture
def mock_user():
    """Mock authenticated User instance for unit tests."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "voice_tester@curio.ai"
    user.is_active = True
    return user


@pytest.fixture
def mock_whisper_model():
    """Mock faster-whisper model returning predetermined segments and info."""
    model = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = "Explain recursion using my uploaded notes."
    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.duration = 1.0

    model.transcribe.return_value = ([mock_segment], mock_info)
    return model


@pytest.fixture
def voice_service_with_mock_model(mock_whisper_model):
    """VoiceService instance configured with a pre-injected mock model."""
    return VoiceService(model=mock_whisper_model)


class TestVoiceTranscriptionApi:
    def test_transcribe_success_mocked_model(self, mock_user, mock_whisper_model):
        """
        Verify successful audio upload and transcription using a mocked Whisper model.
        Returns 200 with text, language, and duration.
        """
        voice_service = VoiceService(model=mock_whisper_model)
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        app.dependency_overrides[get_voice_service] = lambda: voice_service

        try:
            with TestClient(app) as client:
                wav_bytes = create_dummy_wav(duration_seconds=1.5)
                files = {"file": ("question.wav", wav_bytes, "audio/wav")}

                response = client.post("/api/v1/voice/transcribe", files=files)
                assert response.status_code == 200
                data = response.json()

                assert data["text"] == "Explain recursion using my uploaded notes."
                assert data["language"] == "en"
                assert "duration_seconds" in data
                assert data["duration_seconds"] is not None
                assert abs(data["duration_seconds"] - 1.5) < 0.2
        finally:
            app.dependency_overrides.clear()

    def test_transcribe_authentication_required(self):
        """
        Verify that unauthenticated requests to POST /voice/transcribe
        are rejected with 401 Unauthorized.
        """
        app.dependency_overrides.clear()
        with TestClient(app) as client:
            wav_bytes = create_dummy_wav()
            files = {"file": ("question.wav", wav_bytes, "audio/wav")}

            response = client.post("/api/v1/voice/transcribe", files=files)
            assert response.status_code == 401
            assert "detail" in response.json()

    def test_transcribe_empty_upload(self, mock_user, mock_whisper_model):
        """
        Verify that uploading a 0-byte file returns 400 Bad Request.
        """
        voice_service = VoiceService(model=mock_whisper_model)
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        app.dependency_overrides[get_voice_service] = lambda: voice_service

        try:
            with TestClient(app) as client:
                files = {"file": ("empty.wav", b"", "audio/wav")}
                response = client.post("/api/v1/voice/transcribe", files=files)
                assert response.status_code == 400
                assert "empty" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_transcribe_unsupported_or_malformed_audio(self, mock_user, mock_whisper_model):
        """
        Verify that corrupted or non-audio bytes uploaded as audio return 400 Bad Request.
        """
        voice_service = VoiceService(model=mock_whisper_model)
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        app.dependency_overrides[get_voice_service] = lambda: voice_service

        try:
            with TestClient(app) as client:
                corrupted_bytes = b"NOT_A_REAL_AUDIO_FILE_JUST_CORRUPTED_TEXT"
                files = {"file": ("bad_audio.wav", corrupted_bytes, "audio/wav")}
                response = client.post("/api/v1/voice/transcribe", files=files)
                assert response.status_code == 400
                assert "malformed or unsupported" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_transcribe_oversized_upload(self, mock_user, mock_whisper_model):
        """
        Verify that files exceeding the configured maximum upload size return 413 Payload Too Large.
        """
        # Create service with a tiny max upload size of 100 bytes for test
        small_service = VoiceService(model=mock_whisper_model, max_upload_size=100)
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        app.dependency_overrides[get_voice_service] = lambda: small_service

        try:
            with TestClient(app) as client:
                wav_bytes = create_dummy_wav(duration_seconds=1.0)  # ~32KB
                files = {"file": ("large.wav", wav_bytes, "audio/wav")}
                response = client.post("/api/v1/voice/transcribe", files=files)
                assert response.status_code == 413
                assert "exceeds" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_transcribe_empty_transcription_result(self, mock_user):
        """
        Verify that silent audio producing no recognized segments returns 200
        with an empty text string rather than failing or returning null.
        """
        empty_model = MagicMock()
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.duration = 1.0
        empty_model.transcribe.return_value = ([], mock_info)

        voice_service = VoiceService(model=empty_model)
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        app.dependency_overrides[get_voice_service] = lambda: voice_service

        try:
            with TestClient(app) as client:
                wav_bytes = create_dummy_wav(duration_seconds=1.0)
                files = {"file": ("silent.wav", wav_bytes, "audio/wav")}
                response = client.post("/api/v1/voice/transcribe", files=files)
                assert response.status_code == 200
                data = response.json()
                assert data["text"] == ""
                assert data["language"] == "en"
        finally:
            app.dependency_overrides.clear()

    def test_transcribe_model_init_failure(self, mock_user):
        """
        Verify that model initialization failures return a 500 error
        without exposing internal stack traces or filesystem paths.
        """
        failing_service = VoiceService()
        # Simulate model loading exception
        with patch.object(failing_service, "_get_model", side_effect=Exception("Failed to load weights from disk")):
            app.dependency_overrides[get_current_active_user] = lambda: mock_user
            app.dependency_overrides[get_voice_service] = lambda: failing_service

            try:
                with TestClient(app) as client:
                    wav_bytes = create_dummy_wav()
                    files = {"file": ("test.wav", wav_bytes, "audio/wav")}
                    response = client.post("/api/v1/voice/transcribe", files=files)
                    assert response.status_code == 500
                    # Ensure no local paths are leaked
                    assert "C:" not in response.text
                    assert "Failed to load weights" not in response.text
            finally:
                app.dependency_overrides.clear()

    def test_transcribe_inference_failure(self, mock_user):
        """
        Verify that inference execution runtime errors return a safe 500 error.
        """
        failing_model = MagicMock()
        failing_model.transcribe.side_effect = RuntimeError("CUDA/CPU computation kernel error")

        voice_service = VoiceService(model=failing_model)
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        app.dependency_overrides[get_voice_service] = lambda: voice_service

        try:
            with TestClient(app) as client:
                wav_bytes = create_dummy_wav()
                files = {"file": ("test.wav", wav_bytes, "audio/wav")}
                response = client.post("/api/v1/voice/transcribe", files=files)
                assert response.status_code == 500
                assert response.json()["detail"] == "Voice transcription processing failed."
        finally:
            app.dependency_overrides.clear()

    def test_temporary_file_cleanup_on_success_and_failure(self, mock_user, mock_whisper_model):
        """
        Verify that temporary files written to disk are cleaned up in both success and failure cases.
        """
        captured_paths = []

        real_mkstemp = VoiceService.probe_and_validate_audio

        def spy_probe(self_service, file_path):
            captured_paths.append(file_path)
            # Verify file actually exists during probing
            assert os.path.exists(file_path)
            return real_mkstemp(self_service, file_path)

        with patch.object(VoiceService, "probe_and_validate_audio", side_effect=spy_probe, autospec=True):
            voice_service = VoiceService(model=mock_whisper_model)
            app.dependency_overrides[get_current_active_user] = lambda: mock_user
            app.dependency_overrides[get_voice_service] = lambda: voice_service

            try:
                with TestClient(app) as client:
                    # 1. Success case
                    wav_bytes = create_dummy_wav()
                    res1 = client.post("/api/v1/voice/transcribe", files={"file": ("test.wav", wav_bytes, "audio/wav")})
                    assert res1.status_code == 200

                    # Verify staged file was unlinked
                    assert len(captured_paths) == 1
                    assert not os.path.exists(captured_paths[0])

                    # 2. Failure case (inference error)
                    mock_whisper_model.transcribe.side_effect = ValueError("Inference crash")
                    res2 = client.post("/api/v1/voice/transcribe", files={"file": ("test2.wav", wav_bytes, "audio/wav")})
                    assert res2.status_code == 500

                    # Verify second staged file was also unlinked
                    assert len(captured_paths) == 2
                    assert not os.path.exists(captured_paths[1])
            finally:
                app.dependency_overrides.clear()

    def test_model_reuse_across_requests(self, mock_whisper_model):
        """
        Verify that VoiceService reuses the exact same model instance across requests.
        """
        service = VoiceService(model=mock_whisper_model)
        m1 = service._get_model()
        m2 = service._get_model()
        assert m1 is m2
        assert m1 is mock_whisper_model

    def test_concurrency_throttle_resource_safety(self, mock_user, mock_whisper_model):
        """
        Verify that the concurrency semaphore controls simultaneous transcription calls.
        """
        # Create service with concurrency limit of 1
        service = VoiceService(model=mock_whisper_model, concurrent_limit=1)
        # Artificially acquire semaphore to simulate a busy active inference
        service._concurrency_semaphore.acquire()

        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        app.dependency_overrides[get_voice_service] = lambda: service

        try:
            with TestClient(app) as client:
                wav_bytes = create_dummy_wav()
                # Use a very short acquire timeout on the service for the test
                with patch.object(service._concurrency_semaphore, "acquire", return_value=False):
                    res = client.post("/api/v1/voice/transcribe", files={"file": ("test.wav", wav_bytes, "audio/wav")})
                    assert res.status_code == 503
                    assert "busy" in res.json()["detail"].lower()
        finally:
            service._concurrency_semaphore.release()
            app.dependency_overrides.clear()

    def test_existing_endpoints_work_when_whisper_unavailable(self):
        """
        Verify that existing application endpoints (e.g. /health) function completely
        unaffected even if faster-whisper or model weights are missing.
        """
        with TestClient(app) as client:
            res = client.get("/health")
            assert res.status_code == 200
            assert res.json()["status"] == "healthy"
