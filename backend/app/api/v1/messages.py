from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.db.session import get_db
from backend.app.schemas.message import MessageCreate, ChatTurnResponse, MessageResponse
from backend.app.services.chat_service import ChatService

router = APIRouter()
chat_service = ChatService()

@router.post("/sessions/{session_id}/messages", response_model=ChatTurnResponse)
def send_message(
    session_id: UUID,
    message_in: MessageCreate,
    db: SQLAlchemySession = Depends(get_db)
):
    try:
        return chat_service.send_message(db, session_id, message_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
def get_messages(session_id: UUID, db: SQLAlchemySession = Depends(get_db)):
    return chat_service.get_messages(db, session_id)
