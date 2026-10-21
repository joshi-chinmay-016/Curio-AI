# Supabase Connection Validation Report — Curio AI

**Date:** 2026-10-11  
**Status:** Partial — Awaiting Supabase Connection Details  
**Task:** Final Supabase Connection Validation Before Migration

---

## 1. Current Backend Settings Resolution

### Configuration Check (Local Environment)

| Setting | Value (Masked) |
|---------|----------------|
| `DATABASE_URL` configured | ✅ Yes |
| Resolved URL | `postgresql://postgres:***@localhost:5433/curio_db` |
| `TEST_DATABASE_URL` configured | ✅ Yes |
| Resolved Test URL | `postgresql://postgres:***@localhost:5433/curio_test_db` |

**Finding:** Both URLs currently point to **local Docker PostgreSQL** (port 5433), not Supabase.

---

## 2. Alembic Migration Head Verification

```bash
alembic heads
```

**Output:** `6b4da17ad0d5 (head)`

**Confirmed:** Current migration head is `6b4da17ad0d5` — includes:
- ✅ Full schema (14 tables)
- ✅ `vector` extension creation (raw SQL in migration)
- ✅ `embedding_vector vector(1536)` column on `document_chunks`
- ✅ HNSW index `ix_document_chunks_embedding_vector_hnsw`

---

## 3. TEST_DATABASE_URL Isolation Confirmed

- `TEST_DATABASE_URL` → `curio_test_db` on local Docker (port 5433)
- **Unaffected** by any `DATABASE_URL` changes for Supabase
- Safety validation in `settings.validate_test_database_url()` will reject any Supabase URL lacking `'test'` in database name

---

## 4. Pending: Supabase Connectivity Validation

**Required from developer:** Supabase connection string from Dashboard → Settings → Database → Connection string (URI format).

**Expected format:**
```
postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres?sslmode=require
```

**Once provided, will execute:**

### 4.1 Read-Only Connectivity Test
```bash
export DATABASE_URL="<supabase-connection-string>"
python -c "
from backend.app.core.config import settings
from sqlalchemy import create_engine, text
print('Target (masked):', settings.mask_database_url(settings.get_database_url()))
engine = create_engine(settings.get_database_url())
with engine.connect() as conn:
    print('SELECT 1:', conn.execute(text('SELECT 1')).scalar())
    print('DB name:', conn.execute(text('SELECT current_database()')).scalar())
    print('Version:', conn.execute(text('SELECT version()')).scalar()[:80])
"
```

### 4.2 Target Database Alembic Revision Check
```bash
alembic current
```

### 4.3 Target Database Emptiness Check
```bash
psql "$DATABASE_URL" -c "
SELECT schemaname, relname as table_name, n_live_tup as row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY relname;
"
```

---

## 5. Safety Constraints Status

| Constraint | Status |
|------------|--------|
| No `.env` modifications | ✅ Compliant |
| No Alembic migrations run | ✅ Compliant |
| No DDL executed | ✅ Compliant |
| No credentials printed | ✅ Compliant |
| Local databases untouched | ✅ Compliant |
| `TEST_DATABASE_URL` isolated | ✅ Compliant |

---

## 6. Next Steps

1. **Developer provides Supabase connection string** (URI format with `?sslmode=require`)
2. **Run validation commands** (read-only)
3. **Confirm:**
   - Connectivity successful
   - Target database name (expected: `postgres`)
   - Alembic revision (expected: empty/none on fresh Supabase)
   - No existing tables or data
4. **Explicit approval** → proceed with `alembic upgrade head`

---

**Awaiting Supabase connection details to complete validation.**