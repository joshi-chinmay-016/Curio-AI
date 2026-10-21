# Supabase Migration Preflight Report — Curio AI

**Date:** 2026-10-11  
**Status:** Preflight Complete — Awaiting Approval  
**Task:** Supabase Migration Preflight for Schema-Only Migration

---

## 1. Configuration Interaction Summary

### `get_database_url()` Priority (`backend/app/core/config.py:81-84`)

```python
def get_database_url(self) -> str:
    if self.DATABASE_URL:           # ← 1st: explicit DATABASE_URL (from .env)
        return self.DATABASE_URL
    return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
```

| Variable | Role | Precedence |
|----------|------|------------|
| `DATABASE_URL` | **Full connection string** — takes absolute precedence | 1st |
| `POSTGRES_SERVER`/`USER`/`PASSWORD`/`DB`/`PORT` | Fallback components — used only if `DATABASE_URL` is empty | 2nd |

**Current `.env` values:** `DATABASE_URL` is explicitly set → component variables are **ignored** for the dev database.

---

## 2. Alembic Target Database Selection (`backend/alembic/env.py:52-56`)

```python
x_args = context.get_x_argument(as_dictionary=True)
if x_args.get("db") == "test" or os.getenv("ALEMBIC_TARGET_DB") == "test":
    target_url = settings.get_test_database_url()
else:
    target_url = settings.get_database_url()
```

| Mechanism | Syntax | How it works |
|-----------|--------|--------------|
| **CLI `-x` argument** | `alembic -x db=test upgrade head` | `context.get_x_argument()` parses `-x key=value` |
| **Environment variable** | `ALEMBIC_TARGET_DB=test alembic upgrade head` | `os.getenv("ALEMBIC_TARGET_DB")` |

**They are NOT equivalent** — both are checked independently; either works. The `-x` argument is preferred for CI/CD clarity.

---

## 3. PostgreSQL URL Format for SQLAlchemy + psycopg2

**Required format:**
```
postgresql://<user>:<password>@<host>:<port>/<database>
```

**Supabase-specific notes:**
- Host: `db.<project-ref>.supabase.co` (pooler) or `<project-ref>.supabase.co` (direct)
- Port: `5432` (direct) or `6543` (pooler)
- SSL: Supabase requires SSL — add `?sslmode=require` to URL
- Example: `postgresql://postgres:<password>@db.xxx.supabase.co:5432/postgres?sslmode=require`

**Driver:** `psycopg2` (default for `postgresql://` scheme in SQLAlchemy)

---

## 4. Safest Configuration Strategy

| Database | Configuration Approach |
|----------|------------------------|
| **Shared Dev (Supabase)** | Set `DATABASE_URL` in deployment env / Supabase dashboard → `postgresql://...@db.xxx.supabase.co:5432/postgres?sslmode=require` |
| **Local Test (`curio_test_db`)** | Keep `TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/curio_test_db` in local `.env` — **unchanged** |

**Key principle:** `TEST_DATABASE_URL` remains pointing to local Docker; only `DATABASE_URL` changes for Supabase.

---

## 5. Migration Chain Verification

**Current head:** `6b4da17ad0d5` (15 revisions total)

**Critical migrations included:**

| Revision | Purpose |
|----------|---------|
| `6cfd93685f71` | Initial schema (13 tables) |
| `d05335a73981` | `document_chunks` table |
| `6b4da17ad0d5` | **pgvector native column + HNSW index** |

**Applying `alembic upgrade head` to empty Supabase DB will:**

1. ✅ Create all 14 tables with FKs, indexes, constraints
2. ✅ Create `vector` extension (via migration `6b4da17ad0d5` raw SQL)
3. ✅ Add `embedding_vector vector(1536)` column
4. ✅ Create HNSW index `ix_document_chunks_embedding_vector_hnsw`

**No manual DDL required** — migration chain is complete and self-contained.

---

## 6. Supabase Prerequisites (Confirm Before Migration)

| Requirement | Status | Action |
|-------------|--------|--------|
| `pgvector` extension | ⚠️ **Must enable** | Run `CREATE EXTENSION IF NOT EXISTS vector;` in Supabase SQL Editor (requires `postgres` superuser) |
| `CREATE` privilege on target database | ✅ Default for `postgres` user | Verify Supabase project owner can create tables |
| SSL/TLS connection | ✅ Required | Ensure `?sslmode=require` in `DATABASE_URL` |
| Connection pooling (PgBouncer) | Optional | If using pooler (port 6543), ensure `prepared_statements=False` in SQLAlchemy engine |

---

## 7. Preflight Commands (Read-Only / Safe)

**Run from `backend/` directory:**

```bash
# 1. Test connectivity (no DB changes)
# Replace with your actual Supabase DATABASE_URL
export DATABASE_URL="postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres?sslmode=require"
python -c "
from backend.app.core.config import settings
print('Resolved URL:', settings.mask_database_url(settings.get_database_url()))
from sqlalchemy import create_engine, text
engine = create_engine(settings.get_database_url())
with engine.connect() as conn:
    result = conn.execute(text('SELECT version()'))
    print('Connected:', result.scalar()[:80])
"

# 2. Verify target database name & current Alembic revision (read-only)
alembic current

# 3. Show pending migrations (dry-run)
alembic upgrade head --sql > /dev/null && echo "Migration SQL generated successfully"

# 4. After approval — apply migrations (DO NOT RUN YET)
# alembic upgrade head

# 5. Verify schema & vector index post-migration
# psql "$DATABASE_URL" -c "\dt"
# psql "$DATABASE_URL" -c "\d document_chunks"
# psql "$DATABASE_URL" -c "SELECT * FROM alembic_version;"
```

---

## 8. Exact Recommended Migration Sequence (After Approval)

```bash
# 1. Enable pgvector in Supabase (one-time, via SQL Editor)
# CREATE EXTENSION IF NOT EXISTS vector;

# 2. Set DATABASE_URL in your environment (do not commit)
export DATABASE_URL="postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres?sslmode=require"

# 3. Verify connectivity
python -c "from backend.app.core.config import settings; from sqlalchemy import create_engine, text; e=create_engine(settings.get_database_url()); print(e.connect().execute(text('SELECT 1')).scalar())"

# 4. Apply migrations (dev database)
alembic upgrade head

# 5. Verify
alembic current
psql "$DATABASE_URL" -c "\d document_chunks" | grep -E "embedding_vector|hnsw"
```

---

## 9. Safety Constraints Checklist

- [ ] `TEST_DATABASE_URL` unchanged (points to local `curio_test_db`)
- [ ] No `.env` modifications committed
- [ ] Supabase credentials not printed or logged
- [ ] Local `curio_db` / `curio_test_db` untouched
- [ ] No second database assumed in Supabase (uses single `postgres` DB)

---

**Ready for approval to proceed with migration.**