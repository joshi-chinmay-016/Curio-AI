# Pre-Migration Database Audit Report — Curio AI

**Date:** 2026-10-11  
**Status:** Read-Only Audit Complete  
**Task:** Pre-Migration Database Audit for Supabase PostgreSQL Migration

---

## 1. Database Configuration Module & Environment Variables

### Configuration File
**Path:** `backend/app/core/config.py`  
**Class:** `Settings` (extends `pydantic_settings.BaseSettings`)

### Environment Variable Loading Order
1. Root `.env` (repo root)
2. `backend/.env`
3. Local `.env` (current working directory)

### Key Environment Variables (from `backend/.env` — secrets redacted)

| Variable | Value |
|----------|-------|
| `POSTGRES_SERVER` | `localhost` |
| `POSTGRES_USER` | `postgres` |
| `POSTGRES_PASSWORD` | `***` |
| `POSTGRES_DB` | `curio_db` |
| `POSTGRES_PORT` | `5433` |
| `DATABASE_URL` | `postgresql://postgres:***@localhost:5433/curio_db` |
| `TEST_DATABASE_URL` | `postgresql://postgres:***@localhost:5433/curio_test_db` |

### SQLAlchemy Driver & Connection Settings
- **Driver:** `postgresql+psycopg2` (via SQLAlchemy's default PostgreSQL dialect)
- **Host:** `localhost:5433` (Docker-mapped port)
- **Pool:** `NullPool` for Alembic migrations; default pool for application

---

## 2. Source Database Verification

### Development Database: `curio_db`
- **Verified by:** `POSTGRES_DB=curio_db` in `.env` → `settings.get_database_url()` → used by default in `alembic/env.py` when `ALEMBIC_TARGET_DB != 'test'`
- **Docker Compose:** `POSTGRES_DB: curio_db` with port mapping `5433:5432`

### Test Database: `curio_test_db`
- **Verified by:** `TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/curio_test_db` in `.env`
- **Safety Validation:** `settings.validate_test_database_url()` enforces:
  - Must not equal `DATABASE_URL`
  - Must not be system DB (`postgres`, `template1`)
  - Must not be app DB (`curio_db`)
  - Must contain `'test'` in name
  - Must not contain production keywords (`prod`, `production`, `live`)

---

## 3. Database Status

| Database | Exists | Alembic Version | Tables | Row Counts | pgvector Extension |
|----------|--------|-----------------|--------|------------|-------------------|
| `curio_db` | ✅ Yes | `6b4da17ad0d5` (head) | 14 tables | All 0 rows | ✅ v0.8.7 |
| `curio_test_db` | ✅ Yes | `6b4da17ad0d5` (head) | 14 tables | All 0 rows | ✅ v0.8.7 |

**Both databases are empty (no user data)** and at the latest migration head.

---

## 4. Alembic Configuration

**Config File:** `backend/alembic.ini`
- `script_location = %(here)s/alembic`
- `sqlalchemy.url` dynamically set in `alembic/env.py` from `settings.get_database_url()` or `settings.get_test_database_url()`

**Migration Head:** `6b4da17ad0d5` (single head, no branches)

**Applied Revision (both DBs):** `6b4da17ad0d5` — matches head

**Migration History:** 15 revisions from `6cfd93685f71` (initial_schema) to `6b4da17ad0d5` (add_native_vector_column)

---

## 5. Schema Inventory (14 Tables)

| Table | Primary Key | Foreign Keys | Notable Indexes |
|-------|-------------|--------------|-----------------|
| `users` | `id` (UUID) | — | `ix_users_email` (unique) |
| `sessions` | `id` (UUID) | `user_id→users`, `document_id→documents` | `ix_sessions_user_id`, `ix_sessions_topic` |
| `session_states` | `session_id` (UUID, FK→sessions) | `session_id→sessions` (CASCADE) | — |
| `messages` | `id` (UUID) | `session_id→sessions` (CASCADE) | `ix_messages_session_id`, `ix_messages_created_at` |
| `turn_evaluations` | `message_id` (UUID, FK→messages) | `message_id→messages` (CASCADE) | — |
| `documents` | `id` (UUID) | `user_id→users` (CASCADE) | `ix_documents_user_id` |
| `document_chunks` | `id` (UUID) | `document_id→documents` (CASCADE) | `ix_document_chunks_document_id`, **`ix_document_chunks_embedding_vector_hnsw` (HNSW)**, `uq_document_chunk_index` |
| `session_reports` | `session_id` (UUID, FK→sessions) | `session_id→sessions` (CASCADE) | — |
| `session_report_versions` | `id` (UUID) | `session_id→sessions` (CASCADE) | `uq_session_report_version` (session_id, version_number) |
| `report_evidence_snapshots` | `id` (UUID) | `report_version_id→session_report_versions` (RESTRICT) | `uq_report_evidence_snapshot_version` |
| `user_concept_progress` | `(user_id, concept)` | `user_id→users` (CASCADE) | `uq_user_concept` |
| `teacher_intervention_logs` | `id` (UUID) | `session_id→sessions`, `user_id→users` (both CASCADE) | `ix_teacher_intervention_logs_session_id`, `ix_teacher_intervention_logs_user_id` |
| `turn_assessments` | `id` (UUID) | `message_id→messages`, `session_id→sessions`, `user_id→users` (all CASCADE) | `ix_turn_assessments_session_id_created_at`, `ix_turn_assessments_user_id_session_id`, `turn_assessments_message_id_key` (unique) |
| `alembic_version` | `version_num` | — | — |

**Total Foreign Keys:** 16 (all validated)

---

## 6. pgvector / Phase 5 RAG Schema Status

| Component | Status | Details |
|-----------|--------|---------|
| `vector` extension | ✅ Installed | v0.8.7 on both databases |
| `embedding_vector` column | ✅ Present | `vector(1536)` on `document_chunks` |
| Legacy `embedding` column | ✅ Present | `TEXT` (JSON fallback) |
| HNSW Index | ✅ Created | `ix_document_chunks_embedding_vector_hnsw` USING `hnsw (embedding_vector vector_cosine_ops)` WITH `(m=16, ef_construction=64)` |
| Vector Dimensions | ✅ 1536 | Matches `EMBEDDING_DIMENSIONS=1536` in config (text-embedding-3-small) |

---

## 7. Test Database Configuration & Risk Assessment

### Configuration
- Dedicated `curio_test_db` on same PostgreSQL instance (port 5433)

### Safety Mechanisms in Place
1. ✅ `TEST_DATABASE_URL` explicitly configured in `.env`
2. ✅ `settings.get_test_database_url()` validates safety invariants
3. ✅ `conftest.py` fixtures use `NullPool` + transaction rollback per test
4. ✅ `Base.metadata.create_all()` runs on test DB at session start
5. ✅ Test markers: `@pytest.mark.db_integration` required for live DB tests

### Risk of Tests Modifying Shared Database: **LOW**
- Tests use isolated transactions with automatic rollback
- Test DB is separate from dev DB (`curio_test_db` vs `curio_db`)
- Validation prevents accidental targeting of `curio_db` or production DBs
- **However:** Both DBs share the same PostgreSQL container/instance — resource contention possible under heavy parallel test loads

---

## 8. .gitignore Verification

**Excluded Patterns (from `.gitignore`):**
- `.env`, `.env.*` (except `.env.example`)
- `backend/.env`, `backend/.env/*`
- All virtual environments, cache dirs, build artifacts

**Status:** ✅ Properly excludes secrets and database artifacts

---

## 9. Issues to Resolve Before Migration

| # | Issue | Severity | Recommendation |
|---|-------|----------|----------------|
| 1 | **Port discrepancy** | Medium | `.env` uses `POSTGRES_PORT=5433` (Docker host port), but `.env.example` and Docker Compose internal port is `5432`. Ensure Supabase connection uses correct port (typically `5432`). |
| 2 | **Single PostgreSQL instance for dev + test** | Low | Consider separate Supabase projects or at minimum separate databases with isolated roles for production migration. |
| 3 | **No data in source DBs** | Info | Migration will be schema-only; verify Supabase has `pgvector` extension available (Supabase supports it natively). |
| 4 | **Alembic `sqlalchemy.url` empty in ini** | Info | By design — dynamically populated. Ensure Supabase connection string is set via env vars in target environment. |
| 5 | **HNSW index parameters** | Low | Current `m=16, ef_construction=64` are defaults; validate performance at scale on Supabase. |

---

## 10. Recommended Next Step

### Safest Path Forward

1. **Provision Supabase Project** — Create a new Supabase project (or use existing) with two databases: `curio_db` (production) and `curio_test_db` (staging/test), or use separate Supabase projects for complete isolation.

2. **Enable pgvector on Supabase** — Run `CREATE EXTENSION IF NOT EXISTS vector;` in both target databases (Supabase dashboard → SQL Editor).

3. **Configure Target Environment Variables** — Set `DATABASE_URL` and `TEST_DATABASE_URL` in Supabase/deployment environment pointing to the new databases (use `postgresql://` with Supabase host, port 5432, password from Supabase dashboard).

4. **Run Alembic Migrations on Target** — From backend directory:
   ```bash
   alembic upgrade head          # For production DB
   alembic -x db=test upgrade head  # For test DB
   ```

5. **Verify Schema Parity** — Run `\dt`, `\d document_chunks`, and `SELECT * FROM alembic_version;` on both Supabase databases.

6. **Data Migration (if needed)** — Since current DBs are empty, no data migration required. If data existed, use `pg_dump`/`pg_restore` with `--data-only` after schema is in place.

7. **Update CI/CD** — Ensure test pipeline sets `TEST_DATABASE_URL` to Supabase test DB and runs migrations before test suite.

---

**Awaiting approval to proceed with migration steps.**