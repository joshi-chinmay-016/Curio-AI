# Phase 1: PostgreSQL Schema Mismatch Investigation & Resolution Report

**Date**: 2026-09-21  
**Author**: Backend Infrastructure Engineer (Pair Programming with AI Assistant)  
**Objective**: Investigate and resolve the database schema mismatch causing integration test failures in Curio AI.

---

## 1. Executive Summary

During execution of the PostgreSQL database integration test suite (`pytest -m db_integration -v`), 29 tests failed and 5 tests encountered errors due to missing database columns:
- `session_states.teacher_attempt_count`
- `session_states.teacher_intervention`
- `session_reports.evidence_confidence`

An audit of the migration history and database instances showed that although migration scripts existed in the repository, both the development database (`curio_db`) and test database (`curio_test_db`) were still sitting at the baseline revision `6cfd93685f71`.

Without modifying application code or tests, and without dropping, resetting, or recreating either database, all pending migrations were safely applied using Alembic. Both databases were verified at revision `84274ca763eb (head)`. Following the upgrades, 100% of database integration tests (48/48) and 100% of all tests in the repository (191/191) passed cleanly.

---

## 2. Alembic Migration Files & Revision Lineage

Inspection of `backend/alembic/versions/` confirmed three linear migrations without branch divergence:

```mermaid
graph TD
    base["&lt;base&gt;"] --> rev1["6cfd93685f71<br/>initial_schema"]
    rev1 --> rev2["a1b2c3d4e5f6<br/>add_phase3_evaluation_fields"]
    rev2 --> rev3["84274ca763eb<br/>add_teacher_mode_state_fields [HEAD]"]
```

- **`6cfd93685f71`**: Initial schema defining core tables (`users`, `sessions`, `session_states`, `messages`, `turn_evaluations`, `documents`, `session_reports`).
- **`a1b2c3d4e5f6`**: Phase 3 evaluation fields adding `evidence_confidence` and associated JSON reporting fields.
- **`84274ca763eb`**: Task 3B fields adding `teacher_attempt_count` and `teacher_intervention` to `session_states`.

---

## 3. Initial Database State Audit

Before running any migrations, the active revision was inspected on both PostgreSQL databases running inside the Docker container (`curio-ai-db-1` exposed on port 5433):

| Database Target | Connection URL | Pre-Upgrade Revision | Status |
| :--- | :--- | :--- | :--- |
| **`curio_db`** (Dev) | `postgresql://postgres:postgres@localhost:5433/curio_db` | `6cfd93685f71` | Out of date (missing 2 migrations) |
| **`curio_test_db`** (Test) | `postgresql://postgres:postgres@localhost:5433/curio_test_db` | `6cfd93685f71` | Out of date (missing 2 migrations) |

Both databases were missing:
1. Revision `a1b2c3d4e5f6`
2. Revision `84274ca763eb`

---

## 4. Mapping Missing Columns to Migrations

Each missing column identified in the test failures was traced to its authoring migration:

1. **`session_reports.evidence_confidence`**:
   - **File**: `backend/alembic/versions/a1b2c3d4e5f6_add_phase3_evaluation_fields.py`
   - **Column Definition**: `sa.Column('evidence_confidence', sa.Float(), server_default='0.0', nullable=False)`
   - Also added: `concept_assessments`, `resolved_gaps`, `unresolved_gaps`, `resolved_misconceptions`, `unresolved_misconceptions`, `session_evaluation`.

2. **`session_states.teacher_attempt_count`**:
   - **File**: `backend/alembic/versions/84274ca763eb_add_teacher_mode_state_fields.py`
   - **Column Definition**: `sa.Column('teacher_attempt_count', sa.Integer(), server_default='0', nullable=False)`

3. **`session_states.teacher_intervention`**:
   - **File**: `backend/alembic/versions/84274ca763eb_add_teacher_mode_state_fields.py`
   - **Column Definition**: `sa.Column('teacher_intervention', sa.JSON(), nullable=True)`

---

## 5. Migration Execution

Both databases were upgraded to `head` in forward-only, non-destructive mode:

### 1. Upgrade `curio_db` (Development Database)
```powershell
cd backend
..\backend\.venv\Scripts\alembic.exe upgrade head
```
**Output**:
```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 6cfd93685f71 -> a1b2c3d4e5f6, add_phase3_evaluation_fields
INFO  [alembic.runtime.migration] Running upgrade a1b2c3d4e5f6 -> 84274ca763eb, add_teacher_mode_state_fields
```

### 2. Upgrade `curio_test_db` (Isolated Test Database)
```powershell
cd backend
..\backend\.venv\Scripts\alembic.exe -x db=test upgrade head
```
**Output**:
```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 6cfd93685f71 -> a1b2c3d4e5f6, add_phase3_evaluation_fields
INFO  [alembic.runtime.migration] Running upgrade a1b2c3d4e5f6 -> 84274ca763eb, add_teacher_mode_state_fields
```

---

## 6. Post-Migration Verification

### 1. Alembic Version Table Check
- `curio_db`:
  ```powershell
  cd backend; ..\backend\.venv\Scripts\alembic.exe current
  ```
  $\rightarrow$ `84274ca763eb (head)`
- `curio_test_db`:
  ```powershell
  cd backend; ..\backend\.venv\Scripts\alembic.exe -x db=test current
  ```
  $\rightarrow$ `84274ca763eb (head)`

### 2. PostgreSQL `information_schema` Direct Column Verification
Direct query across both physical databases verified column existence, data types, nullability, and server defaults:

```sql
SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE (table_name = 'session_states' AND column_name IN ('teacher_attempt_count', 'teacher_intervention'))
   OR (table_name = 'session_reports' AND column_name = 'evidence_confidence')
ORDER BY table_name, column_name;
```

#### Results:

| Database | Table | Column | Type | Nullable | Default |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`curio_db`** | `session_reports` | `evidence_confidence` | `double precision` | `NO` | `'0'::double precision` |
| **`curio_db`** | `session_states` | `teacher_attempt_count` | `integer` | `NO` | `0` |
| **`curio_db`** | `session_states` | `teacher_intervention` | `json` | `YES` | `NULL` |
| **`curio_test_db`** | `session_reports` | `evidence_confidence` | `double precision` | `NO` | `'0'::double precision` |
| **`curio_test_db`** | `session_states` | `teacher_attempt_count` | `integer` | `NO` | `0` |
| **`curio_test_db`** | `session_states` | `teacher_intervention` | `json` | `YES` | `NULL` |

---

## 7. Test Suite Validation Results

### Database Integration Test Suite
```powershell
$env:PYTHONPATH=(Get-Location).Path
pytest -m db_integration -v
```
- **Previous Result**: 29 failed, 14 passed, 5 errors.
- **New Result**: **48 passed, 0 failed, 0 errors** in 4.16s (100% pass rate).

### Full Project Test Suite (All Unit + Integration Tests)
```powershell
$env:PYTHONPATH="."
pytest -v
```
- **Total Tests Collected**: 191
- **Passed**: **191 passed, 0 failed, 0 errors** in 5.07s.
- **Pass Rate**: **100%**.

---

## 8. Invariants & Safety Summary

1. **No Database Re-creation**: Neither `curio_db` nor `curio_test_db` was dropped, re-created, or reset.
2. **Transactional DDL**: Both migrations were executed under standard PostgreSQL transactional DDL boundaries.
3. **Application & Test Code Untouched**: No application source code or test files were modified during this investigation and upgrade.
4. **Environment Health**: PostgreSQL container (`ankane/pgvector:latest` on port 5433) is healthy and operational.
