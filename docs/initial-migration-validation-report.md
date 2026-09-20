# Initial Alembic Migration Validation Report

## Executive Summary

This report documents the formal read-only technical validation of the baseline Alembic migration script for the Curio AI backend.

* **Target Migration File**: [`backend/alembic/versions/6cfd93685f71_initial_schema.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/alembic/versions/6cfd93685f71_initial_schema.py)
* **Revision ID**: `6cfd93685f71`
* **Down Revision**: `None` (Initial baseline)
* **Execution Constraint**: Strict read-only audit. Neither `alembic upgrade` nor `alembic downgrade` was executed against any database.
* **Final Verdict**: **SAFE TO APPLY (PASS)**. The migration is structurally sound, strictly non-destructive, topologically dependency-aware, and ready for deployment.

---

## 1. Validation Checklist & PASS Items

### a. Table Provisioning (7 of 7 Verified)
All 7 domain models are provisioned with accurate column definitions and primary keys:

| Table Name | Entity Class | Primary Key | Key Attributes & Types |
| :--- | :--- | :--- | :--- |
| **`documents`** | `Document` | `id` (UUID) | `filename` (String), `file_size` (Integer), `mime_type` (String), `created_at` (DateTime TZ) |
| **`users`** | `User` | `id` (UUID) | `email` (String, unique indexed), `created_at` (DateTime TZ) |
| **`sessions`** | `Session` | `id` (UUID) | `topic` (String), `source_type` (String), `status` (String), `created_at`, `last_active_at`, `ended_at` |
| **`messages`** | `Message` | `id` (UUID) | `sender` (String), `content` (Text), `input_type` (String), `created_at` (DateTime TZ) |
| **`session_reports`** | `SessionReport` | `session_id` (UUID) | `understanding_score` (Float), `mastery_level` (String), 8 JSON metrics columns |
| **`session_states`** | `SessionState` | `session_id` (UUID) | `current_mode` (String), `difficulty` (Integer), `confidence` (Float), `active_concept` (String), 2 JSON columns |
| **`turn_evaluations`** | `TurnEvaluation` | `message_id` (UUID) | `correctness`, `clarity`, `completeness`, `depth`, `relevance`, `stuck_probability` (Floats), 4 JSON columns |

---

### b. Integrity, Constraints & Cascade Rules (Verified)
- **Primary Keys**: All tables declare explicit primary keys typed as native PostgreSQL `sa.UUID()`.
- **Foreign Keys**:
  - `sessions.document_id -> documents.id` with `ondelete='SET NULL'` (preserves session history if a source document is deleted).
  - `sessions.user_id -> users.id` with `ondelete='CASCADE'` (deletes sessions when user is removed).
  - `messages.session_id -> sessions.id` with `ondelete='CASCADE'`.
  - `session_reports.session_id -> sessions.id` with `ondelete='CASCADE'`.
  - `session_states.session_id -> sessions.id` with `ondelete='CASCADE'`.
  - `turn_evaluations.message_id -> messages.id` with `ondelete='CASCADE'`.
- **Indexes & Unique Constraints**:
  - `ix_users_email`: Enforces email uniqueness (`unique=True`).
  - Indexing on lookup IDs and foreign keys: `ix_documents_id`, `ix_users_id`, `ix_sessions_id`, `ix_sessions_topic`, `ix_sessions_user_id`, `ix_messages_id`, `ix_messages_session_id`, `ix_messages_created_at`, `ix_session_reports_session_id`, `ix_session_states_session_id`, `ix_turn_evaluations_message_id`.

---

### c. Topological Ordering & Dependency Graph (Verified)
- **`upgrade()` Sequence**:
  Parents are systematically created before children:
  1. `documents` (Independent)
  2. `users` (Independent)
  3. `sessions` (Requires `documents` & `users`)
  4. `messages` (Requires `sessions`)
  5. `session_reports` (Requires `sessions`)
  6. `session_states` (Requires `sessions`)
  7. `turn_evaluations` (Requires `messages`)
- **`downgrade()` Inversion Sequence**:
  Children are dropped before parents to prevent foreign key violation exceptions:
  1. `turn_evaluations`
  2. `session_states`
  3. `session_reports`
  4. `messages`
  5. `sessions`
  6. `users`
  7. `documents`
  All indexes are dropped prior to their parent table being dropped.

---

### d. Docker Port & Configuration Consistency (Verified)
- **Docker Compose Mapping**: [`docker-compose.yml`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docker-compose.yml) explicitly maps host port `5433` to container port `5432` (`ports: - "5433:5432"`), eliminating port collisions with Windows native PostgreSQL services on port 5432.
- **Backend Configuration**: [`backend/.env`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/.env) configures `POSTGRES_PORT=5433` and `TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/curio_test_db`.
- **Container Network**: The containerized backend continues to communicate via internal Docker network (`db:5432`).

---

### e. Non-Destructive Operations (Verified)
- `upgrade()` contains exclusively `op.create_table()` and `op.create_index()`.
- Zero table drops, column drops, type alterations, or row deletions are present.

---

### f. Dry-Run SQL Compilation (Verified)
Running Alembic in static SQL generation mode (`alembic -c backend/alembic.ini upgrade head --sql`) confirms:
- Generates clean, standard PostgreSQL DDL wrapped in a single transaction block (`BEGIN; ... COMMIT;`).
- Manages the `alembic_version` state tracking table cleanly.
- Executes with exit code 0.

---

## 2. Issues Requiring Correction

* **Zero Blocking Issues**. The migration script requires no manual corrections prior to execution.

### Architectural Notes (Non-Blocking):
1. **pgvector Extension**:
   - The migration does **not** require or call `pgvector`. None of the 7 existing SQLAlchemy models declare a `Vector` column.
   - The `vector` extension is already installed in the PostgreSQL container via `scripts/init-databases.sh`. A dedicated follow-up migration can be generated when vector embedding columns are added to the ORM.
2. **JSON vs. JSONB**:
   - Structured dictionary fields use standard `sa.JSON` (PostgreSQL `json`). If binary JSON with GIN indexing is required later for high-volume querying, columns can be migrated to `sa.dialects.postgresql.JSONB`.
3. **User Authentication Columns**:
   - The `User` model currently declares `id`, `email`, and `created_at`. When user authentication is implemented, a separate migration will add credential columns (e.g. `password_hash`).

---

## 3. Verdict

| Assessment | Result | Note |
| :--- | :--- | :--- |
| **Schema Completeness** | **PASS** | 7 of 7 models detected |
| **Constraint Integrity** | **PASS** | PKs, FK cascades, unique constraints verified |
| **Topological Safety** | **PASS** | Upgrade and downgrade orders strictly dependency-safe |
| **Environment Consistency** | **PASS** | Port 5433 aligned across Docker, .env, and Alembic |
| **Safety Verdict** | **SAFE TO APPLY** | Ready to be executed via `alembic upgrade head` |

---

## 4. Test Suite Execution

Pytest was executed to confirm complete project health following the validation:
```powershell
& 'backend/.venv/Scripts/python.exe' -m pytest backend/tests -v
```

### Output Summary:
```text
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-8.0.0, pluggy-1.6.0
rootdir: C:\Users\Vishal S Naik\MyProjects\Curio-AI
plugins: anyio-4.15.1
collected 46 items

backend/tests/ai/test_decision_engine.py::test_scenario_1_correct_but_incomplete PASSED [  2%]
...
backend/tests/api/test_database_safety.py::test_validate_test_database_url_accepts_valid_test_url PASSED [ 73%]
backend/tests/api/test_health.py::test_health_endpoint PASSED            [ 76%]
backend/tests/services/test_chat_service.py::test_send_message_invokes_curio_engine_with_canonical_context PASSED [ 78%]
...
backend/tests/services/test_chat_service.py::test_question_hydration_missing_question_ids PASSED [100%]

======================= 46 passed, 60 warnings in 1.56s =======================
```
All **46 tests passed** with zero regressions.
