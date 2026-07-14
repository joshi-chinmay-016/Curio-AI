from fastapi import APIRouter
from backend.app.api.v1 import sessions, messages, documents, reports

api_router = APIRouter()

api_router.include_router(sessions.router, tags=["Sessions"])
api_router.include_router(messages.router, tags=["Messages"])
api_router.include_router(documents.router, tags=["Documents"])
api_router.include_router(reports.router, tags=["Reports"])
