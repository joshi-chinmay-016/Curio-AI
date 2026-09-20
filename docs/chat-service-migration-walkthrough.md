# ChatService Migration & Defensive Fixes Walkthrough

This document provides the complete technical walkthrough for the Stage 1 migration of [`ChatService`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py) to [`CurioEngine.process()`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/engine.py#L37) and the subsequent runtime defensive fixes.

---

## 1. Problem & Context

Before this migration, the Curio AI backend invoked the legacy [`AIOrchestrator`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/orchestrator.py) inside [`ChatService.send_message()`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py). This legacy path:
* Compiled an incomplete, flat context omitting core state: confidence, unresolved misconceptions, mastered concepts, and streaks.
* Bypassed the compiled LangGraph state machine.
* Relied on unstructured metadata dictionaries (`metadata["evaluation"]`).
* Introduced runtime risks: UUID-versus-string ID hydration mismatches and unhandled lowercase or missing `input_type` values.

---

## 2. Changes Implemented

### 2.1 Direct CurioEngine Invocation
* **File**: [`backend/app/services/chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py)
* Added `ai_engine: Optional[CurioEngine] = None` in `__init__()`, defaulting to `CurioEngine()`.
* Replaced `self.orchestrator.process_turn(...)` exclusively with:
  ```python
  ai_result: AIResult = self.ai_engine.process(context)
  ```
* Retained `self.orchestrator` and `self.ai_provider` for backward compatibility without invoking them.

### 2.2 Canonical AIContext Compilation
* Replaced the flat context with the nested [`AIContext`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L277):
  * **[`SessionInfo`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L240)**: `session_id`, `topic`, `source_mode`.
  * **[`ConversationContext`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L260)**: Messages with `Role.ASSISTANT if m.sender == "AI" else Role.USER`.
  * **[`LearningContext`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L269)**: `mastered_concepts` and `unresolved_misconceptions` from persisted database state.
  * **[`SessionState`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L248)**: Ingests `understanding_confidence`, `unresolved_misconceptions`, `mastered_concepts`, `consecutive_successes`, `consecutive_failures`, `active_concept`, `current_mode`, and `difficulty`.

### 2.3 Defensive Question Hydration (Fix 1)
* Hydrates [`CurrentQuestion`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L125) from `current_question_id` and `interrupted_question_id`.
* Matches messages using type-agnostic string comparison:
  ```python
  matching_q = next(
      (m for m in db_history if getattr(m, "id", None) is not None and str(m.id) == target_qid_str),
      None
  )
  ```
* Safely defaults to `None` if IDs are missing or unfound, without creating synthetic records.

### 2.4 InputType Normalization (Fix 2)
* Added `_normalize_input_type()` and `_normalize_common_input_type()` helpers.
* Preserves existing valid enum instances.
* Uppercases strings (`"text"` -> `"TEXT"`, `"voice"` -> `"VOICE"`).
* Gracefully falls back to `TEXT` for missing, empty, or unexpected values.

### 2.5 Null-Safe State Updates Merging
* Because [`SessionRepository.update_state()`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/repositories/session_repository.py#L53) requires all fields and unconditionally overwrites the database row, any `None` attribute in `StateUpdates` strictly preserves the prior database value.

### 2.6 Resilient API Response Mapping
* Added `_to_message_response()` helper converting database message models (`id` column) into [`MessageResponse`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/message.py#L11) (`message_id` attribute), guaranteeing API response format preservation.

---

## 3. Test Suite Verification

### 3.1 Focused Unit Tests (11 Tests)
File: [`backend/tests/services/test_chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/services/test_chat_service.py)

1. `test_send_message_invokes_curio_engine_with_canonical_context`: PASSED
2. `test_send_message_merges_partial_state_updates`: PASSED
3. `test_send_message_explicit_enum_conversions`: PASSED
4. `test_send_message_preserves_api_response_format`: PASSED
5. `test_send_message_safe_question_hydration_when_missing`: PASSED
6. `test_send_message_raises_when_session_not_found`: PASSED
7. `test_get_messages_mapping`: PASSED
8. `test_question_hydration_uuid_vs_string_id_comparison`: PASSED
9. `test_input_type_normalization_lowercase`: PASSED
10. `test_input_type_normalization_missing`: PASSED
11. `test_question_hydration_missing_question_ids`: PASSED

### 3.2 Full Backend Test Suite
Executed all backend tests with Pytest:
```bash
& 'backend/.venv/Scripts/python.exe' -m pytest
```
```text
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-8.0.0, pluggy-1.6.0
rootdir: C:\Users\Vishal S Naik\MyProjects\Curio-AI
plugins: anyio-4.15.1
collected 37 items

backend\tests\ai\test_decision_engine.py .........                       [ 24%]
backend\tests\ai\test_engine.py .....                                    [ 37%]
backend\tests\ai\test_schemas.py ...........                             [ 67%]
backend\tests\api\test_health.py .                                       [ 70%]
backend\tests\services\test_chat_service.py ...........                  [100%]

======================= 37 passed, 60 warnings in 2.34s =======================
```

---

## 4. Documentation References

* **[Walkthrough Artifact](file:///C:/Users/Vishal%20S%20Naik/.gemini/antigravity-ide/brain/6a2fe1a1-c25e-4215-b146-9dabe3153ceb/walkthrough.md)**: Updated walkthrough artifact.
* **[`docs/chat-service-runtime-integration-audit.md`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docs/chat-service-runtime-integration-audit.md)**: Runtime integration audit.
* **[`docs/chat-service-curio-engine-migration-report.md`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docs/chat-service-curio-engine-migration-report.md)**: Stage 1 migration specification and execution report.
