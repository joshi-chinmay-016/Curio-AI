# Curio AI — Interactive Audio Learning Mode: Repository Audit & Implementation Plan

## Executive Summary

This audit establishes the baseline architecture, existing services, and technical requirements for implementing **Interactive Audio Learning Mode** in Curio AI.
Interactive Audio Learning is an audio-first, animated character learning experience connecting to the Curio AI learning engine, allowing users to:
1. **Student Mode**: Teach a curious student character by explaining concepts aloud. The student listens, takes notes, reacts with emotions, and asks probing follow-up questions. When the learner struggles, the female teacher character temporarily appears to intervene, explain the concept, and verify recovery before returning to the student.
2. **Professor Mode**: Conduct an interview simulation with a strict elderly professor character who asks sequential questions, evaluates spoken answers, handles skips/unanswered inputs, enforces a 3-strike consecutive-unanswered policy, and concludes with a comprehensive assessment summary.

---

## 1. Repository Audit Findings

### 1.1 Direct Component & Service Reuse
- **Audio Transcription (STT)**: `frontend/services/voiceService.ts` and `backend/app/api/v1/voice.py` (`POST /api/v1/voice/transcribe`) using `faster-whisper`.
- **Speech Synthesis (TTS)**: `frontend/services/speechService.ts` (`BrowserSpeechService` with `sanitizeTextForSpeech` markdown and citation sanitization).
- **Session & Message Pipeline**: `frontend/services/sessionRepository/ApiSessionRepository.ts` communicating with `backend/app/api/v1/sessions.py` and `backend/app/api/v1/messages.py`.
- **Document Management**: `frontend/services/documentService.ts` and `backend/app/api/v1/documents.py` (upload, process, list, get, delete).
- **Authentication**: `frontend/stores/authStore.ts` and `frontend/components/curio/auth/ProtectedRoute.tsx` with JWT tokens.
- **Design System**: Keycap styling (`KeycapButton.tsx`), high-contrast Curio palette (`#0F2B4A`, `#3B82F6`, `#F97316`, `#F4F6F8`), and transitions (`DiagonalSweepTransition.tsx`).

### 1.2 Components Requiring Extensions
- **Dashboard (`frontend/app/dashboard/page.tsx`)**: Add prominent **Interactive Audio Learning** feature card and top navigation link.
- **Session Store (`frontend/stores/sessionStore.ts`)**: Add audio learning state synchronization without mutating canonical learning state.
- **Route (`frontend/app/audio-learning/page.tsx`)**: Dedicated separate route for audio-first learning layout.

### 1.3 Professor Mode Backend Support
- The backend defines `LearningMode.EVALUATOR` alongside `STUDENT` and `TEACHER` in `backend/app/schemas/common.py` and `backend/app/ai/schemas.py`.
- Question selection is powered by `QuestionSelector` and `QuestionGenerator` in `backend/app/ai/`.
- For Professor Mode, question ordering (Easy-to-Hard, Hard-to-Easy, Mixed) and consecutive-unanswered handling will be orchestrated using Curio's turn evaluation and difficulty progression.

### 1.4 Voice Recording & Speech Playback Architecture
- **Recording**: Browser `MediaRecorder` captures audio into `audio/webm;codecs=opus` or fallback formats. Sent via multipart form upload to `POST /api/v1/voice/transcribe`. Transcribed text is displayed in an editable review field before submission.
- **Playback**: Web Speech API (`SpeechSynthesis`) speaks the AI's question/explanation aloud. Character animation states subscribe to speech lifecycle events (`onStart`, `onEnd`, `onError`).

### 1.5 Document Upload & Processing Workflow
- Document upload (`POST /api/v1/documents`) stores the file in `UPLOADED` state.
- Processing is triggered via `POST /api/v1/documents/{id}/process`, transitioning from `UPLOADED` -> `PROCESSING` -> `PROCESSED`.
- Sessions only bind documents in the `PROCESSED` state.

### 1.6 Session-Document Association & RAG
- `POST /api/v1/sessions` accepts `document_id` and `source_type: "DOCUMENT"`.
- `ChatService` loads the document context via `RetrievalService`, passing grounded chunks to `CurioEngine` for evidence-based questions and assessment.

### 1.7 Assessment Contracts & Metrics
- `ChatTurnResponse` provides `evaluation` (`correctness`, `clarity`, `completeness`, `depth`, `relevance`, `stuck_probability`, `misconceptions`, `missing_concepts`, `mastered_concepts`, `knowledge_gap`, `recommended_difficulty`) and `decision` (`next_mode`, `strategy`, `confidence`, `reason`, `active_concept`, `should_restore_interrupted_question`).
- `SessionReportResponse` provides final score, mastery level, strengths, priority learning gaps, misconceptions, and personalized roadmap.

### 1.8 Character Artwork Assets
- Character artwork has been cleanly extracted from the user's approved reference image and placed in `frontend/public/characters/`:
  - `student.png` (Cute young student with headphones, blue shirt, backpack)
  - `teacher.png` & `teacher_cutout.png` (Cute female teacher with curly hair, round glasses, blouse, skirt, notebook)
  - `professor.png` (Strict elderly professor with white hair, moustache, glasses, dark formal suit, folded arms)

---

## 2. Phase-by-Phase Implementation Plan

- **Phase 1**: Dashboard Integration & Dedicated Route (`/audio-learning`)
- **Phase 2**: Reusable Character Stage Component with CSS micro-animations & Typed Animation States
- **Phase 3**: Audio Learning Session Setup Flow (Mode, Topic, Document, Difficulty Order)
- **Phase 4**: Shared Audio Conversation Loop & Turn-based Voice Controls
- **Phase 5**: Student Mode Audio Experience & Emotion Reactions
- **Phase 6**: Automatic Teacher Intervention & Recovery Verification Transition
- **Phase 7**: Professor Mode Spoken Interview, Consecutive-Unanswered Policy (3 strikes), & Session Summary
- **Phase 8**: Document-Grounded Audio Learning Integration
- **Phase 9**: Accessibility, Error Fallbacks, & Cleanup
- **Phase 10**: Automated Testing Suite & Validation
