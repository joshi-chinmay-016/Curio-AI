# Final Migration Code Review — Curio AI → Supabase

**Date**: 2026-10-11  
**Target**: Supabase Session Pooler (`aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres`)  
**PostgreSQL**: 17.11  
**pgvector**: 0.8.2 (pre-installed)  
**Alembic Head**: `6b4da17ad0d5` (14 revisions, single head)  
**Database State**: Empty  

---

## 1. Document Ownership Migration (`add_document_ownership_and_status`)

### Behavior on Empty Target DB
- `orphaned_count = 0` → `if` block skipped
- `user_id` altered to `NOT NULL` + FK added directly
- **No `UPDATE` or `DELETE` executed**

### Assumptions & Risks
| Assumption | Reality in Supabase | Risk |
|------------|---------------------|------|
| `users` table exists before this migration | ✅ Created in `initial_schema` (rev `6cfd93685f71`) | None |
| At least one user exists if docs need migration | Fresh DB has no docs → skipped | None |
| `DELETE` only if no users exist | Only triggers if docs exist but no users | Low (shouldn't occur) |

**Verdict**: ✅ Safe for empty target.

---

## 2. Dependency Order, Foreign Keys, Indexes, Constraints

**Chain verified linear** (14 revisions, single head `6b4da17ad0d5`):

| Revision | Creates / Modifies | FKs Added | Indexes / Constraints |
|----------|-------------------|-----------|----------------------|
| `6cfd93685f71` | 7 core tables | users→sessions, sessions→documents, sessions→messages, sessions→session_states, sessions→session_reports, messages→turn_evaluations | PKs, unique email, 15+ indexes |
| `a1b2c3d4e5f6` | session_reports cols | — | — |
| `84274ca763eb` | session_states cols | — | — |
| `b4e440204004` | users auth cols | — | — |
| `d9640bb3d3cf` | session_states cols | — | — |
| `d3c4dafb5201` | user_concept_progress | user→users (PK) | Unique (user_id, concept) |
| `602e5c00140b` | teacher_intervention_logs | session→sessions, user→users | Indexes on session_id, user_id |
| `7a8b9c0d1e2f` | turn_assessments | message→messages, session→sessions, user→users | Composite indexes |
| `8b9c0d1e2f3a` | session_report_versions | session→sessions | Composite indexes + backfill INSERT |
| `a1b2c3d4e5f7` | report_evidence_snapshots | report_version→session_report_versions | Unique + indexes |
| `9b3012f5a0bb` | drops snapshot FK/col | — | — |
| `add_document_ownership` | documents cols | user→users (after data fix) | Index on user_id |
| `d05335a73981` | document_chunks | document→documents | Unique (doc_id, chunk_idx), index on doc_id |
| `6b4da17ad0d5` | embedding_vector (vector) | — | HNSW index |

**All FKs reference existing tables. No circular dependencies. Order correct.**

---

## 3. Revision `6b4da17ad0d5` — pgvector Syntax Validation

```sql
-- Column addition
ALTER TABLE document_chunks ADD COLUMN embedding_vector TEXT;

-- Type conversion (handles NULL/empty from legacy `embedding` text column)
ALTER TABLE document_chunks 
ALTER COLUMN embedding_vector TYPE vector(1536) 
USING CASE 
    WHEN embedding IS NOT NULL AND embedding != '' 
    THEN embedding::vector 
    ELSE NULL 
END;

-- HNSW index
CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_vector_hnsw
ON document_chunks 
USING hnsw (embedding_vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Validation**:
- ✅ `vector(1536)` — valid pgvector 0.8.2 type
- ✅ `USING` clause with `::vector` cast — correct for text→vector conversion
- ✅ `hnsw` with `vector_cosine_ops` — supported in pgvector ≥0.5.0
- ✅ `m=16, ef_construction=64` — valid HNSW parameters
- ✅ `IF NOT EXISTS` — idempotent

**No syntax issues for PostgreSQL 17.11 + pgvector 0.8.2.**

---

## 4. Supabase PostgreSQL 17.11 / Session Pooler Risks

| Operation | Risk | Assessment |
|-----------|------|------------|
| `CREATE INDEX ... USING hnsw` | Long-running, locks table | Table empty → fast; no `CONCURRENTLY` but not needed |
| `ALTER COLUMN ... TYPE vector` | Rewrite table | Table empty → instant |
| `gen_random_uuid()` | Requires `uuid-ossp` or `pgcrypto` | Supabase includes `pgcrypto` by default; `gen_random_uuid()` available |
| Transaction pooling | Long transactions may timeout | All migrations use single transaction per revision; each is fast on empty DB |
| `ON CONFLICT` in backfill | Requires unique constraint | `uq_session_report_version` created before backfill ✅ |

**No blockers identified for Supabase 17.11 / Session Pooler.**

---

## 5. Migration Modifications Needed?

| Migration | Current State | Modification Needed? |
|-----------|---------------|---------------------|
| `6b4da17ad0d5` | No `CREATE EXTENSION vector` | **No** — extension already installed (v0.8.2). Adding `IF NOT EXISTS` would be defensive but not required. |
| Others | All DDL compatible | **No** |

**Recommendation**: Optional defensive improvement only — add `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` at start of `6b4da17ad0d5` upgrade for portability. Not a blocker.

---

## Summary

| Category | Status |
|----------|--------|
| Document ownership migration | ✅ Safe on empty DB |
| Dependency order / FKs / indexes | ✅ Correct |
| pgvector syntax (rev `6b4da17ad0d5`) | ✅ Valid for pgvector 0.8.2 |
| Supabase 17.11 / Session Pooler compatibility | ✅ No issues |
| Required modifications | ⚠️ Optional: add `CREATE EXTENSION IF NOT EXISTS vector` for defense |

---

## Final Recommendation

**APPROVED FOR EXECUTION** — No blockers. The migration chain is sound, targets the correct database, and will succeed on the empty Supabase instance with pgvector 0.8.2 pre-installed.

**Optional** (non-blocking): Add `CREATE EXTENSION IF NOT EXISTS vector` to `6b4da17ad0d5` for future portability.

**Ready to run**: `alembic upgrade head` (uses `DATABASE_URL` → Supabase).

---

## Related Reports

- [Pre-Migration Safety Check Report](./PRE_MIGRATION_SAFETY_CHECK_REPORT.md)
- [pgvector Availability Report](./PGVECTOR_AVAILABILITY_REPORT.md)
- [Supabase Connectivity Validation](./SUPABASE_VALIDATION_REPORT.md)