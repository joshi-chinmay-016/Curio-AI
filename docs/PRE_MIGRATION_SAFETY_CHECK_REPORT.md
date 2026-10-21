# Pre-Migration Safety Check Report — Curio AI

**Date**: 2026-10-11  
**Target**: Supabase Session Pooler (`aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres`)  
**Status**: Conditional GO — requires pgvector extension

---

## 1. Alembic Configuration

| File | Finding |
|------|---------|
| `alembic/env.py` | Uses `settings.get_database_url()` (→ `DATABASE_URL` → Supabase) by default. Only switches to `get_test_database_url()` when `-x db=test` or `ALEMBIC_TARGET_DB=test` is set. ✅ |
| `alembic.ini` | `sqlalchemy.url` empty; dynamically populated by `env.py`. ✅ |
| `config.py` | `get_database_url()` returns `DATABASE_URL` from `.env` (Supabase). `get_test_database_url()` validates `TEST_DATABASE_URL` (local `curio_test_db`) with strict safety checks. ✅ |

---

## 2. Migration Chain Integrity

- **Total revisions**: 14
- **Head revision**: `6b4da17ad0d5` (only one head) ✅
- **Chain**: Linear from `6cfd93685f71` (initial_schema) → `6b4da17ad0d5` (add_native_vector_column). No branches. ✅

```
6cfd93685f71 (initial_schema)
  → a1b2c3d4e5f6 (phase3_evaluation_fields)
    → 84274ca763eb (teacher_mode_state_fields)
      → b4e440204004 (user_authentication_fields)
        → d9640bb3d3cf (session_state_learning_persistence)
          → d3c4dafb5201 (user_concept_progress)
            → 602e5c00140b (teacher_intervention_log)
              → 7a8b9c0d1e2f (turn_assessments)
                → 8b9c0d1e2f3a (report_versions + backfill)
                  → a1b2c3d4e5f7 (report_evidence_snapshots)
                    → 9b3012f5a0bb (drop_evidence_snapshot_id)
                      → add_document_ownership (documents user_id + status)
                        → d05335a73981 (document_chunks table)
                          → 6b4da17ad0d5 (native vector column + HNSW index)  ← HEAD
```

---

## 3. Target Database for `alembic upgrade head`

- Default invocation (`alembic upgrade head`) → uses `DATABASE_URL` → **Supabase Session Pooler** (`aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres`). ✅
- Test invocation (`alembic -x db=test upgrade head`) → uses `TEST_DATABASE_URL` → local `curio_test_db`. ✅

---

## 4. Destructive Operations & Data Changes

| Migration | Operation | Risk |
|-----------|-----------|------|
| `add_document_ownership_and_status` | `UPDATE documents SET user_id = ...` + `DELETE` for orphaned docs | Medium — runs data mutation; safe logic but executes on first run against Supabase |
| `add_report_versions` | `INSERT ... SELECT ... FROM session_reports` (backfill) | Low — expected idempotent backfill |
| Others | `ADD COLUMN`, `CREATE TABLE`, `CREATE INDEX`, `CREATE UNIQUE CONSTRAINT` | None |

**No `DROP TABLE`, `DROP COLUMN` (upgrade path), or `TRUNCATE` in forward direction.**

---

## 5. Required PostgreSQL Extensions

| Extension | Used By | Status |
|-----------|---------|--------|
| `vector` (pgvector) | `6b4da17ad0d5`: `vector(1536)` type, `hnsw` index with `vector_cosine_ops` | ⚠️ **MISSING** — No `CREATE EXTENSION IF NOT EXISTS vector` in any migration. Will fail on fresh Supabase DB unless pre-installed. |
| `uuid-ossp` / `gen_random_uuid()` | Multiple migrations use `gen_random_uuid()` | Usually available by default in Supabase; verify. |

---

## 6. Phase 1–5 Schema Coverage

| Phase | Tables / Structures Created | Status |
|-------|-----------------------------|--------|
| 1 (Core) | users, documents, sessions, messages, session_states, turn_evaluations, session_reports | ✅ |
| 2 (Auth) | users: hashed_password, is_active, updated_at | ✅ |
| 3 (Teacher/Eval) | teacher_mode_state_fields, phase3_evaluation_fields, turn_assessments, user_concept_progress, teacher_intervention_logs | ✅ |
| 4 (Reports/Versions) | session_report_versions, report_evidence_snapshots (created then dropped), document_ownership (user_id, status, storage_path, etc.) | ✅ |
| 5 (RAG/Vector) | document_chunks, embedding_vector (native `vector(1536)`), HNSW index | ✅ |

All FKs, indexes, unique constraints, and JSONB columns present.

---

## 7. Test Database Isolation

- `TEST_DATABASE_URL` = `postgresql://postgres:postgres@localhost:5433/curio_test_db` (local). ✅
- `config.validate_test_database_url()` enforces: contains `test`, not `prod`/`production`, not same as `DATABASE_URL`, not system DB. ✅
- `conftest.py` uses `settings.get_test_database_url()` — fails fast if invalid. ✅
- No test fixture or CI config points to Supabase. ✅

---

## 8. Risks & Blockers

| # | Risk | Severity | Recommendation |
|---|------|----------|----------------|
| 1 | **pgvector extension not created** — Migration `6b4da17ad0d5` uses `vector(1536)` and `hnsw` index but no `CREATE EXTENSION vector`. | **Blocker** | Add `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` at start of `6b4da17ad0d5` upgrade, or run manually in Supabase before migration. |
| 2 | **Data mutation in `add_document_ownership_and_status`** — Updates/deletes orphaned documents on first run. | Medium | Review logic; ensure a valid `users` row exists before running (migration fetches first user). On fresh DB, no docs exist → safe. |
| 3 | **Supabase Session Pooler limitations** — Pooling mode (transaction/statement) may interfere with long-running migrations or `CREATE INDEX CONCURRENTLY` (not used here). | Low | Monitor; HNSW index creation is not concurrent but runs in single transaction. |
| 4 | **No `uuid-ossp` extension check** — `gen_random_uuid()` used widely. | Low | Usually present in Supabase; verify with `SELECT * FROM pg_extension WHERE extname = 'uuid-ossp'`. |

---

## 9. Verdict

**Conditional GO** — Migration chain is sound, linear, and targets Supabase correctly. **Primary blocker**: `pgvector` extension must exist before running `alembic upgrade head`. Add `CREATE EXTENSION IF NOT EXISTS vector` to migration `6b4da17ad0d5` or enable in Supabase dashboard first. Test isolation is robust.