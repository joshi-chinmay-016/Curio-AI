from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.db.session import get_db
from backend.app.schemas.document import DocumentResponse
from backend.app.services.document_service import DocumentService

router = APIRouter()
doc_service = DocumentService()

@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    db: SQLAlchemySession = Depends(get_db)
):
    # Retrieve file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    return doc_service.upload_document(
        db,
        filename=file.filename,
        file_size=file_size,
        mime_type=file.content_type
    )

@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: UUID, db: SQLAlchemySession = Depends(get_db)):
    doc = doc_service.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
