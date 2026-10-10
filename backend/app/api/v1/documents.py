from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.api.deps import get_current_active_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.document import DocumentResponse, DocumentListResponse
from backend.app.services.document_service import DocumentService

router = APIRouter()
doc_service = DocumentService()

@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return doc_service.upload_document(db, user_id=current_user.id, file=file)

@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    doc = doc_service.get_document(db, document_id, current_user.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    return doc_service.list_documents(db, current_user.id, page, page_size)

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    success = doc_service.delete_document(db, document_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/documents/{document_id}/process", response_model=DocumentResponse)
def process_document(
    document_id: UUID,
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Trigger text extraction for a document.
    
    Flow: UPLOADED -> PROCESSING -> PROCESSED (or FAILED)
    
    Does not perform chunking, embedding, or AI processing.
    Extraction result is consumed by downstream chunking infrastructure (Task 5.4).
    """
    try:
        return doc_service.process_document(db, document_id, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Processing failed")
