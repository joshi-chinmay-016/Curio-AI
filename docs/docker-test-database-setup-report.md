# Docker Test Database Setup & Initialization Report

## Executive Summary

This report documents the automated, safe provisioning configuration for a dedicated PostgreSQL test database (`curio_test_db`) alongside the primary development database (`curio_db`) using Docker Compose.

In accordance with safety requirements:
- No containers were started, and Docker Desktop was not launched.
- No live databases or volumes were created, modified, or deleted.
- No Alembic migrations were generated or applied.
- All application models and production settings remain untouched.
- All **46 unit tests** continue to pass cleanly.

---

## 1. Files Created and Modified

### a. Files Created
1. **[`scripts/init-databases.sh`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/scripts/init-databases.sh)**:
   - Shell script executed by PostgreSQL's entrypoint inside `/docker-entrypoint-initdb.d/`.
   - Idempotently creates `curio_db` and `curio_test_db` if they do not already exist.
   - Grants full privileges on both databases to the configured `POSTGRES_USER`.
   - Activates the `vector` extension on both databases if the `pgvector` extension is available.
   - Enforces LF line endings to guarantee compatibility with Linux containers running on Windows hosts.

2. **[` .gitattributes`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/.gitattributes)**:
   - Configures Git to enforce LF (`eol=lf`) line endings for all `*.sh` scripts, preventing Windows `\r\n` line endings from causing `/bin/bash^M: bad interpreter` execution failures inside containers.

### b. Files Modified
1. **[`docker-compose.yml`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docker-compose.yml)**:
   - Mounted `./scripts/init-databases.sh` into `/docker-entrypoint-initdb.d/init-databases.sh:ro` on the `db` service.
   - Configured as read-only (`:ro`) to prevent the container from altering the host script.

---

## 2. Initialization Behavior & Lifecycle

### a. Execution Timing
PostgreSQL official images (including `ankane/pgvector:latest`) inspect `/docker-entrypoint-initdb.d/` **only when the database cluster is initialized for the first time** (i.e. when `/var/lib/postgresql/data` is empty).

```text
docker-compose up -d db
       │
       ▼
Is /var/lib/postgresql/data empty?
       ├── YES (Fresh Volume):
       │     1. initdb initializes cluster
       │     2. Temporary PostgreSQL server starts
       │     3. POSTGRES_DB (curio_db) is created
       │     4. /docker-entrypoint-initdb.d/init-databases.sh executes:
       │        - Creates curio_test_db (if missing)
       │        - Ensures curio_db exists
       │        - Grants privileges to $POSTGRES_USER
       │        - Enables 'vector' extension on both databases
       │     5. Temporary server stops
       │     6. Main PostgreSQL daemon starts on port 5432
       │
       └── NO (Existing Volume):
             1. Skips /docker-entrypoint-initdb.d/ completely
             2. Starts PostgreSQL server immediately with existing cluster data
```

### b. Handling Pre-existing PostgreSQL Volumes
Because PostgreSQL intentionally skips initialization scripts if an existing volume is detected, developers who have previously run `docker-compose up -d db` have two options:

* **Option 1: Fresh Re-initialization (Clean Slate)**
  ```bash
  docker-compose down -v
  docker-compose up -d db
  ```
  *(Warning: `-v` destroys local development database data).*

* **Option 2: Non-Destructive In-Place Provisioning**
  If existing development data must be preserved, the developer can create `curio_test_db` directly on the running container:
  ```bash
  docker-compose exec db psql -U postgres -c "CREATE DATABASE curio_test_db;"
  docker-compose exec db psql -U postgres -d curio_test_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
  ```

---

## 3. Safety Considerations

| Invariant | Protection Strategy |
| :--- | :--- |
| **Non-Destructive** | The script contains **no** `DROP DATABASE`, `DROP TABLE`, `DELETE`, or `TRUNCATE` commands. Existing data cannot be lost. |
| **Idempotency** | Uses `SELECT 'CREATE DATABASE ...' WHERE NOT EXISTS (...) \gexec`. If a database already exists, the creation statement is omitted and no error is raised. |
| **Dynamic Credentials** | Reads `$POSTGRES_USER` directly from the environment (defaulting to `postgres`), avoiding hardcoded passwords or production usernames. |
| **Read-Only Mount** | Mounted with `:ro` flag in `docker-compose.yml`, preventing container processes from modifying the host initialization script. |
| **Cross-Platform Line Endings** | Enforced LF line endings via `.gitattributes` and verified via binary check, preventing interpreter failure on Windows Docker Desktop. |
| **Extension Resilience** | Uses `ON_ERROR_STOP=0` and `|| true` when registering `vector`, ensuring smooth startup even if an image without `pgvector` is substituted. |

---

## 4. Test Results

The test suite was executed against the local Python virtual environment (`backend/.venv`):
```powershell
& 'backend/.venv/Scripts/python.exe' -m pytest backend/tests -v
```

### Summary:
- **Total Tests**: **46 passed** (0 failed, 0 skipped)
- **Duration**: 1.72s
- **Breakdown**:
  - `backend/tests/ai/`: 25 passed (decision engine, Curio graph, schemas)
  - `backend/tests/services/`: 10 passed (ChatService canonical context, question hydration, state merging)
  - `backend/tests/api/`: 1 passed (`/health` endpoint)
  - `backend/tests/api/test_database_safety.py`: 10 passed (URL validation, masking, production rejections, unconfigured test DB errors)

---

## 5. Manual Developer Commands to Start & Verify Databases

When ready to start Docker, the developer should execute the following commands:

### Step 1: Start Docker Desktop
Launch Docker Desktop on Windows and ensure the Docker daemon is running.

### Step 2: Start the PostgreSQL Container
From the repository root:
```bash
docker-compose up -d db
```

### Step 3: Verify Both Databases Were Created
Query PostgreSQL's catalog to confirm both databases exist:
```bash
docker-compose exec db psql -U postgres -c "SELECT datname, pg_catalog.pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datname IN ('curio_db', 'curio_test_db');"
```
Expected output:
```text
    datname    |  owner   
---------------+----------
 curio_db      | postgres
 curio_test_db | postgres
(2 rows)
```

### Step 4: Verify pgvector Extension
Confirm the vector extension is installed on the test database:
```bash
docker-compose exec db psql -U postgres -d curio_test_db -c "\dx"
```
Expected output:
```text
                    List of installed extensions
  Name   | Version |   Schema   |             Description             
---------+---------+------------+-------------------------------------
 plpgsql | 1.0     | pg_catalog | PL/pgSQL procedural language
 vector  | 0.5.1   | public     | vector data type and access methods
(2 rows)
```

### Step 5: Configure and Run Integration Tests
Once verified, set the test database URL in `.env`:
```bash
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/curio_test_db
```
Then run tests with the `db_integration` marker or full test suite:
```bash
python -m pytest backend/tests -v
```
