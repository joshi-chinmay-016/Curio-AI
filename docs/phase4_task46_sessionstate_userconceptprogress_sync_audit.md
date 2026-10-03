# Phase 4 Task 4.6 — SessionState → UserConceptProgress Synchronization
## Architecture Audit Report

---

### 1. Executive Summary

This audit examines the synchronization path from `SessionState` (per-session learning state) to `UserConceptProgress` (cross-session cumulative progress). 

**Current State**: 
- `SessionState` maintains JSON fields: `concept_mastery` (Dict[str, float]), `misconception_counts` (Dict[str, int]), `mastered_concepts` (List[str]), `unresolved_misconceptions` (List[str])
- `UserConceptProgress` table exists with fields: `mastery_score`, `total_attempts`, `successful_attempts`, `last_practiced_at`, `last_difficulty`, `misconception_count` (per user+concept)
- `LearningProgressService` reads from `UserConceptProgress` for APIs
- **No automatic synchronization exists** — `UserConceptProgress` is only updated via manual `repo.upsert()` calls in tests

**Gap**: `ChatService.send_message()` persists `StateUpdates` to `SessionState` but never synchronizes to `UserConceptProgress`.

**Goal**: Define exactly how and when `SessionState` changes should update `UserConceptProgress` without violating the AI boundary.

---

### 2. Current Data Flow

```
USER MESSAGE
    ↓
ChatService.send_message()
    ↓
Load SessionState (hydrate concept_mastery, misconception_counts from DB)
    ↓
Build AIContext (includes SessionState + LearnerModel)
    ↓
CurioEngine.process(AIContext)
    ↓
AIResult (contains: evaluation, decision, state_updates)
    ↓
ChatService persists:
  - User message
  - AI message  
  - TurnEvaluation
  - TurnAssessment
  - SessionState (merged StateUpdates)
    ↓
Return ChatTurnResponse
```

**Where structured learning data is produced**:
1. **`AIResult.state_updates.concept_mastery`** (Dict[str, float]) — AI-produced mastery from `LearnerModelManager.export_mastery_dict()` (lines 656-660, 828 in student_nodes.py)
2. **`AIResult.state_updates.misconception_counts`** (Dict[str, int]) — AI-produced misconception counts (lines 614-617 in chat_service.py)
3. **`AIResult.state_updates.mastered_concepts`** (List[str]) — AI-produced from evaluation
4. **`AIResult.state_updates.unresolved_misconceptions`** (List[str]) — AI-produced from evaluation
5. **`AIResult.evaluation.correctness`** (float) — AI-produced correctness score
6. **`AIResult.evaluation.misconceptions`** (List[str]) — AI-produced misconception strings
7. **`AIResult.evaluation.mastered_concepts`** (List[str]) — AI-produced mastered concepts
7. **`AIResult.decision.difficulty`** (int) — AI-produced difficulty
8. **`AIResult.state_updates.difficulty`** (int) — AI-produced difficulty

**Missing from StateUpdates**:
- `total_attempts` per concept (only available in `LearnerModel` internal state, not exported)
- `successful_attempts` per concept (not directly exported)
- Per-concept attempt tracking (only aggregate `consecutive_successes/failures` in SessionState)

---

### 3. Exact Field Mapping

| AIResult/StateUpdates Field | SessionState Field | UserConceptProgress Field | Mapping Type | Notes |
|----------------------------|-------------------|--------------------------|--------------|-------|
| `state_updates.concept_mastery` (Dict[str, float]) | `concept_mastery` (JSON) | `mastery_score` | **Direct replace** | AI is source of truth; backend must NOT compute |
| `state_updates.misconception_counts` (Dict[str, int]) | `misconception_counts` (JSON) | `misconception_count` | **Direct replace** | AI is source of truth |
| `state_updates.mastered_concepts` (List[str]) | `mastered_concepts` (JSON) | — | Indirect | Used for session-level tracking only |
| `state_updates.unresolved_misconceptions` (List[str]) | `unresolved_misconceptions` (JSON) | — | Indirect | Session-level only |
| `evaluation.correctness` (float) | — | — | Not directly mappable | Per-turn, not per-concept cumulative |
| `evaluation.misconceptions` (List[str]) | — | — | Not directly mappable | Already folded into misconception_counts |
| `evaluation.mastered_concepts` (List[str]) | — | — | Not directly mappable | Already folded into concept_mastery |
| `state_updates.difficulty` / `decision.difficulty` (int) | `difficulty` (int) | `last_difficulty` | **Direct replace** | AI is source of truth |
| `state_updates.active_concept` (str) | `active_concept` (str) | — | Indirect | Session-level only |
| **MISSING**: per-concept attempts | — | `total_attempts` | **Gap** | Only in LearnerModel internal |
| **MISSING**: per-concept successes | — | `successful_attempts` | **Gap** | Only in LearnerModel internal |

**Critical Finding**: `StateUpdates` does NOT contain per-concept `total_attempts` or `successful_attempts`. These exist only in the internal `LearnerModel` which is serialized but not decomposed per-concept for synchronization.

---

### 4. Mastery / Success Semantics

| Term | Meaning | Source |
|------|---------|--------|
| `concept_mastery` | Dict[concept_id → mastery_score 0.0-1.0] | `LearnerModelManager.export_mastery_dict()` — AI-owned, bounded by MasteryGate |
| `mastery_score` (UserConceptProgress) | Single float 0.0-1.0 per concept | Should mirror latest `concept_mastery[concept]` |
| `correctness` | Per-turn answer quality 0.0-1.0 | AI evaluation; NOT cumulative |
| `misconception_count` | Cumulative count of detected misconceptions | AI `LearnerModel.misconception_count` per concept |
| `total_attempts` | Cumulative answer attempts for concept | **Not in StateUpdates** — only in `LearnerModel.attempt_count` |
| `successful_attempts` | Cumulative substantive correct attempts | **Not in StateUpdates** — only derivable from `LearnerModel.evidence_count` |
| `last_difficulty` | Difficulty of last question for concept | AI `decision.difficulty` |

**Backend CANNOT determine**:
- What constitutes a "successful attempt" (requires AI MasteryGate logic)
- Whether an answer should increment `total_attempts` (acknowledgements don't count)
- Whether misconception was genuinely resolved (requires AI evaluation)

---

### 5. Cross-Session Aggregation Analysis

**Current Architecture**:
- `UserConceptProgress` has **unique constraint** on `(user_id, concept)` — one row per user+concept
- `ConceptProgressRepository.upsert()` replaces provided fields, preserves unspecified fields
- `LearningProgressService` reads and aggregates factually (sum, max, count)

**Aggregation Questions**:

| Field | Current Upsert Behavior | Recommended |
|-------|------------------------|-------------|
| `mastery_score` | **Replace** with AI value | Replace — AI is authoritative |
| `total_attempts` | **Replace** with AI value | Replace — AI is authoritative |
| `successful_attempts` | **Replace** with AI value | Replace — AI is authoritative |
| `misconception_count` | **Replace** with AI value | Replace — AI is authoritative |
| `last_difficulty` | **Replace** with AI value | Replace — AI is authoritative |
| `last_practiced_at` | **Replace** if provided | Replace with current timestamp |

**Critical**: The AI's `LearnerModel` IS the cross-session aggregator. Each turn updates the internal `LearnerModel` which persists to `SessionState.learner_model` (serialized). When a new session starts, the `LearnerModel` can be rehydrated. The `UserConceptProgress` table should mirror the **latest** AI state, not independently aggregate.

---

### 6. Source-of-Truth Analysis

| Entity | Role | Authority |
|--------|------|-----------|
| **AIResult / StateUpdates** | Per-turn AI output | **Authoritative** for AI-derived values (mastery, misconceptions, difficulty) |
| **SessionState** | Per-session mutable state | **Mirror** of AIResult + session-specific tracking (streaks, questions) |
| **LearnerModel** (serialized in SessionState) | Internal AI cumulative state | **Authoritative** for per-concept attempts, evidence, misconceptions |
| **UserConceptProgress** | Cross-session progress snapshot | **Derived mirror** of latest AI state per concept |

**Ownership Hierarchy**:
```
AI (CurioEngine) 
    → produces StateUpdates (authoritative)
    → ChatService persists to SessionState (mirror)
    → LearningProgressService reads UserConceptProgress (derived mirror)
```

**Key Principle**: Backend never computes mastery, attempts, or misconceptions. It only persists what AI explicitly provides.

---

### 6. Synchronization Trigger Analysis

**Possible Trigger Points**:

| Trigger | Pros | Cons | Feasibility |
|---------|------|------|-------------|
| **A. Every ChatService turn** | Immediate sync; captures all changes | High write volume; duplicate risk on retry | ✅ Supported — after SessionState update |
| **B. Session end** | Single batch; avoids turn-level noise | Stale progress during session; session may not end cleanly | ✅ Supported — session status COMPLETED |
| **C. Report generation** | Natural aggregation point | Report regen would mutate progress (forbidden) | ❌ Forbidden — reports must be read-only |
| **D. Explicit progress update API** | User-controlled | Requires user action; not automatic | ❌ Not automatic |
| **E. Background job** | Decoupled | Complex; eventual consistency | ❌ Over-engineered |

**Recommended**: **Trigger A (Every turn)** — after SessionState update, using the same structured `StateUpdates` that already contains the AI-authoritative values.

**Why not B/C/D/E**: 
- C violates report immutability
- B leaves progress stale during long sessions
- D not automatic
- E adds infrastructure complexity

---

### 7. Idempotency Analysis

**Risk**: Turn processed twice → attempts counted twice.

**Available Stable Identifiers**:
| Identifier | Scope | Suitability |
|------------|-------|-------------|
| `user_msg.id` (UUID) | Per-turn | ✅ Best — unique per user message |
| `turn_evaluation.message_id` | Per-turn | ✅ Links to user message |
| `turn_assessment.message_id` | Per-turn | ✅ Links to user message |
| `session_id` + `concept` | Per-session+concept | ❌ Not per-turn |
| Timestamp | Per-turn | ❌ Not unique enough |

**Current `ConceptProgressRepository.upsert()`**: Uses `(user_id, concept)` unique constraint — replaces entire row. This is **NOT idempotent for cumulative fields** if called with incremental values.

**Solution**: The AI must provide **absolute values** (not deltas). Since `StateUpdates.concept_mastery` etc. are absolute, upsert with full replacement is naturally idempotent — same input → same output.

**Missing for Idempotency**: Per-concept `total_attempts` and `successful_attempts` in StateUpdates. Without these, backend cannot safely upsert cumulative counters.

---

### 8. Transaction & Concurrency Analysis

**Current ChatService Transaction Pattern**:
- Each repository method commits independently (`db.commit()` in `create_message`, `create_evaluation`, `update_state`, etc.)
- **No single atomic transaction** for the entire turn

**If sync added at end of `send_message()`**:
- Would be separate commit after SessionState update
- Failure after SessionState but before progress sync → inconsistent state (SessionState updated, UserConceptProgress not)

**Concurrency Risk**: Two concurrent turns for same user+concept
- Both read same `UserConceptProgress`
- Both upsert with same absolute AI values → last write wins (acceptable since values are identical)
- Race on `last_practiced_at` timestamp (acceptable — slight timestamp variance)

**PostgreSQL ON CONFLICT**: Current upsert uses SELECT then UPDATE/INSERT — **race condition possible** between SELECT and INSERT. However, since AI provides absolute values, concurrent upserts with same data are benign.

**Recommendation**: Accept current transaction pattern. Do NOT refactor for atomicity in this task. Document the known limitation.

---

### 9. API Impact

**Existing APIs** (unchanged):
- `GET /users/me/progress` — reads `UserConceptProgress` (will now reflect latest sync)
- `GET /users/me/progress/{concept}` — reads single concept
- `GET /users/me/progress/batch` — reads multiple concepts

**No API changes required**. Progress APIs will automatically show synchronized data.

---

### 10. Report Impact

**Current Flow**: 
- `ReportService.compile_report()` → `SessionEvidenceBuilder` → `CurioEngine.evaluate_session()` / `generate_report()`
- EvidenceBuilder reads `teacher_intervention_logs`, turn evaluations, messages
- **Does NOT read `UserConceptProgress`**

**Critical**: Report generation/regeneration must **NEVER** write to `UserConceptProgress`. Reports are read-only derivations.

**No changes needed** to ReportService or EvidenceBuilder.

---

### 11. AI Boundary Verification

**Forbidden Backend Logic** (must NOT implement):
- ❌ Computing mastery from correctness scores
- ❌ Deciding what counts as "successful attempt"
- ❌ Detecting misconceptions from text
- ❌ Inferring difficulty transitions
- ❌ Applying confidence thresholds
- ❌ Calculating `total_attempts` incrementally

**Allowed Backend Logic**:
- ✅ Persisting AI-provided `concept_mastery` dict to `UserConceptProgress.mastery_score`
- ✅ Persisting AI-provided `misconception_counts` dict to `UserConceptProgress.misconception_count`
- ✅ Persisting AI-provided `difficulty` to `UserConceptProgress.last_difficulty`
- ✅ Setting `last_practiced_at = now()` on sync
- ✅ Upserting with absolute AI values (replace, not increment)

**Current Implementation Check**: 
- `LearnerModelManager` (AI internal) computes mastery — **correct location**
- `ChatService` only merges `StateUpdates` into `SessionState` — **correct**
- No backend code computes mastery — **boundary intact**

---

### 12. Database / Migration Assessment

**Current `UserConceptProgress` Schema**:
```sql
user_id (PK, FK) + concept (PK)
mastery_score FLOAT DEFAULT 0.0
total_attempts INT DEFAULT 0
successful_attempts INT DEFAULT 0
last_practiced_at TIMESTAMPTZ NULLABLE
last_difficulty INT DEFAULT 1
misconception_count INT DEFAULT 0
UniqueConstraint(user_id, concept)
```

**Sufficiency**: **YES — sufficient for MVP synchronization of `mastery_score`, `misconception_count`, `last_difficulty`**

**Gap for Full Fidelity**: 
- Missing `total_attempts` and `successful_attempts` in StateUpdates
- Without these, cannot populate those columns accurately

**Migration Required**: **NO** for basic sync. Columns exist but will remain at defaults (0) until AI contract exposes per-concept attempt counts.

---

### 13. Test Gap Analysis

**Existing Tests** (verify read path only):
- `test_learning_progress_service.py` — 11 tests for GET APIs
- `test_concept_progress_repository.py` — 16 tests for CRUD

**Required New Tests** (for synchronization):

| # | Test Case |
|---|-----------|
| 1 | First turn creates UserConceptProgress with AI mastery |
| 2 | Subsequent turn updates mastery (replace, not increment) |
| 3 | Misconception count sync from misconception_counts |
| 4 | Multiple concepts synced in same turn |
| 5 | Multiple sessions same concept → latest AI value wins |
| 6 | Multiple sessions different concepts → all tracked |
| 7 | User isolation — cross-user progress not mixed |
| 8 | Duplicate turn (retry) → no double-count (idempotent) |
| 9 | Report regeneration does NOT mutate UserConceptProgress |
| 10 | Missing concept_mastery in StateUpdates → no crash |
| 11 | Partial StateUpdates (only difficulty) → no crash |
| 12 | Empty concept_mastery dict → no crash |
| 13 | Explicit zero mastery_score → stored as 0.0 |
| 14 | last_practiced_at updated on sync |
| 15 | Concurrent turns same concept → last write wins benignly |

---

### 14. Recommended Implementation Design

**Files to Modify**:

1. **`backend/app/services/chat_service.py`**
   - Import `ConceptProgressRepository`
   - Add `concept_progress_repo` dependency injection
   - Add `_sync_user_concept_progress()` method called after SessionState update
   - Logic: iterate `updates.concept_mastery`, `updates.misconception_counts`, `updates.difficulty` → upsert per concept

2. **`backend/app/repositories/concept_progress_repository.py`**
   - No changes needed (upsert already supports partial field updates)

3. **`backend/app/services/learning_progress_service.py`**
   - No changes needed

**Files to Create**:
- `backend/tests/services/test_session_concept_progress_sync.py` — new sync tests

**Synchronization Trigger**: End of `ChatService.send_message()`, after `session_repo.update_state()` and `_persist_teacher_intervention()`, before return.

**Exact Source Fields** (from `updates: StateUpdates`):
```python
concept_mastery = updates.concept_mastery or {}
misconception_counts = updates.misconception_counts or {}
difficulty = updates.difficulty or db_session.state.difficulty
active_concept = updates.active_concept or db_session.state.active_concept
```

**Sync Logic**:
```python
for concept, mastery in concept_mastery.items():
    misconception_count = misconception_counts.get(concept, 0)
    self.concept_progress_repo.upsert(
        db=db,
        user_id=user_id,
        concept=concept,
        mastery_score=mastery,
        total_attempts=None,        # Not available in StateUpdates
        successful_attempts=None,   # Not available in StateUpdates
        last_practiced_at=datetime.now(timezone.utc),
        last_difficulty=difficulty,
        misconception_count=misconception_count,
    )
```

**Idempotency Strategy**: AI provides absolute values → upsert replace is naturally idempotent.

**Transaction Strategy**: Separate commit (current architecture). Document limitation.

**Concurrency Strategy**: Last-write-wins with identical AI values is benign.

---

### 15. Risks / Deferred Items

| Risk | Severity | Mitigation |
|------|----------|------------|
| `total_attempts` / `successful_attempts` not in StateUpdates | Medium | Leave at 0 in DB; AI contract must evolve to expose `LearnerModel` per-concept attempts |
| Partial sync if turn fails after SessionState | Low | Acceptable — next turn will re-sync with same AI values |
| `LearnerModel` serialized in SessionState vs UserConceptProgress drift | Medium | `UserConceptProgress` is derived snapshot; `LearnerModel` is source |
| Report regeneration accidentally syncing | Critical | Ensure sync ONLY in `ChatService.send_message()` |
| Concept name mismatch (AI concept_id vs DB) | Low | AI uses consistent concept IDs |

**Deferred to Future Tasks**:
- Expose per-concept `attempt_count` and `evidence_count` from `LearnerModel` in StateUpdates
- Add `total_attempts` / `successful_attempts` sync
- Background reconciliation job for drift detection

---

### 16. Exact Next Step

**Implementation Order**:
1. Add `ConceptProgressRepository` to `ChatService` constructor
2. Implement `_sync_user_concept_progress()` method
3. Call it after `_persist_teacher_intervention()` in `send_message()`
4. Write tests in `test_session_concept_progress_sync.py`
5. Run affected regression tests

**No migrations, no AI changes, no API changes, no report changes.**

---

### Final Verification Checklist

- [ ] Audit confirms AI boundary intact (backend only persists AI-structured output)
- [ ] No new database migration required
- [ ] Synchronization uses absolute AI values (idempotent)
- [ ] No report/regeneration path writes to UserConceptProgress
- [ ] Existing progress APIs automatically reflect synced data
- [ ] Test gaps identified for implementation
- [ ] Transaction/Concurrency limitations documented