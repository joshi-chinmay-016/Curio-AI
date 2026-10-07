from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.schemas.document import DocumentResponse, DocumentListResponse

class DocumentService:
    def __init__(self):
        self.repo = DocumentRepository()

    def upload_document(self, db: SQLAlchemySession, user_id: UUID, filename: str, file_size: int, mime_type: str) -> DocumentResponse:
        db_doc = self.repo.create(db, user_id, filename, file_size, mime_type)
        return DocumentResponse(
            document_id=db_doc.id,
            filename=db_doc.filename,
            file_size=db_doc.file_size,
            mime_type=db_doc.mime_type,
            status=db_doc.status,
            page_count=db_doc.page_count,
            chunk_count=db_doc.chunk_count,
            created_at=db_doc.created_at
        )

    def get_document(self, db: SQLAlchemySession, document_id: UUID, user_id: UUID) -> Optional[DocumentResponse]:
        db_doc = self.repo.get_by_id_and_user(db, document_id, user_id)
        if not db_doc:
            return None
        return DocumentResponse(
            document_id=db_doc.id,
            filename=db_doc.filename,
            file_size=db_doc.file_size,
            mime_type=db_doc.mime_type,
            status=db_doc.status,
            page_count=db_doc.page_count,
            chunk_count=db_doc.chunk_count,
            created_at=db_doc.created_at
        )

    def list_documents(self, db: SQLAlchemySession, user_id: UUID, page: int = 1, page_size: int = 20) -> DocumentListResponse:
        documents, total = self.repo.list_by_user(db, user_id, page, page_size)
        return DocumentListResponse(
            documents=[
                DocumentResponse(
                    document_id=doc.id,
                    filename=doc.filename,
                    file_size=doc.file_size,
                    mime_type=doc.mime_type,
                    status=doc.status,
                    page_count=doc.page_count,
                    chunk_count=doc.chunk_count,
                    created_at=doc.created_at
                )
                for doc in documents
            ],
            total=total,
            page=page,
            page_size=page_size
        )

    def delete_document(self, db: SQLAlchemySession, document_id: UUID, user_id: UUID) -> bool:
        return self.repo.delete_by_id_and_user(db, document_id, user_id)
