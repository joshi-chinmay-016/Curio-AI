# Phase 1, Task 4E: Controlled Live Groq API Integration Test Report

**Date**: 2026-09-21  
**Author**: Backend Infrastructure Engineer (Pair Programming with AI Assistant)  
**Status**: Executed & Verified  
**Execution Outcome**: **SUCCESSFUL WITH GRACEFUL MOCK FALLBACK (MODEL AVAILABILITY NOTED)**  
**Objective**: Execute exactly ONE controlled live chat request using the configured Groq API through the actual FastAPI endpoint, capturing safe metadata, verifying database persistence in PostgreSQL, ensuring secret safety, and confirming AI contract invariance.

---

## 1. Executive Summary

Under Phase 1, Task 4E, a single controlled live chat request was executed against the FastAPI backend endpoint `POST /api/v1/sessions/{session_id}/messages` with active Groq provider credentials (`backend/.env`).

### Key Highlights:
1. **End-to-End Execution**: A dedicated isolated test session was created (`0119264b-71da-4aca-a77c-75d748546f57`), and a valid textual learning turn was submitted.
2. **Live Groq API Invocation**: The live Groq API was called at `https://api.groq.com/openai/v1/chat/completions`.
3. **Resilience & Fallback**: The configured model `llama-3.3-70b-versatile` returned HTTP 404 from Groq (`The model llama-3.3-70b-versatile does not exist or you do not have access to it.`). The `GroqLLMProvider` caught the exception, sanitized credentials, and immediately routed execution to `MockLLMProvider` without raising any uncaught exceptions or 500 errors.
4. **Zero-Crash Delivery**: The FastAPI endpoint responded with HTTP 200 OK and a fully schema-valid `ChatTurnResponse`.
5. **Database Persistence Verified**: Direct PostgreSQL inspection confirmed that the USER message, AI response message, `TurnEvaluation` record, and `SessionState` updates were all successfully committed to the database.
6. **Secret Hygiene**: Zero API keys or sensitive authorization tokens were leaked in logs, stdout, or reports.

---

## 2. Pre-Flight Verification

| Configuration / Resource | Value / Status | Verification Method |
| :--- | :--- | :--- |
| **`GROQ_API_KEY`** | **PRESENT** (len=56, masked: `gsk_...dISk`) | Environment check via `backend/.env` |
| **`GROQ_MODEL`** | `llama-3.3-70b-versatile` | `backend/app/core/config.py` & `.env` |
| **`GROQ_TIMEOUT_SECONDS`** | `30.0` | Verified via `Settings` |
| **`GROQ_MAX_RETRIES`** | `2` | Verified via `Settings` |
| **PostgreSQL Database** | `postgresql://postgres:***@localhost:5433/curio_db` | Live connection test (`SELECT 1` -> 1) |
| **Alembic Revision** | `84274ca763eb` | Verified matches latest migration |
| **Database Tables** | `alembic_version`, `documents`, `messages`, `session_reports`, `session_states`, `sessions`, `turn_evaluations`, `users` | All 8 required tables present |

---

## 3. Controlled Live Request Execution

### 3.1 Request Details
- **Test Session Created**: `0119264b-71da-4aca-a77c-75d748546f57`  
  - *Topic*: `"Phase 1 Task 4E: Live Groq Verification - Photosynthesis"`
  - *Initial Mode*: `STUDENT`
  - *Source Type*: `GENERAL`
- **Target Endpoint**: `POST /api/v1/sessions/0119264b-71da-4aca-a77c-75d748546f57/messages`
- **User Message Payload**:
  ```json
  {
    "content": "Photosynthesis is the biological process where plants convert sunlight, water, and carbon dioxide into oxygen and glucose.",
    "input_type": "TEXT"
  }
  ```

### 3.2 Safe Execution Metadata
- **HTTP Status Code**: `200 OK`
- **Total Request Latency**: `0.560s`
- **Response Schema Validity**: **PASSED** (Validated against `ChatTurnResponse`)
- **Active Provider**: `GroqLLMProvider` (dispatched to `https://api.groq.com/openai/v1/chat/completions`)
- **Fallback Status**: **ENGAGED** (Graceful fallback to `MockLLMProvider` due to upstream model availability)
- **AI Response Content**: `"Why does that behavior occur in this scenario?"`
- **Evaluation Output**:
  - `correctness`: `0.80`
  - `clarity`: `0.90`
  - `completeness`: `0.80`
  - `depth`: `0.70`
  - `stuck_probability`: `0.00`
  - `recommended_strategy`: `PROBE_WHY`
  - `mastered_concepts`: `["Core concept"]`
- **Pedagogical Decision**:
  - `next_mode`: `STUDENT`
  - `strategy`: `PROBE_WHY`
  - `difficulty`: `2`
- **Updated State**:
  - `current_mode`: `STUDENT`
  - `confidence`: `0.08`
  - `difficulty`: `2`

---

## 4. Key Discovery: Groq Model Catalog Availability

When the live API call was dispatched to Groq:
```text
2026-09-21 22:15:30,789 [INFO] httpx: HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 404 Not Found"
2026-09-21 22:15:30,792 [WARNING] curio.ai.providers.groq: Groq structured generation failed (NotFoundError: Error code: 404 - {'error': {'message': 'The model `llama-3.3-70b-versatile` does not exist or you do not have access to it.', 'type': 'invalid_request_error', 'code': 'model_not_found'}}); falling back to mock.
```

### Direct Catalog Inspection (`client.models.list()`):
A read-only query to the Groq Models API revealed the exact models active for this API key:
- `openai/gpt-oss-120b` (owned_by: OpenAI, active: True)
- `openai/gpt-oss-20b` (owned_by: OpenAI, active: True)
- `qwen/qwen3.8-27b` (owned_by: Alibaba Cloud, active: True)
- `groq/compound` (owned_by: Groq, active: True)
- `groq/compound-mini` (owned_by: Groq, active: True)
- `allam-2-7b` (owned_by: SDAIA, active: True)
- `canopylabs/orpheus-v1-english`
- `canopylabs/orpheus-arabic-saudi`
- `whisper-large-v3-turbo`
- `whisper-large-v3`
- `meta-llama/llama-prompt-guard-2-22m`
- `meta-llama/llama-prompt-guard-2-86m`
- `openai/gpt-oss-safeguard-20b`

> [!NOTE]
> **Architectural Insight**:
> In earlier tasks, Chinmay had originally hardcoded `model = "openai/gpt-oss-120b"`. Our model catalog query reveals that `openai/gpt-oss-120b` is indeed the primary active chat model available on this Groq account. `llama-3.3-70b-versatile` is not enabled for this specific Groq key/tier. Because `Settings` and `GroqLLMProvider` dynamically read `GROQ_MODEL` from `backend/.env`, switching `GROQ_MODEL=openai/gpt-oss-120b` in `backend/.env` can enable live generation whenever desired.

---

## 5. PostgreSQL Database Persistence Verification

Direct database verification was performed via SQLAlchemy against `curio_db`:

```sql
SELECT sender, content, id FROM messages WHERE session_id = '0119264b-71da-4aca-a77c-75d748546f57';
```
- **USER Message**: `"Photosynthesis is the biological process where plants convert sunlight, water, and carbon dioxide into oxygen and glucose."`  
  - UUID: `69b6ccb6-d7b1-4e27-bb8e-8150cc0be91c`
- **AI Message**: `"Why does that behavior occur in this scenario?"`  
  - UUID: `5b3ba629-cf06-4850-9885-7ed4d41346c3`

```sql
SELECT message_id, correctness, clarity, recommended_strategy FROM turn_evaluations WHERE message_id = '69b6ccb6-d7b1-4e27-bb8e-8150cc0be91c';
```
- **Turn Evaluation**:
  - `message_id`: `69b6ccb6-d7b1-4e27-bb8e-8150cc0be91c` (Properly linked to USER message)
  - `correctness`: `0.80`
  - `clarity`: `0.90`
  - `recommended_strategy`: `"PROBE_WHY"`

```sql
SELECT current_mode, difficulty, confidence FROM session_states WHERE session_id = '0119264b-71da-4aca-a77c-75d748546f57';
```
- **Session State**:
  - `current_mode`: `STUDENT`
  - `difficulty`: `2`
  - `confidence`: `0.08`

---

## 6. Contract Invariance & Safety Verification

1. **`AIContext → CurioEngine → AIResult`**:
   - The canonical contracts remained strictly invariant.
   - All input types, turn evaluations, and learning decisions adhered to the Pydantic schemas without modification.
2. **Zero Leaks**:
   - `_sanitize_error()` in `GroqLLMProvider` ensured that error strings logged during 404 or other network failures did not expose the API key or raw tokens.
3. **Graceful Fallback Validation**:
   - The test verified the ultimate resilience requirement: an upstream model or network error never propagates as a 500 Internal Server Error to the learner.

---

## 7. Regression Test Results

### 1. Groq Provider Reliability Tests
```bash
pytest backend/tests/ai/test_groq_provider.py -v
```
- `test_groq_provider_missing_key_operates_in_mock_mode`: **PASSED**
- `test_groq_provider_client_initialization`: **PASSED**
- `test_groq_provider_custom_configuration`: **PASSED**
- `test_groq_provider_runtime_exception_falls_back_to_mock`: **PASSED**
- `test_groq_provider_malformed_json_fallback`: **PASSED**
- `test_curio_engine_contract_invariance_with_groq_provider`: **PASSED**  
*Result*: **6 passed in 1.21s**

### 2. Teacher Mode Integration Tests
```bash
pytest backend/tests/integration/test_teacher_mode_persistence.py -v
```
*Result*: **13 passed in 3.75s**

### 3. Full Repository Test Suite Validation
```bash
pytest -v
```
*Result*: **204 passed, 357 warnings in 9.35s (100% pass rate, 0 regressions)**

