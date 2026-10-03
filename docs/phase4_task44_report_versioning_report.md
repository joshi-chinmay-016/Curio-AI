# Phase 4 Task 4.4 — Report Versioning & Regeneration Implementation Report

## Executive Summary
Phase 4 Task 4.4 transitions Curio AI's report persistence from a mutable single-report structure to an immutable, versioned report architecture based on **Option B**:
- Dedicated `session_report_versions` table storing an append-only audit trail of historical report generations.
- Retained `session_reports` table as a high-performance current/latest report cache.
- Full backward compatibility for existing endpoints (`GET /report`), frontend consumers, and Phase 4.3 learning timeline aggregation.
- Strict ownership and anti-enumeration (IDOR protection returning HTTP 404).
- Single-transaction atomic commit ensuring synchronization between versions, latest cache, and session status.
- Strict preservation of the AI boundary: CurioEngine, LangGraph, and prompt evaluations remain untouched.

---

## 1. Files Created
1. `backend/app/models/report_version.py`
   - Defines `SessionReportVersion` model with UUID primary key, foreign key to `sessions.id` (ON DELETE CASCADE), `version_number`, full parity of report fields, timezone-aware `created_at`, unique constraint `uq_session_report_version (session_id, version_number)`, and relationship to `Session`.
2. `backend/app/repositories/report_version_repository.py`
   - Session-scoped repository providing `create_version`, `get_latest_version`, `get_by_version_number`, `get_max_version_number`, and `list_versions_paginated`. Historical versions are immutable (no update or delete methods).
3. `backend/alembic/versions/8b9c0d1e2f3a_add_report_versions.py`
   - Revision `8b9c0d1e2f3a` (child of `7a8b9c0d1e2f`).
   - Adds `version_number` to `session_reports`.
   - Creates `session_report_versions` with columns, unique constraint, and composite indexes:
     - `ix_session_report_versions_session_version (session_id, version_number)`
     - `ix_session_report_versions_session_created (session_id, created_at)`
   - Backfills all existing `session_reports` rows into `session_report_versions` as Version 1, preserving original timestamps.
4. `backend/tests/api/test_report_versioning.py`
   - 16 comprehensive integration tests covering initial compilation, regeneration, historical immutability, pagination, anti-enumeration IDOR, unauthenticated access, empty session validation, concurrency constraints, and transaction rollback on failure.

---

## 2. Files Modified
1. `backend/app/models/report.py`
   - Added `version_number = Column(Integer, default=1, server_default="1", nullable=False)` to `SessionReport`.
2. `backend/app/models/session.py`
   - Added `report_versions = relationship("SessionReportVersion", back_populates="session", cascade="all, delete-orphan", order_by="desc(SessionReportVersion.version_number)")`.
   - Preserved `Session.report` 1:1 relationship.
3. `backend/app/db/base.py` & `backend/app/main.py`
   - Registered `SessionReportVersion` in model registries.
4. `backend/app/schemas/report.py`
   - Added `version_number: int = 1` to `SessionReportResponse` (backward compatible).
   - Created `SessionReportVersionResponse`.
   - Created `SessionReportHistoryListResponse` with pagination metadata (`items`, `total`, `page`, `page_size`, `pages`).
5. `backend/app/repositories/report_repository.py`
   - Added `commit: bool = True` to `create_or_update` to allow external transaction management by `ReportService`.
6. `backend/app/services/report_service.py`
   - Updated `compile_report` to allocate Version 1, write immutable version, update latest cache, and complete session in a single atomic transaction.
   - Implemented `regenerate_report` with ownership verification, validation of learner interaction history (400 if empty), row locking (`with_for_update()`), sequential version allocation ($N+1$), immutable version persistence, cache update, and atomic commit.
   - Added `get_report_history` and `get_report_version`.
7. `backend/app/api/v1/reports.py`
   - `POST /sessions/{session_id}/report/regenerate`: Creates Version $N+1$.
   - `GET /sessions/{session_id}/reports`: Paginated history, newest first.
   - `GET /sessions/{session_id}/reports/{version_number}`: Exact version retrieval.
   - `GET /sessions/{session_id}/report`: Returns latest version cache (unchanged route).

---

## 3. Alembic Migration & Database Status
- **Parent Revision**: `7a8b9c0d1e2f`
- **Current Revision**: `8b9c0d1e2f3a` (`add_report_versions`)
- **Single Head Confirmed**: `8b9c0d1e2f3a (head)`
- **Dev Database (`curio_dev_db`)**: Upgraded and validated. Existing data backfilled to Version 1.
- **Test Database (`curio_test_db`)**: Upgraded and validated.

---

## 4. Key Architectural Guarantees
1. **Historical Immutability**:
   - Explicitly validated by `test_historical_version_1_remains_unchanged_after_regeneration`.
   - After regeneration, Version 1 fields (scores, gaps, misconceptions, roadmap) remain identical.
2. **Transaction Integrity**:
   - Eliminated the previous two-commit window. Report version creation, latest cache update, and session status updates are committed in one atomic transaction.
   - On AI error or persistence failure, transaction rollback preserves existing latest report and leaves no partial state.
3. **Concurrency Protection**:
   - Session row is locked with `SELECT ... FOR UPDATE` before allocating `MAX(version_number) + 1`.
   - `UNIQUE(session_id, version_number)` constraint prevents any duplicate version numbers.
4. **IDOR & Anti-Enumeration**:
   - Foreign session access to `/report`, `/reports`, `/reports/{version_number}`, or `/report/regenerate` returns HTTP 404 (not 403).
5. **Phase 4.7 Boundary**:
   - Evidence snapshotting was **NOT** implemented in this task; report versions store immutable report outputs only.
6. **AI Boundary**:
   - No modifications to CurioEngine, LangGraph, prompts, or AI decision logic.

---

## 5. Test Verification Summary
A total of **99 targeted integration and regression tests** were executed and passed with 0 failures:
- `backend/tests/api/test_report_versioning.py`: **16 passed**
- `backend/tests/api/test_phase3_api.py`: **6 passed**
- `backend/tests/api/test_timeline.py`: **36 passed**
- `backend/tests/api/test_session_idor.py`: **41 passed**

**Total: 99 / 99 passed (100% success)**.
