# Initial Alembic Migration Review Report

## Executive Summary

This report documents the generation and technical inspection of the baseline Alembic migration for the Curio AI backend.

The migration was generated using the target development database (`curio_db`) while preserving the isolated integration-test database (`curio_test_db`). In strict accordance with the task instructions:
- `alembic upgrade head` was **not** run.
- `alembic downgrade` was **not** run.
- No live database tables or data were provisioned, modified, or dropped.
- All application models and logic remain unchanged.
- All **46 tests passed**.

---

## 1. Migration Specification

* **Filename**: [`backend/alembic/versions/6cfd93685f71_initial_schema.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/alembic/versions/6cfd93685f71_initial_schema.py)
* **Revision ID**: `6cfd93685f71`
* **Down Revision**: `None` (Baseline initial revision)
* **Creation Timestamp**: `2026-09-20 11:14:04`
* **Target Database URL**: `postgresql://postgres:postgres@localhost:5433/curio_db` (Development database)
* **Target Metadata**: `Base.metadata` from [`backend/app/db/base.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/db/base.py)

---

## 2. Tables & Schema Detected

All 7 application models were successfully detected by Alembic autogenerate:

| Table Name | Model Class | Primary Key | Foreign Keys & Cascade Rules | Key Columns & Types |
| :--- | :--- | :--- | :--- | :--- |
| **`documents`** | `Document` | `id` (UUID) | *None* | `filename` (String), `file_size` (Integer), `mime_type` (String), `created_at` (DateTime TZ) |
| **`users`** | `User` | `id` (UUID) | *None* | `email` (String, unique indexed), `created_at` (DateTime TZ) |
| **`sessions`** | `Session` | `id` (UUID) | `document_id -> documents.id` (`SET NULL`)<br>`user_id -> users.id` (`CASCADE`) | `topic` (String), `source_type` (String), `status` (String), `created_at`, `last_active_at`, `ended_at` |
| **`messages`** | `Message` | `id` (UUID) | `session_id -> sessions.id` (`CASCADE`) | `sender` (String), `content` (Text), `input_type` (String), `created_at` (DateTime TZ) |
| **`session_reports`** | `SessionReport` | `session_id` (UUID) | `session_id -> sessions.id` (`CASCADE`) | `understanding_score` (Float), `mastery_level` (String), 8 JSON fields (`strengths`, `learning_gaps`, `roadmap`, etc.) |
| **`session_states`** | `SessionState` | `session_id` (UUID) | `session_id -> sessions.id` (`CASCADE`) | `current_mode` (String), `difficulty` (Integer), `confidence` (Float), `active_concept` (String), `unresolved_misconceptions` (JSON), `mastered_concepts` (JSON) |
| **`turn_evaluations`** | `TurnEvaluation` | `message_id` (UUID) | `message_id -> messages.id` (`CASCADE`) | `correctness`, `clarity`, `completeness`, `depth`, `relevance`, `stuck_probability` (Floats), `misconceptions` (JSON), `missing_concepts` (JSON) |

---

## 3. Structural & Operational Integrity

### a. Dependency-Aware Creation (`upgrade`)
The `upgrade()` routine constructs tables in exact topological order:
```text
documents, users
      │
      ▼
   sessions
      │
      ├───────────────────┬───────────────────┐
      ▼                   ▼                   ▼
   messages        session_reports     session_states
      │
      ▼
turn_evaluations
```
Because parents (`users`, `documents`, `sessions`, `messages`) are created prior to dependent children, foreign key constraints compile without error.

### b. Safe Clean Reversal (`downgrade`)
The `downgrade()` routine strictly inverts the order:
1. Drops `turn_evaluations`
2. Drops `session_states`
3. Drops `session_reports`
4. Drops `messages`
5. Drops `sessions`
6. Drops `users`
7. Drops `documents`

All indexes created in `upgrade()` have corresponding `drop_index()` calls prior to table deletion in `downgrade()`.

---

## 4. Potential Concerns & Observations

1. **JSON vs. JSONB Storage**:
   - **Observation**: Models use `sa.JSON`, compiling to PostgreSQL's native `json` type (textual JSON).
   - **Impact**: Fully functional for reading and writing dictionaries/lists. If high-performance indexing of nested JSON properties or GIN indexes is required in the future, fields can be migrated to `sa.dialects.postgresql.JSONB`.
   - **Action**: No immediate blocker; safe for baseline.

2. **Vector Extension & Embeddings**:
   - **Observation**: While `init-databases.sh` activates `CREATE EXTENSION IF NOT EXISTS vector;` in PostgreSQL, the `Document` SQLAlchemy model currently does not declare a `Vector` column.
   - **Impact**: Alembic did not generate a vector column or extension dependency.
   - **Action**: When pgvector document chunk embeddings are integrated into the relational database, a dedicated migration (`add_document_embeddings`) can be generated.

3. **User Authentication Columns**:
   - **Observation**: `User` model currently declares `id`, `email`, and `created_at`, but has no `password_hash` column.
   - **Impact**: If backend authentication requires password storage, a password column must be added to the ORM model and migrated before enabling auth routes.

4. **Enum Columns Stored as Strings**:
   - **Observation**: `current_mode`, `recommended_strategy`, and `input_type` are stored as `sa.String()` rather than PostgreSQL native enum types (`CREATE TYPE ... AS ENUM`).
   - **Impact**: Prevents database migration friction when application enums evolve; application-level validation in Pydantic enforces valid values.

---

## 5. Test Suite Verification

Pytest was executed following migration generation to ensure zero regressions:
```powershell
& 'backend/.venv/Scripts/python.exe' -m pytest backend/tests -v
```

### Results:
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

======================= 46 passed, 60 warnings in 1.62s =======================
```

---

## 6. Safety Confirmation & Next Step Guidance

* **Current State**: Migration file `6cfd93685f71_initial_schema.py` is staged on disk in `backend/alembic/versions/`.
* **Database State**: `curio_db` remains empty with zero tables created.
* **When Ready to Apply**:
  To provision the physical tables in development:
  ```bash
  alembic -c backend/alembic.ini upgrade head
  ```
  And to provision the physical tables in the test database:
  ```bash
  TEST_DATABASE_URL=... alembic -c backend/alembic.ini upgrade head
  ```
