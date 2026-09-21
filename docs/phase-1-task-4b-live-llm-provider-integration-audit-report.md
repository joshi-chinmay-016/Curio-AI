# Phase 1, Task 4B: Live LLM Provider Integration Audit Report

**Date**: 2026-09-21  
**Author**: Backend Infrastructure Engineer (Pair Programming with AI Assistant)  
**Status**: Completed (Read-Only Audit)  
**Objective**: Comprehensive technical audit of the live LLM provider integration (`GroqLLMProvider`), environment variable loading, mock fallback resilience, timeout/retry handling, security and credential hygiene, and contract invariance (`AIContext → CurioEngine → AIResult`).

---

## 1. Executive Summary

As part of Phase 1 milestone stabilization, Task 4B audits the real LLM inference layer implemented in [`backend/app/ai/providers/groq_provider.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/providers/groq_provider.py). 

### Key Audit Findings:
1. **Architecture & Contract Invariance**: The architecture cleanly decouples the service layer from the LLM provider. `ChatService` injects `GroqLLMProvider` into `CurioEngine`, which passes it down to LangGraph nodes (`evaluation_node`, `response_node`). The `AIContext → CurioEngine.process() → AIResult` contract is 100% preserved.
2. **Mock Fallback Safety**: The provider includes an automatic, multi-tier fallback to [`MockLLMProvider`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/providers/mock_provider.py) if `GROQ_API_KEY` is missing, the `groq` SDK is uninstalled, initialization fails, or runtime inference errors occur.
3. **Critical Finding — Invalid Model Name**: Both `generate_structured()` and `generate_text()` currently hardcode `model="openai/gpt-oss-120b"`. This is **not** a valid model identifier on Groq's official API (valid models include `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`). Any call with a live key will encounter a 404/NotFound error and silently degrade to the mock provider.
4. **Missing Timeout & Retry Configuration**: No request timeout or retry policies are currently configured on the `Groq` client or in `chat.completions.create()`, posing thread blocking risks during network latency spikes.
5. **Security Hygiene**: `.env` and `backend/.env` are properly ignored in `.gitignore`. No live API keys are logged, printed, or committed to git history.

---

## 2. Current Provider Flow

```mermaid
flowchart TD
    CS[ChatService.__init__] -->|Defaults to| GP[GroqLLMProvider]
    CS -->|Injects into| CE[CurioEngine(provider=GroqLLMProvider)]
    CE -->|Compiles| LG[build_curio_graph(provider)]
    
    subgraph Execution [Turn Execution: ChatService.send_message]
        AIContext[AIContext hydrated from PostgreSQL] --> CE_Proc[CurioEngine.process]
        CE_Proc --> LG_Inv[LangGraph Workflow Invoke]
        
        LG_Inv --> EN[run_evaluation node]
        EN -->|evaluator.evaluate_turn| GP_Struct[provider.generate_structured]
        
        LG_Inv --> DN[run_decision node]
        DN -->|Deterministic Heuristics| DE[DecisionEngine - Zero LLM]
        
        LG_Inv --> RN[run_response node]
        RN -->|student/teacher handler| GP_Text[provider.generate_text]
        
        LG_Inv --> UN[run_state_updates node]
        UN -->|Deterministic Streaks & Updates| SU[StateUpdates - Zero LLM]
        
        SU --> AIResult[AIResult]
    end
```

### Flow Breakdown:
1. **Instantiation**: `ChatService()` defaults to `self.ai_provider = GroqLLMProvider()` and `self.ai_engine = CurioEngine(provider=self.ai_provider)`.
2. **Dependency Injection**: `CurioEngine` injects `self.provider` into the LangGraph state dictionary (`{"context": context, "provider": self.provider}`).
3. **Structured Generation**: `AIEvaluator.evaluate_turn()` invokes `provider.generate_structured(prompt, TurnEvaluation)`:
   - Serializes `TurnEvaluation.model_json_schema()`.
   - Enforces JSON output with system instructions.
   - Validates the returned JSON payload against `TurnEvaluation`.
4. **Text Generation**: `StudentModeHandler` and `TeacherModeHandler` invoke `provider.generate_text(prompt)` to generate targeted Socratic questions or teacher gap explanations.
5. **Deterministic Boundaries**: Neither `DecisionEngine` nor `StateUpdates` call any LLM; all pedagogical heuristics and streak tracking are 100% deterministic.

---

## 3. Environment Configuration Findings

### Key Resolution Mechanism
In [`backend/app/ai/providers/groq_provider.py:25-26`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/providers/groq_provider.py#L25-L26):
```python
self.api_key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", "")
```
- Resolution Order: Explicit argument $\rightarrow$ `os.environ["GROQ_API_KEY"]` $\rightarrow$ `settings.GROQ_API_KEY` $\rightarrow$ `""`.
- `Settings` in [`backend/app/core/config.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/core/config.py#L31-L43) uses `pydantic_settings.BaseSettings` reading from `.env` and `backend/.env`.

### Current Environment Status:
| Target | File Path | Status |
| :--- | :--- | :--- |
| **Root Template** | `.env.example` | Present: `GROQ_API_KEY=` |
| **Backend Environment** | `backend/.env` | Present: `GROQ_API_KEY=` (empty string) |
| **Root Environment** | `.env` | Not present (expected) |
| **Groq SDK** | `groq==0.4.2` | Installed in virtual environment |

When `GROQ_API_KEY` is not set or is empty string, `if self.api_key:` evaluates to `False`. The client remains uninitialized (`self.client = None`), cleanly triggering mock fallback.

### Configuration Gaps:
- **Missing `GROQ_MODEL` setting**: No configuration setting exists in `Settings` for model selection.
- **Missing `GROQ_TIMEOUT_SECONDS`**: No timeout setting exists in `Settings`.
- **Missing `GROQ_MAX_RETRIES`**: No retry configuration exists in `Settings`.

---

## 4. Mock Fallback Behavior

`GroqLLMProvider` initializes `self.mock_fallback = MockLLMProvider()` as a safety fallback.

### Fallback Scenarios & Behavior:
| Trigger Event | Detection Logic | Resulting Action | Error Level |
| :--- | :--- | :--- | :--- |
| **Missing API Key** | `not self.api_key` | `self.client = None` | `logger.info("No GROQ_API_KEY found; operating in mock fallback mode.")` |
| **Missing SDK** | `ImportError` on `import groq` | `self.client = None` | `logger.warning("Groq package not installed; falling back to MockLLMProvider.")` |
| **Init Exception** | `Exception` on `Groq(api_key=...)` | `self.client = None` | `logger.warning("Failed to initialize Groq client (%s)...", type(e).__name__)` |
| **Runtime API Error** | HTTP 401, 404, 429, 500, Network timeout | Caught in `try...except Exception as e` | `logger.warning("Groq ... generation failed (%s: %s); falling back to mock.")` |
| **Malformed JSON** | Invalid JSON syntax from LLM | Caught in `try...except Exception as e` | Falls back to `MockLLMProvider.generate_structured()` |
| **Schema Validation Error** | Pydantic `ValidationError` | Caught in `try...except Exception as e` | Falls back to `MockLLMProvider.generate_structured()` |

### Architectural Assessment:
- **Resilience**: The system never crashes or returns a 500 Internal Server Error to the frontend due to LLM provider failures.
- **Silent Degradation Risk**: Because runtime exceptions are caught by a catch-all `except Exception:`, live API failures (e.g. invalid model or bad credentials) will seamlessly fall back to mock data without failing requests. Developers might assume they are running against live Groq unless they check server logs.

---

## 5. Error Handling and Timeout Risks

### 1. Hardcoded Non-Existent Model (Critical)
Lines 55 and 76 of `groq_provider.py`:
```python
response = self.client.chat.completions.create(
    model="openai/gpt-oss-120b",  # <-- INVALID GROQ MODEL
    ...
)
```
- **Risk**: Groq's official API does not host a model named `openai/gpt-oss-120b`.
- **Consequence**: Even when a valid `GROQ_API_KEY` is provided, every live call will fail with a 404 `model_not_found` error and immediately fall back to `MockLLMProvider`.
- **Recommended Fix**: Change default model to a supported Groq model:
  - Default: `llama-3.3-70b-versatile` (fast, high reasoning quality, supports structured outputs)
  - Alternative / Fast: `llama-3.1-8b-instant`

### 2. Missing Request Timeouts
- **Risk**: `Groq(api_key=self.api_key)` does not set a client timeout, nor does `chat.completions.create(...)`.
- **Consequence**: In production, if Groq's API experiences latency or TCP socket hangs, FastAPI worker threads could block indefinitely, degrading backend throughput.
- **Recommended Fix**: Set a default timeout of 30 seconds on the client (`Groq(api_key=..., timeout=30.0)`).

### 3. Rate Limit (429) & Retry Policies
- **Risk**: Groq imposes rate limits on requests per minute (RPM) and tokens per minute (TPM).
- **Consequence**: Rapid interactions without a bounded retry strategy could fail quickly.
- **Recommended Fix**: Configure `max_retries=2` in the `Groq` client, and ensure 429 status codes trigger clean fallback.

### 4. JSON Fence Cleaning
- `_clean_json_text()` handles markdown code blocks:
  ```python
  if text.startswith("```json"):
      text = text[7:]
  ```
- If the model produces leading conversation or trailing explanations outside of markdown fences, `model_validate_json()` will fail and trigger mock fallback. Adding temperature=0.0 and `response_format={"type": "json_object"}` mitigates this effectively.

---

## 6. Security Findings

| Security Check | Finding | Status |
| :--- | :--- | :--- |
| **API Key Storage** | Stored in `.env` and `backend/.env`, never hardcoded in source. | Pass |
| **Git Exclusion** | `backend/.env` is ignored by `.gitignore` (line 40: `backend/.env`). Verified with `git check-ignore`. | Pass |
| **Git Commit History** | Git log verified: no live Groq API keys (`gsk_*`) have ever been committed (only dummy docs). | Pass |
| **Key Logging** | `self.api_key` is never logged, printed, or exposed in error messages. | Pass |
| **Prompt Logging** | Prompts and user messages are not logged at `INFO` level. Only session IDs, modes, and topics are logged. | Pass |
| **Error Log Sanitization** | `logger.warning(... str(e))` logs exception messages. Standard Groq SDK exceptions do not output authorization headers. | Pass |

---

## 7. Recommended Implementation Steps (Phase 1, Task 4C)

1. **Update `backend/app/core/config.py`**:
   - Add `GROQ_MODEL: str = "llama-3.3-70b-versatile"`.
   - Add `GROQ_TIMEOUT_SECONDS: float = 30.0`.
   - Add `GROQ_MAX_RETRIES: int = 2`.
2. **Update `backend/app/ai/providers/groq_provider.py`**:
   - Accept `model`, `timeout`, and `max_retries` parameters with settings fallbacks.
   - Initialize `Groq(api_key=self.api_key, timeout=self.timeout, max_retries=self.max_retries)`.
   - Replace hardcoded `"openai/gpt-oss-120b"` with `self.model`.
   - Refine exception logging to capture error category without leaking sensitive data.
3. **Preserve Fallback Invariant**:
   - Maintain 100% compatibility with `MockLLMProvider` when `GROQ_API_KEY` is empty or calls fail.
   - Ensure zero Groq API calls execute during test runs.

---

## 8. Tests Required for Validation

1. **Provider Initialization Tests**:
   - Verify `GroqLLMProvider` operates in mock fallback mode when `api_key` is missing or empty.
   - Verify `GroqLLMProvider` initializes `self.client` when a key is provided (mocking the `Groq` client class).
2. **Model & Timeout Configuration Tests**:
   - Verify that the configured `model` (e.g., `llama-3.3-70b-versatile`), `timeout`, and `max_retries` are passed to the Groq client.
3. **Fallback on Exceptions**:
   - Verify that simulated API errors (e.g. 401 AuthenticationError, 404 NotFoundError, 429 RateLimitError, Network timeout) fall back to `MockLLMProvider` without raising unhandled exceptions.
   - Verify that malformed JSON or schema mismatches in `generate_structured()` fall back safely to `MockLLMProvider`.
4. **Contract Invariance**:
   - Verify that `ChatService` and `CurioEngine` produce identical `AIResult` structures whether running against live LLM responses or mock fallbacks.
