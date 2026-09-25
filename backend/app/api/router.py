from fastapi import APIRouter
from backend.app.api.v1 import auth, sessions, messages, documents, reports, progress, teacher_interventions

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(sessions.router, tags=["Sessions"])
api_router.include_router(messages.router, tags=["Messages"])
api_router.include_router(documents.router, tags=["Documents"])
api_router.include_router(reports.router, tags=["Reports"])
api_router.include_router(progress.router)
api_router.include_router(teacher_interventions.router)
