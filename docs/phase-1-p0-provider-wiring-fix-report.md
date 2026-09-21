# Curio AI — Phase 1: P0 Provider Wiring Resolution Report

**Author:** Senior Backend Architect  
**Project:** Curio AI (Feynman Role-Reversal Learning Platform)  
**Date:** September 21, 2026  
**Status:** Resolved & Verified  
**Repository:** `joshi-chinmay-016/Curio-AI`  
**Current Branch:** `backend`  
**Architectural Contract:** `AIContext` $\rightarrow$ `CurioEngine.process()` $\rightarrow$ `AIResult`

---

## 1. Executive Summary

During the Phase 1 AI–Backend Integration Compatibility Audit ([`docs/phase-1-ai-backend-integration-audit-report.md`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docs/phase-1-ai-backend-integration-audit-report.md)), a critical Priority 0 (P0) defect was identified:
- [`ChatService`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py) instantiated `self.ai_provider = GroqLLMProvider()` but did not pass it to [`CurioEngine`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/engine.py).
- Since `CurioEngine.__init__` defaults to `MockLLMProvider()`, default instantiations of `ChatService` (including the active FastAPI router in [`backend/app/api/v1/messages.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/api/v1/messages.py#L10)) ran in mock inference mode rather than real Groq inference in production.
- Additionally, an unused instance of legacy [`AIOrchestrator`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/orchestrator.py) was retained in `ChatService.__init__`.

This task successfully resolved the P0 wiring issue, removed the legacy orchestrator, and verified that all 136 non-database unit tests pass with zero regressions.

---

## 2. Root Cause Analysis

In [`backend/app/services/chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L40-L48), the constructor previously read:

```python
class ChatService:
    def __init__(self, ai_engine: Optional[CurioEngine] = None):
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()
        # Retain legacy provider and orchestrator for backward compatibility until migration is verified
        self.ai_provider = GroqLLMProvider()
        self.orchestrator = AIOrchestrator(self.ai_provider)
        # Canonical AI Engine
        self.ai_engine = ai_engine or CurioEngine()
```

And in [`backend/app/ai/engine.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/engine.py#L34-L36):

```python
class CurioEngine:
    def __init__(self, provider: Optional[BaseAIProvider] = None, graph: Any = None):
        self.provider = provider or MockLLMProvider()
        self._graph = graph or build_curio_graph(self.provider)
```

Because `CurioEngine()` was called without arguments when `ai_engine` was omitted, `self.provider` fell back to `MockLLMProvider()`. `self.ai_provider` remained orphaned, and `self.orchestrator` was never called in any active execution path.

---

## 3. Implemented Changes

### A. [`backend/app/services/chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py)

1. **Imports Refined**:
   - Removed: `from backend.app.ai.orchestrator import AIOrchestrator`
   - Added: `from backend.app.ai.providers.base import BaseAIProvider`

2. **Constructor Updated**:
   - Added optional `ai_provider: Optional[BaseAIProvider] = None` parameter.
   - Instantiated `self.ai_provider = ai_provider or GroqLLMProvider()`.
   - Wired `self.ai_engine = ai_engine or CurioEngine(provider=self.ai_provider)`.
   - Removed `self.orchestrator = AIOrchestrator(self.ai_provider)`.

```python
class ChatService:
    def __init__(
        self,
        ai_engine: Optional[CurioEngine] = None,
        ai_provider: Optional[BaseAIProvider] = None,
    ):
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()
        self.ai_provider = ai_provider or GroqLLMProvider()
        # Canonical AI Engine: ensure configured provider is passed if engine is not supplied
        self.ai_engine = ai_engine or CurioEngine(provider=self.ai_provider)
```

### B. [`backend/tests/services/test_chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/services/test_chat_service.py)

Added 4 dedicated unit tests:
1. `test_chat_service_default_initialization_injects_groq_provider`: Asserts that `ChatService()` initializes `CurioEngine` with `GroqLLMProvider` as its provider.
2. `test_chat_service_explicit_engine_preserved`: Asserts that passing an explicit `ai_engine` preserves the instance without modification.
3. `test_chat_service_custom_provider_injection`: Asserts that passing an explicit `ai_provider` correctly propagates to `CurioEngine`.
4. `test_legacy_orchestrator_not_present_or_invoked`: Asserts that `hasattr(service, "orchestrator")` is `False` and that `AIOrchestrator` is never invoked during `send_message()`.

---

## 4. Verification & Test Results

### 1. Focused ChatService Suite
```bash
pytest backend/tests/services/test_chat_service.py -v
```
**Results:** 15/15 tests passed in 1.76s (11 existing + 4 new).

```text
backend/tests/services/test_chat_service.py::test_send_message_invokes_curio_engine_with_canonical_context PASSED
backend/tests/services/test_chat_service.py::test_send_message_merges_partial_state_updates PASSED
backend/tests/services/test_chat_service.py::test_send_message_explicit_enum_conversions PASSED
backend/tests/services/test_chat_service.py::test_send_message_preserves_api_response_format PASSED
backend/tests/services/test_chat_service.py::test_send_message_safe_question_hydration_when_missing PASSED
backend/tests/services/test_chat_service.py::test_send_message_raises_when_session_not_found PASSED
backend/tests/services/test_chat_service.py::test_get_messages_mapping PASSED
backend/tests/services/test_chat_service.py::test_question_hydration_uuid_vs_string_id_comparison PASSED
backend/tests/services/test_chat_service.py::test_input_type_normalization_lowercase PASSED
backend/tests/services/test_chat_service.py::test_input_type_normalization_missing PASSED
backend/tests/services/test_chat_service.py::test_question_hydration_missing_question_ids PASSED
backend/tests/services/test_chat_service.py::test_chat_service_default_initialization_injects_groq_provider PASSED
backend/tests/services/test_chat_service.py::test_chat_service_explicit_engine_preserved PASSED
backend/tests/services/test_chat_service.py::test_chat_service_custom_provider_injection PASSED
backend/tests/services/test_chat_service.py::test_legacy_orchestrator_not_present_or_invoked PASSED
```

### 2. Full Non-Database Test Suite
```bash
pytest -m "not db_integration"
```
**Results:** 136/136 tests passed, 43 deselected (requiring live Postgres DB) in 3.51s.
- `test_decision_engine.py`: 9 passed
- `test_engine.py`: 14 passed
- `test_phase1_student_mode.py`: 33 passed
- `test_phase2_teacher_mode.py`: 20 passed
- `test_phase3_contracts.py`: 7 passed
- `test_phase3_evaluator.py`: 5 passed
- `test_phase3_evidence.py`: 6 passed
- `test_phase3_scoring.py`: 6 passed
- `test_schemas.py`: 11 passed
- `test_database_safety.py`: 9 passed
- `test_health.py`: 1 passed
- `test_chat_service.py`: 15 passed

---

## 5. Backward Compatibility & Safety Guarantees

- **No Breaking API Changes**: Existing code and tests using `ChatService(ai_engine=...)` remain fully functional.
- **Provider Fallback Safety**: [`GroqLLMProvider`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/providers/groq_provider.py#L30-L40) checks for `GROQ_API_KEY`. If absent, it logs a warning and falls back to `MockLLMProvider`, ensuring local offline environments and tests run without network calls or crashes.
- **Zero Schema or DB Changes**: No database tables, Alembic migrations, or model schemas were touched in this task.
- **Strict Boundary Integrity**: No AI prompts, LangGraph nodes, or pedagogical decision heuristics were modified.

---

## 6. Remaining Phase 1 Tasks

With P0 resolved, the next tasks for Phase 1 backend completion are:
1. **P1 — Teacher Mode State Persistence**: Persist `teacher_attempt_count` and `teacher_intervention` in `SessionState` so that Teacher Mode can advance through pedagogical attempts (Attempt 1 $\rightarrow$ 2 $\rightarrow$ 3).
2. **P1 — Learning Context Evaluations Hydration**: Query recent turn evaluations in `ChatService.send_message()` to populate `learning_context.recent_evaluations` so `DecisionEngine` Trigger C can detect repeated knowledge gap failures.
