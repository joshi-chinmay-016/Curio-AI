# Phase 4 Task 4.7 — Evidence Snapshots for Reports
## Architecture Audit Report

---

### 1. Executive Summary

This audit examines the current report versioning architecture and determines how to implement **immutable evidence snapshots** for report versions to achieve historical reproducibility.

**Current State (Phase 4.4):**
- Report versioning exists: `SessionReport` (latest cache) + `SessionReportVersion` (immutable history)
- Report generation: `ReportService._build_report_data()` → `SessionEvidenceBuilder.build_from_history()` → `CurioEngine.evaluate_session()` + `generate_report()`
- Regeneration creates new version N+1 with fresh evidence from **current mutable tables**
- Historical versions are immutable in terms of report output fields, but **evidence is not snapshotted**

**Critical Gap:** When report version N is regenerated to version N+1, the evidence used for version N is lost. If source data (messages, evaluations, interventions) is later modified or deleted, version N's evidence cannot be reconstructed. The report output fields are frozen, but the **input evidence** that produced them is not.

**Audit Conclusion:** A dedicated `report_evidence_snapshots` table is needed, storing the exact `SessionEvidence` passed to the AI at report generation time, linked to each `SessionReportVersion`.

---

### 2. Current Report Version Flow

**Compile/Regenerate Flow (ReportService):**

```
POST /sessions/{id}/evaluate or POST /sessions/{id}/report/regenerate
    ↓
ReportService.compile_report() / regenerate_report()
    ↓
1. Acquire session FOR UPDATE lock
2. Determine next version_number
3. _build_report_data():
   a. Load messages + evaluations from DB (mutable tables)
   b. SessionEvidenceBuilder.build_from_history() → SessionEvidence
      - Queries TeacherInterventionLog (mutable)
      - Uses session state, messages, evaluations (mutable)
   c. CurioEngine.evaluate_session(evidence) → SessionEvaluation
   d. CurioEngine.generate_report(evidence) → LearningReport
   e. Map to report_data dict
4. Create SessionReportVersion (immutable output fields)
5. Update SessionReport cache
6. Mark session COMPLETED
7. Single commit
```

**Evidence Collection (SessionEvidenceBuilder.build_from_history):**

| Evidence Source | Query/Repository | Currently Mutable? | Snapshotted? |
|-----------------|------------------|-------------------|--------------|
| Messages | `db_session.messages` relationship | YES (new messages added) | NO |
| TurnEvaluations | `message.evaluation` relationship | YES (new evaluations added) | NO |
| TurnAssessments | `TurnAssessmentRepository` | YES (new assessments added) | NO |
| TeacherInterventions | `TeacherInterventionRepository.get_by_session()` | YES (new logs added) | NO |
| SessionState | `db_session.state` relationship | YES (updated per turn) | NO |
| Session metadata | `db_session` fields | YES (status, ended_at) | NO |
| SessionEvidence output | Built in-memory | N/A | NO |

**What's Lost After Regeneration:** The exact `SessionEvidence` object passed to `CurioEngine` is discarded after report generation. Only the AI's *output* (report fields) is persisted in `SessionReportVersion`. The *input evidence* that produced that output is not stored.

---

### 3. Evidence Inventory

| Evidence Type | Source Table/Model | Query Method | Used by AI? | Currently Snapshotted? | Mutable? |
|---------------|-------------------|--------------|-------------|----------------------|----------|
| **User messages** | `messages` (sender=USER) | `session.messages` | YES (TurnEvidence) | NO | YES (appended) |
| **AI messages** | `messages` (sender=AI) | `session.messages` | YES (question context) | NO | YES |
| **TurnEvaluations** | `turn_evaluations` | `message.evaluation` | YES (TurnEvidence.evaluation) | NO | YES |
| **TurnAssessments** | `turn_assessments` | `TurnAssessmentRepository` | YES (LearningAssessment, etc.) | NO | YES |
| **TeacherInterventionLogs** | `teacher_intervention_logs` | `TeacherInterventionRepository.get_by_session()` | YES (TeacherInterventionEvidence) | NO | YES |
| **SessionState** | `session_states` | `session.state` relationship | YES (difficulty, active_concept) | NO | YES |
| **Session metadata** | `sessions` | `db_session` fields | YES (topic, status) | NO | YES |
| **LearningProgress** | `user_concept_progress` | `LearningProgressService` | NO (not passed to AI) | NO | YES |
| **SessionEvidence (assembled)** | Built in-memory | `SessionEvidenceBuilder.build_from_history()` | YES (passed to CurioEngine) | **NO** | N/A |

**Key Finding:** The assembled `SessionEvidence` object (which is the exact input to `CurioEngine.evaluate_session()` and `generate_report()`) is **never persisted**. It exists only in memory during report generation.

---

### 4. Historical Reproducibility Problem

**Scenario:**
1. T1: Report Version 1 generated → evidence built from current tables
2. T2: New messages/evaluations/interventions added
3. T3: Report Version 2 generated → new evidence from updated tables
4. T4: Source data modified/deleted (e.g., message deleted, evaluation updated)
5. T5: User requests Version 1

**Current Result:** Version 1's *output* (report fields) is frozen in `SessionReportVersion`. But Version 1's *input evidence* cannot be reconstructed because:
- Messages may be deleted (cascade from session)
- Evaluations may be updated
- TeacherInterventionLogs may be modified
- SessionState is overwritten
- `SessionEvidenceBuilder` always queries current mutable state

**Data That Must Be Frozen for Historical Reproducibility:**
1. **Exact `SessionEvidence` passed to AI** — turns, interventions, concept map, difficulty progression
2. **Raw source records** at time of generation — messages, evaluations, interventions, session state

---

### 5. Snapshot Design Options Comparison

| Criterion | Option A: JSON on SessionReportVersion | Option B: Dedicated `report_evidence_snapshots` table | Option C: Normalized evidence tables | Option D: Store only source IDs |
|-----------|----------------------------------------|------------------------------------------------------|--------------------------------------|--------------------------------|
| **Historical Immutability** | ✅ (row immutable) | ✅ (separate immutable table) | ❌ (normalized = mutable) | ❌ (IDs don't freeze data) |
| **Reproducibility** | ✅ Full evidence in one row | ✅ Full evidence in one row | ❌ Requires joins of mutable tables | ❌ IDs don't freeze data |
| **Implementation Complexity** | Low (add JSON column) | Medium (new table + FK) | High (many tables) | Low (store IDs only) |
| **Query Performance** | ✅ Single row read | ✅ Single row read | ❌ Multiple joins | ❌ Requires reconstruction |
| **Storage** | Medium (JSON in version row) | Medium (separate table) | High (normalized) | Low (IDs only) |
| **Schema Evolution** | ❌ Version row schema coupling | ✅ Separate evolution | ❌ Complex migrations | ✅ Simple |
| **Report Version Isolation** | ✅ 1:1 with version | ✅ 1:1 with version | ❌ Shared tables | ❌ Shared tables |
| **Deletion Safety** | ✅ Version row survives | ✅ Snapshot table survives | ❌ Depends on cascades | ❌ Source data may be gone |
| **Ownership/IDOR** | ✅ Via version ownership | ✅ Via version ownership | ❌ Complex | ❌ Complex |
| **AI Boundary** | ✅ Stores EvidenceBuilder output | ✅ Stores EvidenceBuilder output | ❌ Stores raw records | ❌ Stores IDs |
| **Compatibility with Versioning** | ✅ Same transaction | ✅ Same transaction | ❌ Complex | ❌ Complex |

**Recommendation: Option B — Dedicated `report_evidence_snapshots` table**

**Rationale:**
- Best balance of immutability, reproducibility, and architectural fit
- Separates evidence from report output (clean separation of concerns)
- Allows schema evolution of evidence independently from report output
- Single row per report version → simple queries
- Clean ownership via `SessionReportVersion` FK
- Does not couple evidence schema to report output schema

---

### 6. Exact Snapshot Contents

**Snapshot Should Contain: The exact `SessionEvidence` output from `SessionEvidenceBuilder.build_from_history()`**

```json
{
  "schema_version": 1,
  "session_evidence": {
    "session_id": "uuid",
    "topic": "string",
    "turns": [
      {
        "turn_index": 0,
        "question": "string",
        "learner_answer": "string",
        "concept": "string",
        "difficulty": 1,
        "evaluation": {
          "correctness": 0.8,
          "clarity": 0.7,
          "completeness": 0.6,
          "depth": 0.5,
          "relevance": 1.0,
          "stuck_probability": 0.1,
          "misconceptions": ["string"],
          "missing_concepts": ["string"],
          "undefined_terms": ["string"],
          "mastered_concepts": ["string"],
          "knowledge_gap": "string",
          "recommended_strategy": "PROBE_WHY",
          "recommended_difficulty": 2
        }
      }
    ],
    "teacher_interventions": [
      {
        "intervention_index": 0,
        "gap": "string",
        "attempt_count": 1,
        "teacher_explanation": "string",
        "verification_question": "string",
        "verification_answer": "string",
        "verification_passed": true,
        "related_concept": "string"
      }
    ],
    "concepts_encountered": ["string"],
    "concept_evidence_map": {
      "concept_name": {
        "concept": "string",
        "turns_evaluated": [0, 1],
        "correctness_scores": [0.8, 0.9],
        "misconceptions": ["string"],
        "gaps": ["string"],
        "teacher_assisted": false,
        "highest_difficulty_passed": 2
      }
    },
    "difficulty_progression": [1, 2, 2],
    "confidence_progression": [0.5, 0.6, 0.7],
    "total_learner_turns": 5,
    "successful_turns": 3,
    "failed_turns": 1
  },
  "session_metadata": {
    "session_id": "uuid",
    "topic": "string",
    "status": "ACTIVE",
    "source_type": "GENERAL",
    "created_at": "ISO timestamp",
    "session_state_snapshot": {
      "current_mode": "STUDENT",
      "difficulty": 2,
      "confidence": 0.7,
      "active_concept": "string",
      "current_question_id": "uuid",
      "interrupted_question_id": "uuid",
      "consecutive_strong_answers": 2,
      "consecutive_weak_answers": 0,
      "unresolved_misconceptions": ["string"],
      "mastered_concepts": ["string"],
      "teacher_attempt_count": 0,
      "concept_mastery": {"concept": 0.8},
      "misconception_counts": {"concept": 1},
      "recent_strategy_history": ["PROBE_WHY"],
      "mode_switch_history": [...]
    }
  },
  "learning_progress_snapshot": {
    "concepts": [
      {
        "concept": "string",
        "mastery_score": 0.8,
        "total_attempts": 5,
        "successful_attempts": 4,
        "last_practiced_at": "ISO timestamp",
        "last_difficulty": 2,
        "misconception_count": 1
      }
    ]
  },
  "turn_assessments": [
    {
      "message_id": "uuid",
      "learning_assessment": {...},
      "turn_interpretation": {...},
      "learning_objective": {...},
      "question_specification": {...}
    }
  ],
  "generated_at": "ISO timestamp",
  "evidence_builder_version": "1.0"
}
```

**What NOT to Snapshot:**
- ❌ AI output (LearningReport, SessionEvaluation) — already in SessionReportVersion
- ❌ AI reasoning/interpretation — belongs to AI boundary
- ❌ Computed/derived fields — only factual source evidence

---

### 7. Snapshot Timing

**Recommended: Create snapshot BEFORE AI generation, within the same transaction**

```
BEGIN TRANSACTION
  1. Lock session FOR UPDATE
  2. Determine next version_number
  3. Build evidence → SessionEvidence
  4. Create evidence snapshot row (evidence_json, schema_version) → get snapshot_id
  5. Run CurioEngine on SessionEvidence → SessionEvaluation + LearningReport
  6. Create SessionReportVersion (with snapshot_id FK)
  7. Update SessionReport cache
  8. Mark session COMPLETED
COMMIT TRANSACTION
```

**Failure Case Analysis:**

| Failure Point | Behavior |
|---------------|----------|
| Evidence snapshot succeeds, AI generation fails | Rollback → no version created, no snapshot orphaned |
| AI generation succeeds, snapshot persistence fails | Rollback → no version created |
| Report version persistence fails | Rollback → no version created |
| Concurrent regeneration | Prevented by `SELECT FOR UPDATE` on session |
| Duplicate regeneration request | Idempotent check under lock returns existing |

---

### 8. Atomicity Analysis

**Current Architecture:** `ReportService` already uses a single transaction with `SELECT FOR UPDATE` on session, `commit=False` on repository creates, then single `db.commit()`.

**Evidence Snapshot Integration:** Can be added within the same transaction:
1. `SessionEvidenceBuilder.build_from_history()` returns `SessionEvidence`
2. Serialize to JSON → insert into `report_evidence_snapshots` (with `commit=False`)
3. Get generated `snapshot_id`
4. Create `SessionReportVersion` with `evidence_snapshot_id` FK (with `commit=False`)
4. Update `SessionReport` cache (with `commit=False`)
5. Single `db.commit()`

**No transaction refactor needed** — fits existing pattern exactly.

---

### 9. Immutability Strategy

**Database-Level Protections:**
1. **Dedicated table** `report_evidence_snapshots` with no UPDATE/DELETE APIs
2. **FK to SessionReportVersion** with `ON DELETE RESTRICT` (snapshot cannot be deleted while version exists)
3. **No UPDATE endpoint** — repository only has `create()` method
3. **Composite unique constraint** on `(report_version_id)` ensures 1:1
4. **Row-level security** not needed — ownership inherited from `SessionReportVersion` → `Session` → `User`

**Table Schema:**
```sql
CREATE TABLE report_evidence_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_version_id UUID NOT NULL REFERENCES session_report_versions(id) ON DELETE RESTRICT,
    schema_version INT NOT NULL DEFAULT 1,
    evidence_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (report_version_id)
);

CREATE INDEX ix_report_evidence_snapshots_version ON report_evidence_snapshots(report_version_id);
```

---

### 10. Report Version Relationship

```
Session (1) → SessionReport (1) ←→ SessionReportVersion (N)
                          ↓
                    SessionReportVersion (1) → report_evidence_snapshots (1)
```

**Relationship:** One evidence snapshot per report version. The snapshot belongs to the version, not the session.

**FK:** `report_evidence_snapshots.report_version_id` → `session_report_versions.id`

**Cascade:** `ON DELETE RESTRICT` on version side (cannot delete version if snapshot exists, but versions are never deleted anyway)

---

### 11. Regeneration Behavior

**Current:** Regeneration creates Version N+1 with fresh evidence from current tables.

**With Snapshots:**
- Version N retains its original evidence snapshot (immutable)
- Version N+1 gets a NEW evidence snapshot built from current tables
- Latest cache (`SessionReport`) points to N+1
- History shows both versions with their respective snapshots
- User can retrieve Version N's evidence to see exactly what the AI saw

**If source evidence changed between T1 and T2:**
- Version 1 snapshot = evidence at T1
- Version 2 snapshot = evidence at T2 (includes new messages/evals/interventions)
- Both retrievable and comparable

---

### 12. Deletion/Retention Analysis

**Current Cascade Behavior:**
| Source Table | FK to Session | On Delete Session | Impact on Reports |
|--------------|---------------|-------------------|-------------------|
| messages | session_id → sessions | CASCADE | Messages gone |
| turn_evaluations | message_id → messages | CASCADE | Evaluations gone |
| turn_assessments | session_id → sessions | CASCADE | Assessments gone |
| teacher_intervention_logs | session_id → sessions | CASCADE | Interventions gone |
| session_states | session_id → sessions | CASCADE | State gone |

**With Evidence Snapshots:** Report versions remain fully readable even if session is deleted (cascades don't affect `session_report_versions` or `report_evidence_snapshots` — they have their own FKs with `ON DELETE RESTRICT`).

**Retention Policy:** Evidence snapshots persist as long as their report versions exist. Report versions are never deleted (immutable history).

---

### 13. Security / IDOR

**Ownership Chain:** `User` → `Session` → `SessionReportVersion` → `report_evidence_snapshots`

**Existing Enforcement:** All report APIs verify `session.user_id == current_user.id` before returning data.

**Snapshot Access:** No direct snapshot API needed initially. Snapshots are accessed via report version endpoints:
- `GET /sessions/{id}/reports/{version}` → returns report + can include `evidence_snapshot_id`
- Future: `GET /sessions/{id}/reports/{version}/evidence` → returns snapshot (same ownership check)

**No new IDOR vectors** — snapshots inherit version ownership.

---

### 14. Performance Analysis

**Expected Snapshot Size:**
- Messages: ~50-200 per session (500 chars each truncated in timeline, but full for evidence)
- TurnEvidence: ~50-200 turns × ~500 bytes = ~25-100 KB
- TeacherInterventions: ~0-10 × ~2 KB = ~20 KB
- SessionState snapshot: ~5 KB
- TurnAssessments: ~50-200 × ~3 KB = ~150-600 KB (assessment JSON can be large)
- **Total estimated: 200 KB - 1 MB per snapshot**

**Mitigation:**
- JSONB storage (compressed in Postgres)
- EvidenceBuilder already limits: max 10 recent evaluations, truncated content in timeline
- Could add size limit + truncation in builder if needed

**Query Performance:**
- Single row read by `report_version_id` (indexed)
- ~1-5 ms read time for 1 MB JSONB

---

### 15. Schema Evolution

**Required:** `schema_version` column in `report_evidence_snapshots`

```python
class ReportEvidenceSnapshot(Base):
    ...
    schema_version = Column(Integer, default=1, nullable=False)
    evidence_json = Column(JSONB, nullable=False)
```

**Evolution Strategy:**
- v1: Current `SessionEvidence` + session metadata + learning progress + turn assessments
- v2+: Add new fields to `evidence_json` (backward compatible)
- Breaking changes → increment `schema_version`, add migration, maintain backward-compatible deserialization

---

### 16. AI Boundary Verification

**Snapshot Contains Only:**
- ✅ Raw source evidence (messages, evaluations, interventions)
- ✅ Structured factual evidence (TurnEvidence, TeacherInterventionEvidence, ConceptEvidenceItem)
- ✅ Session metadata (topic, state snapshot)
- ✅ Learning progress (factual counters from UserConceptProgress)
- ✅ Turn assessments (structured AI output, not interpretation)

**Snapshot Does NOT Contain:**
- ❌ AI-generated report output (LearningReport, SessionEvaluation) — already in version
- ❌ AI reasoning/interpretation — AI boundary
- ❌ Backend-computed mastery/confidence — AI boundary

**Verification:** Snapshot = `SessionEvidenceBuilder` output + metadata. This is the **exact input** to `CurioEngine.evaluate_session()` and `generate_report()`. No AI reasoning reconstructed.

---

### 17. API Impact

**No new APIs required for MVP.**

**Existing APIs Unchanged:**
- `GET /sessions/{id}/report` → latest report
- `GET /sessions/{id}/reports` → history
- `GET /sessions/{id}/reports/{version}` → specific version
- `POST /sessions/{id}/report/regenerate` → new version with new snapshot

**Optional Future API:**
- `GET /sessions/{id}/reports/{version}/evidence` → returns snapshot (same ownership check)

---

### 18. Migration Assessment

**Migration Required: YES**

**New Table:** `report_evidence_snapshots`

**Columns:**
- `id` UUID PK
- `report_version_id` UUID FK → `session_report_versions(id)` ON DELETE RESTRICT, UNIQUE
- `schema_version` INT NOT NULL DEFAULT 1
- `evidence_json` JSONB NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT now()

**Index:** `CREATE INDEX ON report_evidence_snapshots(report_version_id)`

**FK Modification:** Add `evidence_snapshot_id` UUID FK to `session_report_versions` (nullable for existing versions)

```sql
ALTER TABLE session_report_versions 
ADD COLUMN evidence_snapshot_id UUID REFERENCES report_evidence_snapshots(id) ON DELETE RESTRICT;

CREATE INDEX ix_session_report_versions_snapshot ON session_report_versions(evidence_snapshot_id);
```

**Backfill:** Existing report versions will have `evidence_snapshot_id = NULL` (acceptable — they predate snapshots)

---

### 19. Test Gap Analysis

| # | Test Case |
|---|-----------|
| 1 | Report Version 1 gets immutable evidence snapshot |
| 2 | Report Version 2 gets a separate snapshot |
| 3 | Version 1 snapshot remains unchanged after Version 2 |
| 4 | Source messages change after Version 1 → Version 1 snapshot unchanged |
| 5 | Source evaluations change after Version 1 → Version 1 snapshot unchanged |
| 6 | Teacher intervention changes after Version 1 → Version 1 snapshot unchanged |
| 7 | SessionState changes after Version 1 → Version 1 snapshot unchanged |
| 8 | UserConceptProgress changes after Version 1 → Version 1 snapshot unchanged |
| 9 | Deleted source records do not destroy historical report evidence |
| 10 | Cross-user access to snapshots denied (IDOR) |
| 11 | Regeneration creates a new snapshot |
| 12 | Failed AI generation does not create an invalid completed report version |
| 13 | Snapshot persistence failure is handled safely (rollback) |
| 14 | Empty evidence is handled |
| 15 | Large but bounded evidence is handled |
| 16 | Snapshot schema_version is preserved |
| 17 | Existing report history tests remain valid |
| 18 | Existing timeline/intervention/evaluation tests remain valid |

---

### 20. Recommended Implementation Design

**Files to Modify:**

1. **`backend/app/models/report_version.py`** — Add `evidence_snapshot_id` FK column
2. **`backend/app/models/report_evidence_snapshot.py`** — New model (NEW FILE)
3. **`backend/app/repositories/report_evidence_snapshot_repository.py`** — New repository (NEW FILE)
3. **`backend/app/services/report_service.py`** — Add snapshot creation in `compile_report()` and `regenerate_report()`
4. **`backend/alembic/versions/xxxx_add_report_evidence_snapshots.py`** — New migration (NEW FILE)

**Files NOT to Modify:**
- `CurioEngine`, `SessionEvidenceBuilder`, `SessionEvaluator` — AI boundary intact
- `ReportService` public API — unchanged
- Report APIs — unchanged
- `SessionEvidenceBuilder` — unchanged (only its output is snapshotted)

**Exact Snapshot Creation Point:**
In `ReportService._build_report_data()`, after `evidence = self.evidence_builder.build_from_history(...)`:
```python
# Serialize evidence for snapshot
evidence_json = evidence.model_dump(mode="json")
# Create snapshot row
snapshot = ReportEvidenceSnapshot(
    report_version_id=None,  # Will be set after version created
    schema_version=1,
    evidence_json=evidence_json,
)
self.evidence_snapshot_repo.create(db, snapshot, commit=False)
snapshot_id = snapshot.id
# Then create SessionReportVersion with evidence_snapshot_id=snapshot_id
```

**Transaction Behavior:** Same transaction as version creation (existing pattern with `commit=False` on repos, single `db.commit()` at end).

**Ownership Mechanism:** Inherited from `SessionReportVersion` → `Session` → `User`. No separate ownership checks needed.

---

### 21. Risks / Deferred Work

| Risk | Severity | Mitigation |
|------|----------|------------|
| Snapshot size growth | Medium | JSONB compression; monitor; add size limit if needed |
| Schema evolution complexity | Low | `schema_version` column + backward-compatible deserialization |
| Transaction rollback leaves orphan snapshot | Low | Same transaction — atomic |
| Report version without snapshot (pre-migration) | Low | `evidence_snapshot_id` nullable |
| AI contract changes breaking snapshot format | Medium | `schema_version` + versioned deserialization |
| Snapshot includes AI output by accident | Critical | Code review; snapshot = EvidenceBuilder output only |
| Performance of large JSONB reads | Low | Index on version_id; JSONB is efficient |

**Deferred to Future Tasks:**
- `GET /reports/{version}/evidence` API
- Snapshot diff/comparison between versions
- Evidence snapshot export/download
- Automated snapshot validation/repair job

---

### 22. Exact Next Step

**Implementation Order:**

1. **Create migration** for `report_evidence_snapshots` table + `evidence_snapshot_id` FK on `session_report_versions`
2. **Create model** `ReportEvidenceSnapshot` in `backend/app/models/report_evidence_snapshot.py`
3. **Create repository** `ReportEvidenceSnapshotRepository` with `create()` method
4. **Modify `ReportService`**:
   - Inject `ReportEvidenceSnapshotRepository`
   - In `_build_report_data()`: after `evidence = self.evidence_builder.build_from_history()`, create snapshot
   - Pass `evidence_snapshot_id` to `SessionReportVersion` creation
5. **Write tests** in `backend/tests/services/test_report_evidence_snapshots.py`
6. **Run regression tests** (report versioning, timeline, interventions, progress)

**No AI changes. No API changes. No report behavior changes.**