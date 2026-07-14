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
        return DocumentResponse.model_validate(db_doc)

    def get_document(self, db: SQLAlchemySession, document_id: UUID) -> Optional[DocumentResponse]:
        db_doc = self.repo.get(db, document_id)
        if not db_doc:
            return None
        return DocumentResponse.model_validate(db_doc)
