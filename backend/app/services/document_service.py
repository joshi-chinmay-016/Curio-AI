from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.schemas.document import DocumentResponse

class DocumentService:
    def __init__(self):
        self.repo = DocumentRepository()

    def upload_document(self, db: SQLAlchemySession, filename: str, file_size: int, mime_type: str) -> DocumentResponse:
        db_doc = self.repo.create(db, filename, file_size, mime_type)
        return DocumentResponse(
            document_id=db_doc.id,
            filename=db_doc.filename,
            file_size=db_doc.file_size,
            mime_type=db_doc.mime_type,
            created_at=db_doc.created_at
        )

    def get_document(self, db: SQLAlchemySession, document_id: UUID) -> Optional[DocumentResponse]:
        db_doc = self.repo.get(db, document_id)
        if not db_doc:
            return None
        return DocumentResponse(
            document_id=db_doc.id,
            filename=db_doc.filename,
            file_size=db_doc.file_size,
            mime_type=db_doc.mime_type,
            created_at=db_doc.created_at
        )
