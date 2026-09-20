# Walkthrough: PostgreSQL Infrastructure, Alembic Migration Setup & Isolated Test Environment

## 1. Overview & Objectives

Following the completion of the `CurioEngine` migration and PostgreSQL Integration Readiness Audit, we systematically resolved the infrastructure blockers needed to support safe PostgreSQL database operations and isolated automated testing:

1. **Alembic Migration Infrastructure Setup**: Safely initialized and configured Alembic without connecting to or mutating live databases.
2. **PostgreSQL Test Environment Isolation**: Designed `TEST_DATABASE_URL` with programmatic safety barriers to prevent accidental production targeting or silent fallbacks.
3. **Docker Multi-Database Provisioning**: Updated Docker Compose to automatically provision both `curio_db` and `curio_test_db` with `pgvector` enabled.
4. **Backend Test Configuration Integration**: Configured `backend/.env` with `TEST_DATABASE_URL`, verified `.gitignore` protection, and validated all 46 tests.

---

## 2. Key Components & Implementation Details

### a. Alembic Migration Infrastructure
* **Configuration Files**:
  * [`backend/alembic.ini`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/alembic.ini): Configured `script_location = %(here)s/alembic` to ensure reliable invocation from both root and backend directories.
  * [`backend/alembic/env.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/alembic/env.py): Injects `project_root` and `backend_root` into `sys.path`; dynamically binds `config.set_main_option("sqlalchemy.url", settings.get_database_url())`; imports `Base` from [`backend.app.db.base`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/db/base.py).
* **Model Discovery**:
  * All 7 application models (`users`, `sessions`, `session_states`, `messages`, `turn_evaluations`, `documents`, `session_reports`) are discovered on `target_metadata = Base.metadata`.
* **Verification**:
  * Tested in offline mode with `EnvironmentContext(as_sql=True)`; confirmed PostgreSQL dialect implementation (`PostgresqlImpl`) and zero database mutations.

### b. PostgreSQL Isolated Test Environment & Safety Guardrails
* **Settings Safety Methods ([`backend/app/core/config.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/core/config.py))**:
  * `TEST_DATABASE_URL: str = ""` field added to `Settings`.
  * `mask_database_url(url)`: Redacts passwords (`postgresql://user:***@host:port/db`) in all error messages, logs, and representations.
  * `validate_test_database_url(url)`:
    1. **Never Silently Falls Back**: Raises `RuntimeError` if unset.
    2. **Strict URL Separation**: Rejects URLs matching `get_database_url()`.
    3. **Explicit Test Naming**: Requires the database name to contain `"test"` (e.g. `curio_test_db`).
    4. **System/App DB Rejection**: Rejects `postgres`, `template1`, and `curio_db`.
    5. **Production Keyword Shield**: Rejects URLs with `prod`, `production`, or `live`.
* **Pytest Fixtures ([`backend/tests/conftest.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/conftest.py))**:
  * `test_db_url`: Session fixture returning validated test URL.
  * `test_db_engine`: Session fixture utilizing `NullPool` to prevent connection leaks.
  * `test_db_session`: Function fixture providing transactional rollback on test teardown.
  * `override_get_db`: Function fixture overriding FastAPI's `get_db` dependency for integration tests.
  * Registered `db_integration` marker.

### c. Docker Multi-Database Provisioning
* **Initialization Script ([`scripts/init-databases.sh`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/scripts/init-databases.sh))**:
  * Idempotently creates `curio_db` and `curio_test_db` using `SELECT 'CREATE DATABASE ...' WHERE NOT EXISTS (...) \gexec`.
  * Grants all privileges to `$POSTGRES_USER`.
  * Enables `vector` extension (`ankane/pgvector`) on both databases.
  * Non-destructive: Contains zero `DROP`, `DELETE`, or `TRUNCATE` statements.
* **Line Ending Integrity ([` .gitattributes`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/.gitattributes))**:
  * Enforces `*.sh text eol=lf` to prevent Windows CRLF interpreter failures (`/bin/bash^M`) inside Linux containers.
* **Docker Compose Mount ([`docker-compose.yml`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docker-compose.yml))**:
  * Mounted `./scripts/init-databases.sh:/docker-entrypoint-initdb.d/init-databases.sh:ro` on service `db`.

### d. Backend Test Database Configuration
* **Environment File ([`backend/.env`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/.env))**:
  * Added `TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/curio_test_db`.
  * Preserved all existing variables (`PROJECT_NAME`, `POSTGRES_*`, `GROQ_API_KEY`, etc.).
  * Verified that `.gitignore` line 2 (`.env`) completely ignores `backend/.env`.
* **Config Resilience**:
  * Configured `Config.env_file` in [`backend/app/core/config.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/core/config.py) to resolve `.env` from both `backend/` and repository root.
  * Added `extra = "ignore"` to `Settings.Config` to prevent crashes when extra frontend environment variables are present.

---

## 3. Verification & Live Results

### a. Live Docker Verification
Execution of `docker-compose up -d db`:
1. Container `curio-ai-db-1` started successfully.
2. Verified database catalog:
   ```text
       datname    
   ---------------
    curio_db
    curio_test_db
   (2 rows)
   ```
3. Verified pgvector extension on `curio_test_db`:
   ```text
     Name   | Version |   Schema   |                     Description                      
   ---------+---------+------------+------------------------------------------------------
    plpgsql | 1.0     | pg_catalog | PL/pgSQL procedural language
    vector  | 0.5.1   | public     | vector data type and ivfflat and hnsw access methods
   ```

### b. Database Safety Test Suite
Executed [`backend/tests/api/test_database_safety.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/api/test_database_safety.py):
* `test_mask_database_url_masks_password`: **PASSED**
* `test_mask_database_url_handles_empty_or_no_password`: **PASSED**
* `test_get_test_database_url_unconfigured_fails`: **PASSED**
* `test_validate_test_database_url_rejects_identical_to_main`: **PASSED**
* `test_validate_test_database_url_rejects_system_databases`: **PASSED**
* `test_validate_test_database_url_rejects_app_database`: **PASSED**
* `test_validate_test_database_url_requires_test_in_name`: **PASSED**
* `test_validate_test_database_url_rejects_production_keywords`: **PASSED**
* `test_validate_test_database_url_accepts_valid_test_url`: **PASSED**

### c. Full Test Suite Execution
```powershell
python -m pytest backend/tests -v
```
```text
======================= 46 passed, 60 warnings in 1.75s =======================
```
* **AI Tests**: 25 passed
* **Service Tests**: 10 passed
* **API Health Test**: 1 passed
* **Database Safety Tests**: 10 passed

---

## 4. Documentation Generated

| Document | Purpose |
| :--- | :--- |
| [`docs/alembic-setup-report.md`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docs/alembic-setup-report.md) | Initial Alembic migration setup, offline validation, and model detection report |
| [`docs/postgresql-test-environment-report.md`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docs/postgresql-test-environment-report.md) | `TEST_DATABASE_URL` safety rules, pytest fixtures design, and connection isolation |
| [`docs/docker-test-database-setup-report.md`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docs/docker-test-database-setup-report.md) | Multi-database Docker Compose initialization, `/docker-entrypoint-initdb.d/` lifecycle, and verification |
| [`docs/postgresql-and-test-environment-walkthrough.md`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docs/postgresql-and-test-environment-walkthrough.md) | End-to-end walkthrough report covering all completed PostgreSQL milestones |

---

## 5. Next Steps Readiness

The database infrastructure is fully provisioned and validated:
1. `curio_db` and `curio_test_db` are actively running on PostgreSQL port 5432.
2. `TEST_DATABASE_URL` is loaded via `backend/.env` and verified by safety tests.
3. Alembic is ready to autogenerate the baseline schema migration:
   ```bash
   alembic -c backend/alembic.ini revision --autogenerate -m "initial_schema"
   ```
