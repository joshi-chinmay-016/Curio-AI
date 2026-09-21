# Phase 1, Task 4D: Live Groq Integration Readiness Audit Report

**Date**: 2026-09-21  
**Author**: Backend Infrastructure Engineer (Pair Programming with AI Assistant)  
**Status**: Completed (Read-Only Audit)  
**Readiness Verdict**: **READY FOR CONTROLLED LIVE API TESTING**  
**Objective**: Comprehensive end-to-end readiness audit tracing live chat turn execution from FastAPI through `ChatService`, `GroqLLMProvider`, `CurioEngine`, and PostgreSQL persistence to ensure safety, reliability, secret hygiene, and contract invariance before executing the first live Groq request.

---

## 1. Executive Summary

With Phase 1, Task 4C completed and a real `GROQ_API_KEY` configured in `backend/.env`, Task 4D performs an exhaustive architectural and runtime readiness audit. The audit evaluated:
- The full request/response lifecycle.
- Live model specification (`llama-3.3-70b-versatile`).
- Structured JSON output parsing and Pydantic validation.
- Request timeout (30.0s) and bounded retries (2).
- Mock fallback guarantees under API failure modes (rate limits, timeouts, schema errors).
- Zero-exposure credential hygiene.
- Complete contract invariance: `AIContext → CurioEngine.process() → AIResult`.

### Key Conclusions:
- **Zero Critical Blockers**: The previously identified invalid model identifier (`openai/gpt-oss-120b`) has been resolved to `llama-3.3-70b-versatile`.
- **Zero High-Severity Risks**: All timeout, retry, and exception fallback paths are operational and tested.
- **Resilience**: Any failure of the live Groq API (network drops, rate limits, schema anomalies) immediately and gracefully degrades to `MockLLMProvider` without causing 500 errors or crashing worker processes.
- **Readiness Verdict**: The system is fully **READY** for a single controlled live chat request test.

---

## 2. End-to-End Chat Request Trace

```mermaid
sequenceDiagram
    autonumber
    actor Learner as Client / Frontend
    participant API as FastAPI Router (/messages)
    participant CS as ChatService
    participant DB as PostgreSQL (curio_db)
    participant CE as CurioEngine (LangGraph)
    participant Groq as GroqLLMProvider (Live API)
    participant Mock as MockLLMProvider (Fallback)

    Learner->>API: POST /api/v1/sessions/{session_id}/messages
    API->>CS: send_message(db, session_id, message_in)
    
    rect rgb(240, 245, 255)
        note over CS,DB: 1. State Loading & Message Persistence
        CS->>DB: SessionRepository.get(session_id)
        CS->>DB: MessageRepository.create_message("USER", content)
        CS->>DB: MessageRepository.get_recent_evaluations_by_session(limit=10)
        CS->>CS: Compile canonical AIContext (with hydrated evaluations & state)
    end

    rect rgb(255, 245, 240)
        note over CS,Groq: 2. CurioEngine Turn Processing (LangGraph)
        CS->>CE: process(context)
        
        %% Evaluation Node
        CE->>Groq: generate_structured(evaluation_prompt, TurnEvaluation)
        alt Live Call Success
            Groq-->>CE: TurnEvaluation (calibrated metrics)
        else Groq Fails (429, Timeout, Malformed JSON)
            Groq->>Mock: generate_structured(...)
            Mock-->>CE: TurnEvaluation (fallback metrics)
        end
        
        %% Decision Node
        CE->>CE: DecisionEngine.decide() [Deterministic Rules - Zero LLM]
        
        %% Response Node
        CE->>Groq: generate_text(student/teacher_prompt)
        alt Live Call Success
            Groq-->>CE: Socratic / Verification Question Text
        else Groq Fails
            Groq->>Mock: generate_text(...)
            Mock-->>CE: Socratic / Verification Question Text
        end
        
        %% State Updates Node
        CE->>CE: state_updates_node [Deterministic Streaks & Updates - Zero LLM]
        CE-->>CS: AIResult (evaluation, decision, response, state_updates)
    end

    rect rgb(240, 255, 240)
        note over CS,DB: 3. Persistence & API Response
        CS->>DB: MessageRepository.create_message("AI", response.content)
        CS->>DB: MessageRepository.create_evaluation(user_msg.id, evaluation)
        CS->>DB: SessionRepository.update_state(session_id, state_update)
        CS-->>API: ChatTurnResponse
    end

    API-->>Learner: 200 OK (ChatTurnResponse JSON)
```

### Detailed Trace Steps:
1. **Endpoint Entry**: [`backend/app/api/v1/messages.py:send_message()`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/api/v1/messages.py#L12-L24) receives payload `{"content": "...", "input_type": "TEXT"}` and `session_id`.
2. **Session Verification**: `SessionRepository.get(db, session_id)` ensures the session exists and has an initialized `SessionState`. Raises 404 if missing.
3. **User Message Persistence**: `MessageRepository.create_message(db, session_id, "USER", message_in)` saves the user message to `messages` table with an indexed UUID.
4. **Context Hydration**:
   - `list_by_session()` compiles conversation history into `List[ChatMessage]`.
   - `get_recent_evaluations_by_session(limit=10)` joins `messages` and `turn_evaluations`, fetches up to 10 latest evaluations, and returns them chronologically.
   - `_to_ai_turn_evaluation()` defensively sanitizes historical evaluations.
   - Active question and interrupted question are resolved by matching IDs against message history.
   - Builds strongly-typed `AIContext`.
5. **AI Engine Execution**: Calls `self.ai_engine.process(context)`:
   - **`run_evaluation`**: Calls `provider.generate_structured(prompt, TurnEvaluation)`:
     - Groq client calls `chat.completions.create(model="llama-3.3-70b-versatile", response_format={"type": "json_object"}, temperature=0.0, timeout=30.0)`.
     - Validates payload using `TurnEvaluation.model_validate_json(cleaned_content)`.
     - If any exception occurs (401, 404, 429, timeout, network error, schema error), caught in `except Exception:` and routed to `MockLLMProvider.generate_structured()`.
   - **`run_decision`**: Invokes `DecisionEngine.decide(context, evaluation)` — purely deterministic pedagogical logic (zero LLM calls).
   - **`run_response`**: Calls `provider.generate_text(prompt)`:
     - Invokes `chat.completions.create(model="llama-3.3-70b-versatile", temperature=0.7, timeout=30.0)`.
     - Output filtered by `_enforce_single_question()` (Student Mode) or `_enforce_single_verification_question()` (Teacher Mode).
     - If any exception occurs, caught and routed to `MockLLMProvider.generate_text()`.
   - **`run_state_updates`**: Evaluates streaks, mastery candidates, and question IDs deterministically.
   - Packages `AIResult`.
6. **Backend Persistence**:
   - Persists AI message via `MessageRepository.create_message("AI", ...)`.
   - Persists turn evaluation via `MessageRepository.create_evaluation(user_msg.id, ...)`.
   - Merges and commits state updates via `SessionRepository.update_state(...)`.
7. **Response**: Returns `ChatTurnResponse` matching OpenAPI schema.

---

## 3. Categorized Audit Findings

| ID | Category | Severity | Description | Impact | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **F-01** | Model Selection | **Resolved** | Hardcoded invalid model `"openai/gpt-oss-120b"` in previous versions. | Was 100% fatal for live calls. | **Fixed in Task 4C** (`llama-3.3-70b-versatile`). |
| **F-02** | Timeout Protection | **Resolved** | Missing client/request timeouts. | Sockets could block worker threads indefinitely. | **Fixed in Task 4C** (`timeout=30.0s`). |
| **F-03** | Retry Limits | **Resolved** | Missing explicit retry policies on Groq client. | Could trigger rapid rate-limit cascades. | **Fixed in Task 4C** (`max_retries=2`). |
| **F-04** | Prompt Persona | **Medium** | In `generate_text()`, the system message hardcodes: *"You are Curio, an inquisitive student learning from the user. Output exactly ONE primary learning question. Do not lecture."* When Teacher Mode runs, the user prompt instructs an expert teacher persona giving an explanation, which partially conflicts with the system prompt. | In Teacher Mode, the model might produce shorter explanations or be influenced by the conflicting student persona. (Non-blocking: user prompt still enforces teacher rules). | **Identified for Task 5 refinement**. |
| **F-05** | Case Sensitivity | **Medium** | `TurnEvaluation.recommended_strategy` is an Enum. If Groq outputs lowercase (e.g. `"probe_why"` instead of `"PROBE_WHY"`), Pydantic raises `ValidationError`. | Triggers fallback to `MockLLMProvider` on case discrepancy. | **Mitigated**: Fallback prevents crash; can add pre-validator. |
| **F-06** | Observability | **Low** | When live Groq calls fail and fall back to Mock, responses return normally with status 200 without a metadata header indicating fallback. | Developers must check logs to confirm whether a turn used Groq or Mock. | **Non-blocking**. |

---

## 4. Required Fixes Before Live API Request

### Pre-Flight Checklist:
1. **Critical / Blocker Fixes**: **None**. All core provider configurations and safety nets are in place.
2. **Configuration Readiness**:
   - `GROQ_API_KEY`: Present in `backend/.env` (verified masked `gsk_***`, 56 chars).
   - `GROQ_MODEL`: `llama-3.3-70b-versatile` (verified).
   - `GROQ_TIMEOUT_SECONDS`: `30.0` (verified).
   - `GROQ_MAX_RETRIES`: `2` (verified).
3. **Secret Hygiene**:
   - `backend/.env` is ignored by Git (`.gitignore:40`).
   - `git ls-files backend/.env` is empty.
   - `_sanitize_error()` redacts any keys before logging.
4. **Fallback Readiness**:
   - Unit tests confirm that simulated API errors, rate limits, timeouts, and malformed JSON cleanly fall back to `MockLLMProvider`.

---

## 5. Readiness Verdict

> [!NOTE]
> **VERDICT: READY FOR CONTROLLED LIVE API TESTING**
> 
> The Curio AI backend is structurally and operationally ready for an initial, single controlled live chat request using the Groq API. The fail-safe architecture ensures that even in the event of upstream API rate limits, latency timeouts, or authentication errors, the application will degrade gracefully to `MockLLMProvider` without disruption.

---

## 6. Verification and Test Execution Results

### 1. Focused Provider Tests
```bash
pytest backend/tests/ai/test_groq_provider.py -v
```
- Missing key fallback: **PASSED**
- Client initialization with mocked SDK: **PASSED**
- Custom configuration propagation: **PASSED**
- Runtime exception fallback & log redaction: **PASSED**
- Malformed JSON / schema validation fallback: **PASSED**
- AIResult contract invariance: **PASSED**  
*Result*: `6 passed in 1.51s`

### 2. Full Test Suite Validation
```bash
pytest -v
```
*Result*: `204 passed, 357 warnings in 20.27s` (100% pass rate across entire repository).
