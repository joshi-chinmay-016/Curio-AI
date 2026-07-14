# Curio AI - Learn by Teaching

Curio AI reverses the traditional chatbot dynamic. The user acts as the teacher, and the AI acts as a curious student. You select a topic and attempt to teach it. The AI evaluates your explanation, detects gaps, asks follow-up questions, challenges vague explanations, identifies misconceptions, and switches roles when you get stuck.

## Architecture Overview
- **Frontend**: Next.js 14, Tailwind CSS, Zustand. (Owner: Chinmay)
- **Backend**: Python 3.10, FastAPI, SQLAlchemy, Pydantic. (Owner: Vishal)
- **Database**: PostgreSQL with pgvector support (future).
- **AI Engine**: Python-based deterministic state machine paired with Groq LLM integration. (Owner: Chinmay)

## Quick Start (Local Development)

### 1. Environment Setup
```bash
cp .env.example .env
```
*Optional: Add your `GROQ_API_KEY` in `.env` if you wish to run the real AI module on the backend.*

### 2. Run Database
```bash
docker-compose up db -d
```

### 3. Run Backend (Vishal)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```
API runs on http://localhost:8000/docs

### 4. Run Frontend (Chinmay)
*Note: The frontend is configured to use the local mock API by default so UI development isn't blocked by backend progress. See `.env` (`NEXT_PUBLIC_USE_MOCK_API=true`).*
```bash
cd frontend
npm install
npm run dev
```
UI runs on http://localhost:3000

## Ownership & Contribution
- Please review `docs/ownership.md` before making sweeping changes.
- Ensure any schema changes are documented in `contracts/api-contract.md` or `contracts/ai-contract.md`.
