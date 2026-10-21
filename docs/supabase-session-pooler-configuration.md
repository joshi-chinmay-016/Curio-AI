# Supabase Session Pooler Configuration Guide — Curio AI

**Date:** 2026-10-11  
**Status:** Configuration Instructions — Awaiting Local Setup  
**Task:** Configure backend for Supabase Session Pooler connectivity (validation only)

---

## 1. Current Configuration Behavior

### `DATABASE_URL` Resolution Priority (`backend/app/core/config.py:81-84`)

```python
def get_database_url(self) -> str:
    if self.DATABASE_URL:           # ← 1st: explicit DATABASE_URL (from .env)
        return self.DATABASE_URL
    return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
```

| Variable | Role | Precedence |
|----------|------|------------|
| `DATABASE_URL` | Full connection string — **absolute precedence** | 1st |
| `POSTGRES_*` components | Fallback — used **only if `DATABASE_URL` is empty** | 2nd |

**Current `backend/.env`** has `DATABASE_URL` explicitly set → component variables are **ignored** for dev database.

---

## 2. TEST_DATABASE_URL Isolation

- **Preserved as-is** in `backend/.env`:
  ```env
  TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/curio_test_db
  ```
- Safety validation (`validate_test_database_url`) will **reject** any Supabase URL (lacks `'test'` in database name)
- Local test database remains completely unaffected

---

## 3. Exact Configuration Steps

### 3.1 Get Supabase Session Pooler Details from Dashboard

Go to: **Supabase Dashboard → Settings → Database → Connection pooling**

Note these values:

| Field | Your Value |
|-------|------------|
| **Host** | `aws-0-<region>.pooler.supabase.com` |
| **Port** | `6543` (Session pooler) |
| **Database** | `postgres` |
| **User** | `postgres.<project-ref>` (note the prefix) |
| **Password** | *your database password* |

### 3.2 URL-Encode the Password

Special characters must be percent-encoded:

| Char | Encoded |
|------|---------|
| `@` | `%40` |
| `#` | `%23` |
| `%` | `%25` |
| `:` | `%3A` |
| `/` | `%2F` |
| `?` | `%3F` |

**Example:** `p@ss#word` → `p%40ss%23word`

### 3.3 Construct the Session Pooler URL

```
postgresql://<USER>:<ENCODED_PASSWORD>@<HOST>:6543/<DATABASE>?sslmode=require
```

**Example:**
```
postgresql://postgres.abcdefghijklmnop:MyP%40ss%23word@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

### 3.4 Update `backend/.env` (Local Only — Do Not Commit)

**Edit `backend/.env` and replace only the `DATABASE_URL` line:**

```env
# Replace this line:
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/curio_db

# With your Session Pooler URL (password already encoded):
DATABASE_URL=postgresql://postgres.<project-ref>:<ENCODED_PASSWORD>@<HOST>:6543/postgres?sslmode=require

# Keep TEST_DATABASE_URL exactly as-is:
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/curio_test_db
```

### 3.5 Verify Configuration (After Edit)

```bash
cd C:\Users\Vishal S Naik\MyProjects\Curio-AI\backend
python -c "
from backend.app.core.config import settings
print('Dev DB (masked):', settings.mask_database_url(settings.get_database_url()))
print('Test DB (masked):', settings.mask_database_url(settings.get_test_database_url()))
"
```

**Expected output:**
```
Dev DB (masked): postgresql://postgres.<project-ref>:***@aws-0-xxx.pooler.supabase.com:6543/postgres
Test DB (masked): postgresql://postgres:***@localhost:5433/curio_test_db
```

---

## 4. Safety Checklist (Before Proceeding)

- [ ] `DATABASE_URL` uses **Session Pooler** (port 6543), not direct connection (port 5432)
- [ ] Password is **URL-encoded** in the connection string
- [ ] `?sslmode=require` is appended
- [ ] `TEST_DATABASE_URL` **unchanged** — still points to local `curio_test_db`
- [ ] No credentials committed to Git (`.env` is in `.gitignore`)
- [ ] No migrations run yet

---

## 5. Next Steps After Local Setup

1. You edit `backend/.env` locally with your Session Pooler URL
2. Run read-only connectivity validation (`SELECT 1`, check DB name, Alembic revision)
3. Confirm target DB is empty
4. Explicit approval → `alembic upgrade head`

---

**No changes made. Awaiting your local configuration.**