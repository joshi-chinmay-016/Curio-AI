# Development Workflow & Git Guidelines

This document establishes the daily git workflow, PR review structure, and synchronization protocols for the Curio AI development team.

## Branch Naming Conventions

- **Vishal**: Use `feat/backend-*` or `fix/backend-*`.
  - Examples: `feat/backend-session-api`, `feat/backend-message-persistence`
- **Chinmay**: Use `feat/frontend-*` or `feat/ai-*` or `fix/frontend-*`.
  - Examples: `feat/frontend-chat-ui`, `feat/ai-evaluator-engine`

## Pull Request Template

Every PR should specify the following checklist:
- **Summary**: What was built and why.
- **Contracts changed?**: Have `contracts/` markdown specs been modified? (Requires approval from both).
- **Database migrations?**: Does this PR add Alembic migrations?
- **Testing**: List commands run and results.
- **Screenshots**: Mandatory if UI changes are introduced.

## Contract Modification Protocol

If either developer needs to change an API input/output model or an AI Engine schema:
1. Open a discussion or create a quick PR modifying the files under `contracts/`.
2. Both developers must approve the PR.
3. Once approved, Chinmay updates the TypeScript types in the frontend and Pydantic schemas in the AI engine. Vishal updates SQLAlchemy models and endpoints in parallel.

## Migration and DB Schema Guidelines
- Vishal owns all schema migrations.
- When Chinmay requires a new database attribute, he requests it via a Github Issue/contract update. Vishal writes the Alembic migration and pushes it.
- To execute migrations locally, run: `alembic upgrade head`.
