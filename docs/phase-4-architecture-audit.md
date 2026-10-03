# Phase 4 Architecture Audit

## 1. Current Architecture

The backend is a FastAPI application with SQLAlchemy ORM, PostgreSQL, and a LangGraph-based AI engine (CurioEngine). The architecture follows a clean separation:

- **Models**: SQLAlchemy models in `backend/app/models/`
- **Schemas**: Pydantic schemas in `backend/app/schemas/`
- **Repositories**: Data access layer in `backend/app/repositories/`
- **Services**: Business logic in `backend/app/services/`
- **AI**: Isolated in `backend/app/ai/` with CurioEngine as the only backend interface
- **API**: Versioned under `backend/app/api/v1/`

Key tables: `users`, `sessions`, `session_states`, `messages`, `turn_evaluations`, `session_reports`, `teacher_intervention_logs`, `user_concept_progress`, `documents`.

All relationships use FKs with CASCADE deletes. Ownership is enforced at repository level via `user_id` scoping.

## 2. Existing Report Flow

**What is persisted**: `SessionReport` model stores 28 fields including understanding_score, mastery_level, strengths, 3-tier priority gaps, misconceptions, concepts_mastered, teacher_interventions_required, difficulty_achieved, personalized_roadmap, recommended_exercises, evidence_confidence, concept_assessments, resolved/unresolved gaps & misconceptions, session_evaluation (JSON), created_at.

**What is generated dynamically**: The report is compiled by `ReportService.compile_report()` which:
1. Fetches session messages and turn evaluations
2. Builds `SessionEvidence` via `SessionEvidenceBuilder`
3. Invokes `CurioEngine.evaluate_session()` + `generate_report()` (AI)
4. Maps AI output to `SessionReport` model
5. Persists and marks session COMPLETED

**When generated**: POST `/sessions/{session_id}/end` or POST `/sessions/{session_id}/evaluate`

**Regeneration**: Supported via `force_recompute=True` parameter (idempotent otherwise)

**Retrieval**: GET `/sessions/{session_id}/report` returns persisted report

**User-scoping**: Via session ownership verification in `ReportService.get_report()`

**Immutability**: Reports are replaceable (merge/upsert), not versioned

**Evidence changes**: If evidence changes after report creation, `force_recompute` will regenerate from current evidence. No audit trail of evidence snapshots.

## 3. Learning History Flow

**Persisted representations**:
- Sessions: `Session` + `SessionState` (difficulty, confidence, active_concept, mastery, misconceptions, mode history)
- Messages: `Message` (chronological, sender, content)
- Evaluations: `TurnEvaluation` (per user message, 12 metrics + strategy)
- Teacher interventions: `TeacherInterventionLog` (gap, attempts, explanation, verification, type)
- Cross-session progress: `UserConceptProgress` (mastery_score, attempts, last_practiced, difficulty, misconception_count)

**Coherent timeline**: **NO** - No unified learning timeline API exists. User can retrieve:
- Session list (summary only)
- Individual session details
- Messages per session
- Report per session
- Interventions per session or all
- Progress per concept or all
But no single endpoint combining these into a chronological learning history across sessions.

**Missing capabilities**:
- No session history pagination/filtering
- No evaluation history API
- No learning timeline aggregation
- SessionState data (concept_mastery, misconception_counts) not auto-synced to UserConceptProgress

## 4. Teacher Mode Evidence Status

**How interventions created**: 
- `TeacherInterventionRepository.create()` exists but **ChatService does NOT call it** (deferred item #1)
- `SessionEvidenceBuilder` reads persisted logs as authoritative source (lines 182-211)
- Fallback: heuristic detection from message metadata (lines 214-267)

**Completeness gaps**:
- Not all actual interventions are persisted (ChatService doesn't create logs)
- `intervention_type` is nullable and inconsistently populated
- Verification information only persisted if explicitly provided
- Gap information captured but `related_concept` inference is weak (line 191-194)
- Report generation uses `evidence.teacher_interventions` which prefers DB logs

**Comparison with AI structures**: AI `TeacherIntervention` schema (active, gap, attempt_count, verification_required) differs from persisted `TeacherInterventionLog` (includes verification Q/A, passed, type, timestamps). The evidence builder maps log → evidence but concept linking is incomplete.

## 5. Existing APIs

| Category | Endpoints | Auth | Ownership | Pagination | Filtering |
|----------|-----------|------|-----------|------------|-----------|
| Sessions | POST/GET/PATCH/DELETE /sessions, GET /sessions/{id}, POST /pause/resume/end/evaluate | JWT | ✓ (session_repo) | ✗ | ✗ |
| Messages | POST/GET /sessions/{id}/messages | JWT | ✓ (via session) | ✗ | ✗ |
| Reports | GET /sessions/{id}/report | JWT | ✓ (via session) | N/A | N/A |
| Progress | GET /users/me/progress, /batch, /{concept} | JWT | ✓ (user_id) | ✗ | batch by concepts |
| Teacher Interventions | GET /users/me/teacher-interventions, /users/me/sessions/{id}/teacher-interventions | JWT | ✓ (user_id + session) | ✗ | ✗ |

**Missing endpoints**:
- GET /sessions (with pagination, status filter, date range)
- GET /sessions/{id}/evaluations (paginated)
- GET /users/me/learning-timeline (unified history)
- GET /sessions/{id}/report/history (if versioning added)
- POST /sessions/{id}/report/regenerate (explicit endpoint)

## 6. Missing Capabilities

| Capability | Status | Notes |
|------------|--------|-------|
| Session history pagination | Missing | List returns all sessions |
| Evaluation history API | Missing | Only recent 10 via message_repo |
| Learning timeline (cross-session) | Missing | No aggregation endpoint |
| Report versioning/history | Missing | Single report per session, replaceable |
| Report regeneration endpoint | Partial | Via force_recompute but no dedicated API |
| Teacher intervention auto-persistence | Missing | ChatService doesn't create logs |
| Intervention type consistency | Partial | Nullable, not enforced |
| Cross-session progress sync | Partial | SessionState → UserConceptProgress not automatic |
| Large dataset handling | Missing | No pagination on messages/interventions/progress |

## 7. Database Findings

**Current schema** (migration 602e5c00140b) covers all Phase 1-3 needs. **Phase 4 minimal changes needed**:

| Need | Migration Required? | Proposed Change |
|------|---------------------|-----------------|
| Report versions/history | Yes | New table `session_report_versions` (session_id, version, report_json, created_at) |
| Learning timeline metadata | No | Can be derived via joins; optional materialized view |
| Evidence snapshots | Yes | If report regeneration needs historical evidence, add `session_evidence_snapshots` |
| Pagination indexes | Yes | Add indexes: `messages(session_id, created_at)`, `teacher_intervention_logs(user_id, created_at)`, `turn_evaluations(message_id)` already PK |
| Evaluation pagination | No | Can use existing FKs with LIMIT/OFFSET |

**Ownership constraints**: All user-owned tables have `user_id` FK with CASCADE. `session_reports` scoped via `session_id` → `sessions.user_id`. Sufficient.

## 8. Security/Ownership Findings

**Current pattern**: Every repository method accepts `user_id` and filters by ownership:
- `SessionRepository.get_by_id_and_user()`
- `TeacherInterventionRepository.get_by_session(session_id, user_id)` / `get_by_user(user_id)`
- `ConceptProgressRepository.get_by_user_and_concept()`
- `MessageRepository` scoped via session ownership

**Anti-enumeration**: All return 404 (not 403) for unauthorized access.

**IDOR risks**: Low. All endpoints use `current_user.id` from JWT. No direct `report_id` or `evaluation_id` exposure (reports keyed by session_id, evaluations by message_id).

**Sufficiency**: Current patterns are sufficient for Phase 4. New endpoints must follow same repository pattern.

## 9. Performance Findings

| Issue | Location | Impact |
|-------|----------|--------|
| Full message history loaded | `SessionEvidenceBuilder.build_from_history()` line 80 | O(n) messages per report generation |
| Full evaluation history loaded | `ReportService.compile_report()` lines 80-101 | O(n) evaluations |
| Unbounded intervention retrieval | `TeacherInterventionRepository.get_by_user()` line 57-69 | Loads all user interventions |
| No pagination on messages | `MessageRepository.list_by_session()` line 44-45 | Large sessions = large responses |
| No pagination on interventions | `teacher_interventions.py` GET endpoints | Same |
| N+1 risk in evidence builder | Concept map built per turn | Acceptable for typical session sizes |
| Repeated report generation | `force_recompute` re-runs AI evaluation | Expensive; should be explicit |

**Recommendations**: Add pagination parameters to list endpoints; add LIMIT to repository queries; consider caching compiled reports; add `evidence_snapshot` to avoid re-processing.

## 10. AI Boundary Findings

**Backend responsibilities (correct)**:
- Data retrieval & assembly (`SessionEvidenceBuilder`)
- Persistence (`ReportRepository`, `SessionRepository`)
- API exposure (`reports.py`, `sessions.py`, `progress.py`)
- Ownership enforcement
- Factual aggregation (`LearningProgressService.summary`)

**AI responsibilities (correct)**:
- Turn evaluation (`CurioEngine.process()`)
- Session evaluation (`CurioEngine.evaluate_session()`)
- Report generation (`CurioEngine.generate_report()` → `ReportBuilder`)
- Pedagogical decisions (strategy, difficulty, mode switches)
- Teacher Mode responses (`TeacherModeHandler`)

**Boundary violations**: None found. `SessionEvidenceBuilder` is backend code that normalizes data for AI. `ReportBuilder` is deterministic (no AI). `CurioEngine` is the only AI interface.

## 11. Frontend Contract Findings

**Current schemas match backend models**:
- `SessionReportResponse` ↔ `SessionReport` (all fields)
- `TeacherInterventionResponse` ↔ `TeacherInterventionLog` (all fields)
- `ConceptProgressResponse` ↔ `UserConceptProgress` (all fields)
- `SessionSummaryResponse` includes mode, difficulty, confidence from `SessionState`

**Mismatches/gaps**:
- No schema for paginated responses (list endpoints return raw arrays)
- No schema for learning timeline / unified history
- No schema for evaluation history
- `SessionReportResponse.session_evaluation` is `Optional[Dict]` - loosely typed
- `personalized_roadmap` and `recommended_exercises` are `List[Any]` - could be stricter

## 12. Test Coverage Gaps

| Area | Coverage | Gaps |
|------|----------|------|
| Reports | `test_phase3_api.py` tests report generation | No report regeneration test, no versioning test |
| Sessions | `test_session_idor.py`, `test_api_integration.py` | No pagination test, no filtering test |
| History/Timeline | None | No integration test for cross-session history |
| Evaluations | Indirect via chat tests | No direct evaluation history API test |
| Teacher Interventions | `test_teacher_intervention_api.py`, `test_teacher_mode_persistence.py` | No auto-creation test (since not implemented) |
| Progress | `test_progress_api.py`, `test_learning_progress_service.py` | No cross-session sync test |
| Ownership | `test_session_idor.py` | Good coverage |
| Large datasets | None | No pagination/performance tests |

## 13. Recommended Phase 4 Tasks

| # | Task Title | Objective | Files/Components | Migration | API | AI | Security | Testing | Dependencies |
|---|------------|-----------|------------------|-----------|-----|-----|----------|---------|--------------|
| 4.1 | Session History Pagination & Filtering | Add pagination, status filter, date range to session list | `session_repository.py`, `session_service.py`, `sessions.py`, `schemas/session.py` | No | Yes | No | Verify ownership in list | Pagination, filtering, auth | None |
| 4.2 | Evaluation History API | Expose paginated turn evaluations per session | `message_repository.py`, new service, `schemas/message.py`, new `evaluations.py` router | No | Yes | No | Session ownership | Pagination, auth, cross-user | 4.1 |
| 4.3 | Learning Timeline Aggregation | Unified chronological view across sessions | New `timeline_service.py`, `schemas/timeline.py`, new `timeline.py` router | No | Yes | No | User scoping | Aggregation, ordering, auth | 4.1, 4.2 |
| 4.4 | Report Versioning & Regeneration | Store report versions, explicit regeneration endpoint | `report.py` model, `report_repository.py`, `report_service.py`, `reports.py` | Yes (new table) | Yes | No | Session ownership | Version CRUD, regeneration, auth | 4.1 |
| 4.5 | Teacher Intervention Auto-Persistence | ChatService creates `TeacherInterventionLog` on mode switch | `chat_service.py`, `teacher_intervention_repository.py` | No | No | No | Session ownership | Creation, retrieval, mode transitions | None |
| 4.6 | SessionState → UserConceptProgress Sync | Auto-update cross-session progress on session end | `session_service.py`, `learning_progress_service.py`, `concept_progress_repository.py` | No | No | No | User scoping | Sync accuracy, idempotency | 4.4 (session end) |
| 4.7 | Evidence Snapshots for Reports | Persist `SessionEvidence` at report generation for audit | `report.py` model (add evidence_snapshot), `report_service.py` | Yes (column) | No | No | Session ownership | Snapshot fidelity, size | 4.4 |

## 14. Recommended Task Order

1. **4.1 Session History Pagination & Filtering** - Foundation for all history APIs
2. **4.5 Teacher Intervention Auto-Persistence** - Independent, fixes data completeness
3. **4.2 Evaluation History API** - Builds on 4.1 patterns
4. **4.3 Learning Timeline Aggregation** - Requires 4.1 + 4.2
5. **4.4 Report Versioning & Regeneration** - Requires migration, enables 4.7
6. **4.7 Evidence Snapshots for Reports** - Requires 4.4 migration
7. **4.6 SessionState → UserConceptProgress Sync** - Requires 4.4 (session end flow)

## 15. Next Task

**NEXT TASK = 4.1** — Session History Pagination & Filtering

Rationale: No schema changes, establishes pagination/filtering patterns used by subsequent tasks, unblocks timeline and evaluation history APIs, minimal risk.

## 16. Regression Baseline

Expected: **437/437 passing**.

Note: Test collection failed in this environment due to module import path issues (tests import `backend.app.*` but package not installed). In the project's configured test environment (with proper PYTHONPATH or editable install), the baseline is 437/437 per project status. This audit does not modify code; baseline verification should be run in the project's standard test environment.