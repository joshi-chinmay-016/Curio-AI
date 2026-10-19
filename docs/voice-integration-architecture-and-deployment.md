# Curio AI — Voice Integration Architecture and Deployment Guide (STT + TTS)

## 1. Overview and Architecture

Curio AI includes a complete voice interaction capability that seamlessly integrates with the existing chat pipeline:

1. **Speech-to-Text (STT)**: User speaks their question or explanation; `MediaRecorder` captures audio; the authenticated backend `/api/v1/voice/transcribe` endpoint decodes and transcribes the speech using `faster-whisper`.
2. **Review-Before-Send**: The recognized transcript automatically populates the existing composer (`InputArea.tsx`). The learner reviews, edits, clarifies, or discards the text before submitting.
3. **Unified Chat Pipeline**: Submitting the transcribed question triggers the exact same `sendMessage` handler (`POST /api/v1/sessions/{id}/messages`), preserving session state, Student/Teacher modes, document grounding, MasteryGate assessment, and conversation persistence without any duplicate voice-only AI context.
4. **Text-to-Speech (TTS)**: AI responses feature an accessible read-aloud control powered by the browser's `speechSynthesis` API, modularized through an extensible `SpeechProvider` interface for future self-hosted Piper TTS support.

```mermaid
flowchart LR
    A[Learner Microphone] -->|MediaRecorder| B[Audio Blob]
    B -->|POST /api/v1/voice/transcribe| C[faster-whisper STT]
    C -->|Transcript| D[Existing InputArea Composer]
    D -->|User Review / Send| E[POST /sessions/id/messages]
    E -->|Context & Retrieval| F[CurioEngine LLM]
    F -->|Persisted Response| G[ChatBubble UI]
    G -->|Read Aloud Button| H[SpeechSynthesis TTS]
```

---

## 2. API Contract: POST /api/v1/voice/transcribe

### Request
- **Method**: `POST`
- **Path**: `/api/v1/voice/transcribe`
- **Authentication**: `Authorization: Bearer <access_token>`
- **Content-Type**: `multipart/form-data`
- **Form Field**: `file` (Binary audio upload)

### Supported Audio Formats
Validated via container stream probing (`PyAV`):
- `audio/webm;codecs=opus` (Default browser format)
- `audio/webm`
- `audio/ogg;codecs=opus`
- `audio/wav` / `audio/x-wav`
- `audio/mp3` / `audio/mpeg`
- `audio/m4a` / `audio/mp4`
- `audio/flac`

### Success Response (`200 OK`)
```json
{
  "text": "Explain recursion using my uploaded notes.",
  "language": "en",
  "duration_seconds": 3.5
}
```

### Error Responses
- **400 Bad Request**:
  - `Audio file is empty (0 bytes).`
  - `Malformed or unsupported audio format.`
  - `No audio streams found in uploaded file.`
  - `Audio duration (X.Xs) exceeds the maximum allowed limit of 300.0s.`
- **401 Unauthorized**: Missing or expired Bearer token.
- **413 Payload Too Large**: Audio file exceeds configured limit (`VOICE_MAX_UPLOAD_SIZE`, default 10MB).
- **503 Service Unavailable**: Transcription concurrency throttle saturated (all worker slots busy).
- **500 Internal Server Error**: Internal model or processing error (safe masked message without leaking system paths).

---

## 3. Configuration and Environment Variables

Configured in `backend/app/core/config.py`:

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `VOICE_WHISPER_MODEL` | `base` | Whisper model size (`tiny`, `base`, `small`, `medium`) |
| `VOICE_DEVICE` | `cpu` | Inference device (`cpu` or `cuda`) |
| `VOICE_COMPUTE_TYPE` | `int8` | Quantization type (`int8`, `float16`, `float32`) |
| `VOICE_MAX_UPLOAD_SIZE` | `10485760` (10MB) | Maximum audio upload payload in bytes |
| `VOICE_MAX_AUDIO_DURATION_SECONDS` | `300.0` (5 mins) | Maximum allowed recording duration |
| `VOICE_CONCURRENT_REQUEST_LIMIT` | `2` | Max concurrent active Whisper inference tasks |

---

## 4. Dependencies and Compatibility

### Backend Requirements
- `faster-whisper==1.2.1`: CTranslate2-accelerated inference engine.
- `av==13.1.0`: PyAV binding for FFmpeg (pinned for full parameter compatibility with faster-whisper on Python 3.12).
- `python-multipart==0.0.6`: FastAPI multipart form body parser.

### Frontend Requirements
- `MediaRecorder` API: Supported across Chrome, Edge, Firefox, and Safari 14.1+.
- Web Speech API (`window.speechSynthesis`): Universal browser TTS support.

---

## 5. Performance and Resource Benchmarks

Measured on a standard CPU test environment with `base` model in `int8` quantization:

- **Initial Cold-Start Download**: ~145 MB (downloaded once from Hugging Face Hub to `~/.cache/huggingface/hub/`).
- **Model Initialization (RAM)**: +151.9 MB RSS memory overhead.
- **Warm Model Loading Time**: ~1.5 seconds.
- **Transcription Latency**: 1.35 seconds for 3.0 seconds of audio.
- **Real-Time Factor (RTF)**: **0.45x** (transcription completes more than twice as fast as real-time audio playback).
- **Total Process Memory**: ~222 MB total RSS.

### Deployment Implications
- **CPU**: Minimum 2 vCPUs recommended for multi-user inference.
- **Memory**: ~300 MB dedicated to model inference cache.
- **Pre-baking Weights**: For Docker deployments, pre-download model weights into the container image during `docker build` using:
  ```dockerfile
  RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
  ```
  This eliminates first-request cold-start download latencies in production.

---

## 6. Privacy and Security Guardrails

1. **Zero Audio Persistence**: Audio uploads are streamed to ephemeral temporary files on disk solely for FFmpeg validation and transcription. Temporary files are **guaranteed to be deleted** in `finally:` blocks on both success and error. No audio recordings are saved to disk storage or database.
2. **Zero Transcript Leakage in Logs**: Loggers output only telemetry metadata (duration, audio size, language, inference latency). Raw speech content and transcripts are never written to server logs.
3. **Authentication Boundary**: Endpoint enforces `Depends(get_current_active_user)`.
4. **Content Sanitization for TTS**:
   - Fenced code blocks (` ```...``` `) are omitted rather than reading raw code syntax aloud.
   - Markdown formatting (`#`, `**`, `_`, links, horizontal rules) is stripped into natural conversational prose.

---

## 7. Troubleshooting Guide

### Microphone Permission Denied
- **Symptom**: "Microphone permission denied. Please allow microphone access in your browser settings."
- **Fix**: The browser requires explicit permission for the origin. If testing on Chrome, visit `chrome://settings/content/microphone` or click the lock icon in the address bar. Microphones require HTTPS in production (browsers restrict `getUserMedia` to secure origins and `localhost`).

### Model Initialization Failure on First Startup
- **Symptom**: 500 error on first voice transcription attempt.
- **Fix**: The host machine could not connect to `huggingface.co` to download initial model weights. Ensure outbound internet connectivity is enabled, or set `HF_HUB_ENABLE_HF_TRANSFER=0` / verify firewall rules. Alternatively, pre-download weights locally.

### Unsupported Browser Audio Format
- **Symptom**: "Malformed or unsupported audio format."
- **Fix**: `useAudioRecorder` negotiates supported MIME types (`isTypeSupported`). If testing on Safari/iOS, `audio/mp4` or `audio/wav` will be selected automatically.

---

## 8. Local Testing Instructions

### Run Backend Voice Tests
```bash
$env:PYTHONPATH="."
python -m pytest backend/tests/api/test_voice_api.py -v
```

### Run Frontend Voice & Speech Tests
```bash
npx --prefix frontend tsx --tsconfig frontend/tsconfig.json --test frontend/tests/voice-transcription.test.ts
npx --prefix frontend tsx --tsconfig frontend/tsconfig.json --test frontend/tests/voice-chat-routing.test.ts
npx --prefix frontend tsx --tsconfig frontend/tsconfig.json --test frontend/tests/speech-tts.test.ts
```
