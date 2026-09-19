# Curio AI — Phase 0 Audit Report

## 1. Executive Summary

This Phase 0 Audit was performed as a read-only architectural, environment, and code hygiene inspection of the Curio AI monorepo. Curio AI is designed as a role-reversal learning platform centered on the Feynman Learning Technique, where the AI acts primarily as an inquisitive student, switches adaptively to a tutor/teacher when conceptual gaps are detected, and compiles structured diagnostic reports upon session completion.

The audit verified that the repository contains an initial architectural scaffold including a FastAPI backend with a custom state machine, a Next.js 14 frontend, technical contracts, and architectural documentation. However, several critical gaps and environment mismatches were identified:
- **No Python virtual environment exists**; global Python 3.13.14 is present with some packages installed globally, whereas the project pin (in Docker and CI) is Python 3.10.
- **The frontend API client layer is completely missing from disk** (`frontend/lib/api/client.ts`), causing the frontend build and TypeScript checks to fail.
- **Alembic migrations are not initialized**: no `alembic.ini` or migration versions directory exists despite Alembic being declared in `requirements.txt`.
- **Docker Desktop is not running**, and the PostgreSQL service is currently offline.
- **Model vs. Schema naming mismatches** exist in the backend (e.g., `Message.id` vs. `MessageResponse.message_id`), which will trigger runtime Pydantic validation errors when reading from the database.

---

## 2. Repository and Git Status

### 2.1 Repository Information
- **Repository Root**: `c:\Users\Vishal S Naik\MyProjects\Curio-AI`
- **Current Git Branch**: `dev`
- **Remote Origin**: `https://github.com/joshi-chinmay-016/Curio-AI.git`
- **Available Branches**:
  - Local: `dev`
  - Remote: `origin/HEAD -> origin/dev`, `origin/dev`, `origin/main`

### 2.2 Working Tree Status
- The working tree is clean (`nothing to commit, working tree clean`).
- `git status --ignored` revealed untracked local artifacts left from previous executions:
  - `.pytest_cache/`
  - `backend/app/ai/__pycache__/`
  - `backend/app/schemas/__pycache__/`
  - `backend/tests/ai/__pycache__/`
  - `backend/tests/api/__pycache__/`
- No tracked `.env` file exists; only `.env.example` is tracked.
- No unstaged changes or untracked source files are present.

### 2.3 Commit History
Recent commits on `dev`:
1. `4aa38f7` — *Update ReadMe*
2. `ba8ecc7` — *Update ReadMe*
3. `9952edc` — *feat: initial Curio AI monorepo scaffold Sets up the end-to-end architecture including FastAPI backend with AI state machine, Next.js frontend with Tailwind and Zustand, Docker infrastructure, CI workflows, and technical contracts.*
4. `a89befa` — *Create Readme.md*

### 2.4 Monorepo and Branching Conventions
- **Structure**: Monorepo containing `backend/`, `frontend/`, `contracts/`, `docs/`, `scripts/`, and root-level Docker and CI workflows.
- **Branching Convention**: Two-branch model (`main` for production releases, `dev` for active integration). Note that the CI workflow `.github/workflows/ci.yml` currently triggers only on `main`, meaning changes pushed to `dev` do not trigger automated CI runs.
- **Documentation**: Root `Readme.md` (53.8 KB) details the Feynman technique, architectural state machine, data models, and local setup commands. No separate `CONTRIBUTING.md` exists. `.gitignore` is present and properly configured.

---

## 3. Current Project Structure

The repository contains 8 primary subdirectories and 5 root configuration files. Below is the verified inventory:

| Relative Path | Apparent Purpose | Exists | Status |
| :--- | :--- | :---: | :--- |
| `.env.example` | Environment variable template | Yes | Confirmed |
| `.gitignore` | Git exclusions list | Yes | Confirmed |
| `docker-compose.yml` | Docker Compose specification for db & backend | Yes | Confirmed |
| `Dockerfile` | Container image specification for backend | Yes | Confirmed |
| `Readme.md` | Monorepo architecture & setup guide | Yes | Confirmed |
| `.github/workflows/ci.yml` | GitHub Actions CI workflow | Yes | Confirmed |
| `.github/pull_request_template.md` | PR template | Yes | Confirmed |
| `backend/requirements.txt` | Python dependencies declaration | Yes | Confirmed |
| `backend/app/main.py` | FastAPI application entry point | Yes | Confirmed |
| `backend/app/core/` | Core configuration, exceptions, and logging | Yes | Confirmed |
| `backend/app/db/` | SQLAlchemy engine & session management | Yes | Confirmed |
| `backend/app/models/` | SQLAlchemy ORM database models | Yes | Confirmed |
| `backend/app/schemas/` | Pydantic request/response schemas | Yes | Confirmed |
| `backend/app/repositories/` | Data access layer | Yes | Confirmed |
| `backend/app/services/` | Business logic & service orchestration | Yes | Confirmed |
| `backend/app/api/` | REST API routes (v1 endpoints) | Yes | Confirmed |
| `backend/app/ai/` | State machine, evaluator, decision engine, Groq/Mock | Yes | Confirmed |
| `backend/tests/` | Backend test suite | Yes | Confirmed |
| `backend/alembic/` | Alembic migrations | **No** | Missing |
| `contracts/` | API, AI, and Events markdown contracts & sample JSONs | Yes | Confirmed |
| `docs/` | Architectural docs, ADRs, database docs | Yes | Confirmed |
| `frontend/package.json` | Frontend dependencies & scripts | Yes | Confirmed |
| `frontend/app/` | Next.js App Router root & pages | Yes | Confirmed |
| `frontend/components/` | React UI components (chat, reports, sessions) | Yes | Confirmed |
| `frontend/stores/` | Zustand state store (`session-store.ts`) | Yes | Confirmed |
| `frontend/types/` | TypeScript interface definitions (`index.ts`) | Yes | Confirmed |
| `frontend/lib/api/client.ts` | Frontend API client implementation | **No** | Missing (Broken import) |
| `scripts/` | Developer setup scripts (`setup.ps1`, `setup.sh`) | Yes | Confirmed |

---

## 4. Development Environment

Command verification results executed on the Windows host:

| Tool | Status | Version / Output | Binary Location |
| :--- | :--- | :--- | :--- |
| **python** | Available | `Python 3.13.14` | `C:\Users\Vishal S Naik\AppData\Local\Programs\Python\Python313\python.exe` |
| **python3** | Alias Error | Microsoft Store Alias Error (`App execution alias`) | `C:\Users\Vishal S Naik\AppData\Local\Microsoft\WindowsApps\python3.exe` |
| **pip** | Available | `pip 26.1.2` | `C:\Users\Vishal S Naik\AppData\Local\Programs\Python\Python313\Scripts\pip.exe` |
| **pip3** | Available | `pip 26.1.2` | `C:\Users\Vishal S Naik\AppData\Local\Programs\Python\Python313\Scripts\pip3.exe` |
| **git** | Available | `git version 2.54.0.windows.1` | `C:\Program Files\Git\cmd\git.exe` |
| **uvicorn** | Not Found | Not installed in system PATH (`CommandNotFoundException`) | None |
| **psql** | Available | `psql (PostgreSQL) 18.4` | `C:\Program Files\PostgreSQL\18\bin\psql.exe` |
| **docker** | CLI Available | `Docker version 29.6.1, build 8900f1d` | `C:\Program Files\Docker\Docker\resources\bin\docker.exe` |
| **docker daemon** | **Not Running** | `failed to connect to the docker API at npipe...` | Engine offline |

### Virtual Environment Audit
- Checked paths: `.venv`, `venv`, `env`, `backend/.venv`, `backend/venv`, `backend/env`.
- **Finding**: All returned `False`. **No Python virtual environment exists**.
- **Important**: System Python 3.13.14 has several packages installed in global site-packages (FastAPI 0.141.1, SQLAlchemy 2.0.54, psycopg2-binary 2.9.13, pydantic 2.13.5, pytest 9.1.1, groq 1.7.0). However, running project workflows in the global environment is strongly discouraged due to version conflicts with pinned project requirements.

---

## 5. Python Dependencies

### 5.1 Dependency Files
- Only one dependency file is present: `backend/requirements.txt`.
- No `pyproject.toml`, `poetry.lock`, `Pipfile`, `setup.py`, or `requirements-dev.txt` exist.

### 5.2 Dependency Declaration Checklist (from `backend/requirements.txt`)
- **FastAPI**: Declared (`fastapi==0.109.2`)
- **Uvicorn**: Declared (`uvicorn==0.27.1`)
- **SQLAlchemy**: Declared (`sqlalchemy==2.0.25`)
- **Alembic**: Declared (`alembic==1.13.1`)
- **Pydantic**: Declared (`pydantic==2.6.1`, `pydantic-settings==2.1.0`)
- **Pytest**: Declared (`pytest==8.0.0`)
- **PostgreSQL Driver**: Declared (`psycopg2-binary==2.9.9`)
- **AI Dependencies**: Declared (`groq==0.4.2`). **LangGraph is NOT declared.**
- **Other Dependencies**: `httpx==0.26.0`, `python-multipart==0.0.9`.

### 5.3 Version Alignment Issues
- `Dockerfile` targets `python:3.10-slim`.
- `.github/workflows/ci.yml` uses `python-version: '3.10'`.
- Host machine has `Python 3.13.14`. Some dependencies pinned from early 2024 (e.g. `fastapi==0.109.2`, `pydantic==2.6.1`, `sqlalchemy==2.0.25`) may experience build issues with C-extensions on Python 3.13 on Windows if binary wheels are absent.

---

## 6. Backend Architecture

### 6.1 Application Entry Point
- Located in `backend/app/main.py`.
- Creates the FastAPI app instance with metadata, sets up CORS middleware using `settings.BACKEND_CORS_ORIGINS`, registers global exception handlers from `backend/app/core/exceptions.py`, mounts a root `/health` endpoint, and includes the versioned API router at `/api/v1`.

### 6.2 Route Structure
Mounted in `backend/app/api/router.py`:
- **Sessions** (`backend/app/api/v1/sessions.py`):
  - `POST /api/v1/sessions` — Create a new learning session
  - `GET /api/v1/sessions` — List user session summaries
  - `GET /api/v1/sessions/{session_id}` — Get single session details
  - `PATCH /api/v1/sessions/{session_id}` — Update session parameters
  - `DELETE /api/v1/sessions/{session_id}` — Delete session (cascading)
  - `POST /api/v1/sessions/{session_id}/pause` — Pause session
  - `POST /api/v1/sessions/{session_id}/resume` — Resume session
  - `POST /api/v1/sessions/{session_id}/end` — Complete session and trigger report compilation
- **Messages** (`backend/app/api/v1/messages.py`):
  - `POST /api/v1/sessions/{session_id}/messages` — Send user message, evaluate, step state machine, return AI response
  - `GET /api/v1/sessions/{session_id}/messages` — Get session message history
- **Documents** (`backend/app/api/v1/documents.py`):
  - `POST /api/v1/documents` — Multipart file upload (PDF/Text)
  - `GET /api/v1/documents/{document_id}` — Retrieve document metadata
- **Reports** (`backend/app/api/v1/reports.py`):
  - `GET /api/v1/sessions/{session_id}/report` — Retrieve compiled evaluation report
- **Health**:
  - `GET /health` — Root health check

### 6.3 Layered Architecture Audit & Target Direction Comparison
The requested target direction is: **API route → Service → Repository**.

| Layer | Implementation Found | Compliance / Deviation |
| :--- | :--- | :--- |
| **API Router** | `backend/app/api/v1/*.py` | Routes call service methods, but services are instantiated as **module-level global singletons** rather than using FastAPI's `Depends()` dependency injection. |
| **Service Layer** | `backend/app/services/*.py` (`SessionService`, `ChatService`, `DocumentService`, `ReportService`) | Contains business logic and orchestrates AI/state transitions. However, services instantiate repositories internally via `self.repo = SessionRepository()` instead of accepting injected instances. |
| **Repository Layer** | `backend/app/repositories/*.py` (`SessionRepository`, `MessageRepository`, `DocumentRepository`) | Encapsulates SQLAlchemy CRUD operations using synchronous sessions (`db.query(...)`, `db.add(...)`, `db.commit()`). |
| **AI Layer** | `backend/app/ai/*.py` | Implemented as a standalone, deterministic state machine (`decision_engine.py`) and orchestrator (`orchestrator.py`), independent of web frameworks. |
| **Location** | `backend/app/*` | Project is structured under a `backend/` monorepo directory rather than at the workspace root `app/`. |

### 6.4 Authentication & Session Management
- **Authentication**: No real authentication system is implemented. In `backend/app/services/session_service.py`, a hardcoded mock user UUID (`00000000-0000-0000-0000-000000000000`) and mock email (`chinmay.vishal@curio.ai`) are used to satisfy database foreign keys.
- **Session State**: Explicitly tracked in the database table `session_states`, storing `current_mode` (`STUDENT`, `TEACHER`, `EVALUATOR`), `difficulty` (1–5), `confidence` (0.0–1.0), `consecutive_strong_answers`, `consecutive_weak_answers`, and JSON arrays for misconceptions and mastered concepts.

### 6.5 AI Engine Implementation vs LangGraph
- The documentation (`Readme.md`) describes an AI state machine and mentions LangGraph.
- **Observed Reality**: LangGraph is **not implemented or installed**. The AI engine is built with custom Python code:
  - `AIOrchestrator` (`backend/app/ai/orchestrator.py`) coordinates the turn.
  - `AIEvaluator` evaluates user answers against 6 dimensions (correctness, clarity, completeness, depth, relevance, stuck probability).
  - `decide_next_action` (`backend/app/ai/decision_engine.py`) selects mode transitions and pedagogical strategies.
  - `GroqLLMProvider` connects to Groq API (`llama3-8b-8192` for structured schema extraction, `llama-3.1-70b-versatile` for conversational generation) and automatically falls back to `MockLLMProvider` if `GROQ_API_KEY` is not provided.

---

## 7. Database Configuration

### 7.1 Configuration & Connection Logic
- **Configuration Source**: `backend/app/core/config.py` via `pydantic_settings.BaseSettings`.
- **Connection Method**: `backend/app/db/session.py` initializes a synchronous SQLAlchemy engine:
  ```python
  engine = create_engine(settings.get_database_url(), pool_pre_ping=True)
  SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
  Base = declarative_base()
  ```
- **Driver**: `psycopg2` via `psycopg2-binary`.
- **Connection Pooling**: Default SQLAlchemy QueuePool with `pool_pre_ping=True`.
- **Session Lifecycle**: Handled by generator `get_db()` yielding `SessionLocal()`.

### 7.2 Models Inventory
Defined in `backend/app/models/` and aggregated in `backend/app/db/base.py`:
1. `user.py` (`User`): Primary key UUID, email, created_at, relationship to sessions.
2. `session.py` (`Session` and `SessionState`): Session lifecycle and active pedagogical state machine tracking.
3. `message.py` (`Message`): Message records with sender (`USER`, `AI`), content, and input_type.
4. `evaluation.py` (`TurnEvaluation`): Metrics per message turn (scores, misconceptions, recommendations).
5. `document.py` (`Document`): Uploaded document metadata.
6. `report.py` (`SessionReport`): Final session evaluation report.

### 7.3 Migrations & Initialization Status
- **Alembic Status**: **Uninitialized**. There is no `alembic.ini`, no `alembic/` or `migrations/` directory, and no migration scripts exist anywhere in the repository.
- **Database Table Initialization**: No `Base.metadata.create_all(bind=engine)` call exists in the application startup code. Unless tables are created manually, running the application against an empty database will result in table-not-found errors.
- **Database Health Check**: In `backend/app/main.py`, the `/health` endpoint hardcodes `"database": "connected"` with a comment `# In a real environment, we'd ping the DB`. It does not perform an actual database query.

---

## 8. Environment Variables

### 8.1 Variable Inventory
Only variable names are reported. No values or secrets are revealed:

| Variable Name | Referenced In | Safe Template Exists? | Required? | Notes |
| :--- | :--- | :---: | :---: | :--- |
| `PROJECT_NAME` | `backend/app/core/config.py`, `.env.example` | Yes | Optional | Defaults to `"Curio AI"` |
| `API_V1_STR` | `backend/app/core/config.py` | No | Optional | Defaults to `"/api/v1"` |
| `BACKEND_CORS_ORIGINS` | `backend/app/core/config.py` | No | Optional | Defaults to localhost/127.0.0.1 origins |
| `POSTGRES_SERVER` | `backend/app/core/config.py`, `.env.example` | Yes | Required* | *Required if `DATABASE_URL` is not set |
| `POSTGRES_USER` | `backend/app/core/config.py`, `.env.example`, `docker-compose.yml` | Yes | Required* | *Required if `DATABASE_URL` is not set |
| `POSTGRES_PASSWORD` | `backend/app/core/config.py`, `.env.example`, `docker-compose.yml` | Yes | Required* | Secret value intentionally not displayed |
| `POSTGRES_DB` | `backend/app/core/config.py`, `.env.example`, `docker-compose.yml` | Yes | Required* | *Required if `DATABASE_URL` is not set |
| `POSTGRES_PORT` | `backend/app/core/config.py`, `.env.example` | Yes | Required* | Defaults to `5432` |
| `DATABASE_URL` | `backend/app/core/config.py`, `docker-compose.yml` | No | Optional | Overrides individual `POSTGRES_*` variables |
| `GROQ_API_KEY` | `backend/app/core/config.py`, `backend/app/ai/providers/groq_provider.py`, `.env.example`, `docker-compose.yml` | Yes | Optional** | **Live AI requires key; falls back to mock if blank |
| `NEXT_PUBLIC_USE_MOCK_API` | `.env.example`, `docs/adr/adr-001-mock-first-api.md` | Yes | Optional | Frontend mock switch (defaults to `true`) |
| `NEXT_PUBLIC_API_URL` | `.env.example` | Yes | Optional | Frontend API target (defaults to `http://localhost:8000/api/v1`) |

### 8.2 Configuration Observations
- Default fallback database credentials in `backend/app/core/config.py` default to `postgres:postgres` on `localhost:5432`.
- No actual `.env` file exists on disk. Developers must copy `.env.example` to `.env`.

---

## 9. Frontend–Backend Integration

### 9.1 Base URL & CORS
- **Base URL**: Set via `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` in `.env.example`.
- **CORS**: Configured in `backend/app/main.py` allows origins: `http://localhost:3000`, `http://localhost:8000`, `http://127.0.0.1:3000`, and `http://127.0.0.1:8000`.

### 9.2 Critical Finding: Missing Frontend API Client
- In `frontend/stores/session-store.ts` (line 3):
  ```typescript
  import { api } from '../lib/api/client';
  ```
- **Verification**: The directory `frontend/lib/` and file `frontend/lib/api/client.ts` **do not exist**.
- **Impact**: Any attempt to build or run type checking on the frontend (`npx tsc --noEmit` or `npm run build`) will fail immediately with `Cannot find module '../lib/api/client'`.
- Context from `docs/adr/adr-001-mock-first-api.md`: ADR-001 specified creating a `CurioApi` interface in `frontend/lib/api/client.ts` with `MockCurioApi` and `HttpCurioApi` implementations, but this file was never created or committed.

### 9.3 Schema & Field Naming Mismatches
1. **Message Primary Key Mismatch**:
   - Model `backend/app/models/message.py` defines the primary key as `id = Column(...)`.
   - Schema `backend/app/schemas/message.py` defines `message_id: UUID` with `from_attributes = True`.
   - Contract `contracts/api-contract.md` defines `message_id`.
   - Frontend interface `frontend/types/index.ts` defines `message_id: string`.
   - **Problem**: When `MessageResponse.model_validate(db_message)` is called in `backend/app/services/chat_service.py`, Pydantic v2 fails because `db_message` has `.id` but lacks `.message_id`.

2. **Document Primary Key Mismatch**:
   - Model `backend/app/models/document.py` defines `id = Column(...)`.
   - Schema `backend/app/schemas/document.py` defines `document_id: UUID`.
   - Calling `DocumentResponse.model_validate(db_doc)` in `backend/app/services/document_service.py` produces the same Pydantic validation failure.

3. **Session Response Identifier Mismatch**:
   - Schema `backend/app/schemas/session.py` (`SessionResponse`) defines `id: UUID`.
   - Contract `contracts/api-contract.md` specifies `"session_id": "..."`.
   - `SessionSummaryResponse` in the same file defines `session_id: UUID`.
   - This internal inconsistency causes discrepancies between session detail responses and session list responses.

4. **Error Response Format Inconsistency**:
   - Custom exceptions (`backend/app/core/exceptions.py`) return `{"code": "...", "message": "..."}`.
   - Standard route `HTTPException` raises (e.g. in `backend/app/api/v1/sessions.py`) return FastAPI's default `{"detail": "..."}`.

---

## 10. Testing Setup

### 10.1 Existing Tests
Backend tests are located in `backend/tests/`:
1. `backend/tests/ai/test_decision_engine.py`:
   - `test_scenario_1_correct_but_incomplete` (verifies student mode stays active and probes missing concept)
   - `test_scenario_2_user_stuck` (verifies transition to teacher mode when user is stuck)
   - `test_scenario_3_teacher_verified` (verifies transition back to student mode and restoration of interrupted question)
   - `test_scenario_4_confidence_limit` (verifies offering termination when confidence threshold is reached)
2. `backend/tests/api/test_health.py`:
   - `test_health_endpoint` (verifies `GET /health` returns status 200 and `"status": "healthy"`)

### 10.2 Frontend Tests
- **None**. `frontend/package.json` contains no `test` script, and no testing framework (Jest, Vitest, Cypress, Playwright) is installed or configured.

### 10.3 Test Execution Safety Assessment
- **Read-Only Dry Run (`pytest --collect-only backend/tests/`)**:
  - Successfully collected 5 test items in 2.14 seconds.
- **Why Full Execution Is Unsafe/Improper in the Current State**:
  1. **Absence of a Virtual Environment**: Running pytest in the global Python 3.13.14 environment risks altering global cache files and lacks isolation.
  2. **Python Version Incompatibility**: Pydantic v1 `class Config:` syntax and SQLAlchemy 1.x style `declarative_base()` produce multiple `PydanticDeprecatedSince20` and `MovedIn20Warning` deprecation warnings on Python 3.13.
  3. **No Database Available**: While the current 5 tests do not hit the database directly, any subsequent database or integration tests cannot run because the database is offline and unmigrated.
  4. Per explicit audit instructions, no tests were claimed to pass without full execution.

---

## 11. Deployment Configuration

### 11.1 Docker Infrastructure
- `Dockerfile`:
  - Base image: `python:3.10-slim`
  - Installs system packages `gcc` and `libpq-dev`
  - Copies `backend/requirements.txt` and installs via pip
  - Copies `./backend` to `/app/backend`
  - Sets `ENV PYTHONPATH=/app`
  - Entrypoint: `CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- `docker-compose.yml`:
  - Service `db`: image `ankane/pgvector:latest`, maps port `5432:5432`, persists to volume `postgres_data`.
  - Service `backend`: builds root `Dockerfile`, maps port `8000:8000`, depends on `db`, mounts `./backend:/app/backend`.
  - **Missing**: Frontend service is not defined in `docker-compose.yml`.

### 11.2 Continuous Integration
- `.github/workflows/ci.yml`:
  - Triggers on `push` and `pull_request` to branch `main`.
  - Backend job: Sets up Python 3.10, installs `backend/requirements.txt`, runs `pytest backend/tests/` with `PYTHONPATH=$PWD`.
  - Frontend job: Sets up Node 20 with `cache-dependency-path: 'frontend/package-lock.json'`, runs `npm install --legacy-peer-deps`, `npx tsc --noEmit`, and `npm run build`.
  - **CI Vulnerability**: `frontend/package-lock.json` is missing from git, which may disrupt npm caching in CI. Furthermore, the frontend build step will fail due to the missing `frontend/lib/api/client.ts`.

### 11.3 Startup Commands (from documentation)
- Backend: `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload` (requires virtualenv and `PYTHONPATH=.`).
- Frontend: `npm run dev` in `frontend/`.
- Full stack local: `docker compose up --build`.

---

## 12. Security and Repository Hygiene

### 12.1 Findings
1. **No Committed Secrets**: A search across tracked git files confirmed no live API keys, JWT secrets, private keys, or `.env` files were accidentally committed.
2. **Hardcoded Fallback Credentials**: In `backend/app/core/config.py` and `docker-compose.yml`, default database credentials (`postgres:postgres`) are hardcoded as fallbacks.
3. **Mock Authentication**: `backend/app/services/session_service.py` uses a static mock UUID without user verification, authorization checks, or tenant isolation.
4. **CORS Settings**: Permissive for localhost development (`allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`). Must be parameterized before production deployment.
5. **Unvalidated File Upload**: In `backend/app/api/v1/documents.py`, `upload_document` accepts any uploaded file without MIME-type whitelist verification or size limits.
6. **Git Hygiene**: Local `.pytest_cache` and `__pycache__` artifacts are present on disk. Although correctly ignored by `.gitignore`, they should be cleaned up.

---

## 13. Confirmed Findings

1. **Repository Structure**: Monorepo with distinct `backend/`, `frontend/`, `contracts/`, `docs/`, and `scripts/` directories, currently on branch `dev`.
2. **Virtual Environment**: Confirmed that **no virtual environment exists** anywhere in the project tree.
3. **Installed Tooling**: Python 3.13.14, pip 26.1.2, git 2.54.0, psql 18.4, and Docker CLI 29.6.1 are available on the host. `uvicorn` is not installed globally.
4. **Docker Daemon Status**: Confirmed Docker daemon is **offline**; `docker info` fails to connect to the named pipe.
5. **Missing Frontend API Client**: Confirmed `frontend/lib/api/client.ts` does not exist on disk, breaking the frontend build.
6. **Uninitialized Database Migrations**: Confirmed no `alembic.ini` or migration version files exist.
7. **Mock AI Fallback**: Confirmed `GroqLLMProvider` automatically falls back to `MockLLMProvider` when `GROQ_API_KEY` is not supplied.
8. **Test Collection**: Confirmed Pytest successfully collects 5 tests across AI and API modules when `PYTHONPATH` is properly configured.
9. **Clean Git Tree**: Confirmed no untracked or modified source files are pending in git.

---

## 14. Missing or Unverified Information

1. **Database Schema on Running Server**: Because the PostgreSQL service and Docker are offline, database connectivity and runtime table structures could not be verified against a live instance.
2. **Groq API Key Validity**: No active key was verified (not set in environment).
3. **Frontend Runtime Appearance**: Because the frontend API client is missing, the Next.js frontend cannot compile or run.
4. **`package-lock.json`**: Not present in `frontend/`, preventing strict lockfile verification.

---

## 15. Potential Risks and Issues

| Risk / Issue | Severity | Impact | Affected Area |
| :--- | :---: | :--- | :--- |
| **Missing `frontend/lib/api/client.ts`** | **CRITICAL** | Frontend build (`npm run build`) and type check (`tsc`) fail completely. | Frontend / Monorepo build |
| **Model vs Schema Column Mismatches** (`id` vs `message_id`, `document_id`) | **HIGH** | Pydantic will raise validation errors on runtime serialization for messages and documents. | Backend API & Services |
| **No Alembic Migrations & No Table Init** | **HIGH** | Starting the backend against PostgreSQL will fail immediately with missing table errors. | Backend / Database |
| **Python Version Disparity (3.10 vs 3.13)** | **MEDIUM** | Deprecation warnings and potential binary wheel compilation errors during package installation. | Backend Environment |
| **Hardcoded Mock User Authentication** | **MEDIUM** | No multi-user separation or security; all data maps to static UUID `00000000-0000-0000-0000-000000000000`. | Backend Security & Data Model |
| **Missing Frontend in `docker-compose.yml`** | **LOW** | Running `docker compose up` starts database and backend, but leaves out frontend. | DevOps / Local Dev |
| **CI Workflow Only Listens to `main`** | **LOW** | PRs or commits to `dev` do not trigger automated CI verification. | DevOps / CI Pipeline |

---

## 16. Required Actions Before Phase 1

Before proceeding to Phase 1 (Database Implementation and Migration Setup), the following prerequisites must be addressed:

1. **Create an Isolated Python Virtual Environment**:
   - Create a Python virtual environment (Python 3.10 or 3.11 recommended to match Docker/CI specifications).
   - Install dependencies from `backend/requirements.txt`.
2. **Initialize Alembic**:
   - Run `alembic init` within `backend/` or repository root.
   - Configure `alembic.ini` and `env.py` to import `Base` from `backend.app.db.base` and point to `settings.get_database_url()`.
   - Generate initial migration scripts for all 7 database models.
3. **Resolve Model–Schema Property Mismatches**:
   - Align `Message.id` with `MessageResponse.message_id` (using Pydantic v2 `validation_alias` or model property).
   - Align `Document.id` with `DocumentResponse.document_id`.
   - Standardize `SessionResponse` to consistently use `session_id` or `id`.
4. **Implement Missing Frontend API Client**:
   - Create `frontend/lib/api/client.ts` implementing `CurioApi` with both `MockCurioApi` and `HttpCurioApi` as decided in ADR-001.
   - Generate `frontend/package-lock.json` via `npm install`.
5. **Start Docker and PostgreSQL**:
   - Start Docker Desktop to enable running `ankane/pgvector` via Docker Compose.
6. **Implement Real Database Health Check**:
   - Replace the mock response in `GET /health` with an actual `SELECT 1` execution using the SQLAlchemy session.

---

## 17. Phase 0 Completion Checklist

- [x] Repository location confirmed — **COMPLETE**
- [x] Git status reviewed — **COMPLETE**
- [x] Branch structure documented — **COMPLETE**
- [x] Project structure documented — **COMPLETE**
- [x] Python availability checked — **COMPLETE**
- [x] Virtual environment status checked — **COMPLETE**
- [x] Dependency files identified — **COMPLETE**
- [x] Backend framework status checked — **COMPLETE**
- [x] PostgreSQL client status checked — **COMPLETE**
- [x] Database configuration reviewed — **COMPLETE**
- [x] Environment variable names documented safely — **COMPLETE**
- [x] Frontend/backend integration reviewed — **COMPLETE**
- [x] Existing tests identified — **COMPLETE**
- [x] Deployment configuration reviewed — **COMPLETE**
- [x] Security risks reviewed — **COMPLETE**
- [x] Missing information documented — **COMPLETE**
- [x] Phase 1 prerequisites identified — **COMPLETE**
