# Code Ownership Matrix

This document outlines team ownership boundaries for the Curio AI monorepo.

## Direct Code CodeOwnership

| Component / Path | Primary Owner | Description |
| :--- | :--- | :--- |
| `frontend/` | **Chinmay** | Complete Next.js dashboard, sidebars, stores, and components. |
| `backend/app/ai/` | **Chinmay** | Prompt engineering, LLM evaluators, state machine decisions. |
| `backend/app/api/` | **Vishal** | FastAPI routes, requests validation, error handlers. |
| `backend/app/models/` | **Vishal** | SQLAlchemy ORM entity definitions. |
| `backend/app/repositories/` | **Vishal** | Database access objects, transactions, and filters. |
| `backend/app/services/` | **Vishal** | Application coordination, database-AI mapping. |
| `backend/app/db/` | **Vishal** | Postgres session management, db pools. |
| `backend/alembic/` | **Vishal** | Alembic database schema migrations. |
| `contracts/` | **Shared** | API endpoints, LLM JSON inputs/outputs specs. |
| `docs/` | **Shared** | Architecture, state machine, and development documents. |

## Interfacing Boundary

### The DB-AI Isolation Rule

```
                  +-------------------------+
                  |  backend/app/services   |
                  |     (Vishal's layer)    |
                  +-------------------------+
                               |
                               |  Maps db models to AI schemas
                               v
                  +-------------------------+
                  |     backend/app/ai      |
                  |    (Chinmay's layer)    |
                  +-------------------------+
```

1. **Database Access**: Chinmay's AI files must **never** import `sqlalchemy` or anything from `backend/app/models/` or `backend/app/db/`.
2. **Context Passing**: Vishal's service layers load the data from PostgreSQL, construct the static Pydantic input models (defined in `backend/app/ai/schemas.py`), call the orchestrator, and handle saving the output evaluations and session state back to the database.
