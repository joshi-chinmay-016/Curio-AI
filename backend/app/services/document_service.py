from pathlib import Path
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from fastapi import UploadFile, HTTPException, status
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.schemas.document import DocumentResponse, DocumentListResponse
from backend.app.storage import get_storage
from backend.app.core.config import settings


class DocumentService:
    def __init__(self, storage=None):
        self.repo = DocumentRepository()
        self._storage = storage or get_storage()

    @property
    def storage(self):
        return self._storage

    def upload_document(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
        file: UploadFile,
    ) -> DocumentResponse:
        # Validate file type first
        filename = file.filename or ""
        mime_type = file.content_type or "application/octet-stream"
        
        try:
            extension = self._storage.validate_file_type(filename, mime_type)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Generate document ID upfront for storage path
        import uuid
        document_id = uuid.uuid4()

        # Stream file to storage
        try:
            storage_path, actual_size, content_hash = self._storage.save_uploaded_file(
                upload_file=file,
                user_id=user_id,
                document_id=document_id,
                filename=filename,
                mime_type=mime_type,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store file")

        # Persist document metadata
        try:
            db_doc = self.repo.create(
                db,
                user_id=user_id,
                filename=filename,
                file_size=actual_size,
                mime_type=mime_type,
                storage_path=str(storage_path),
                content_hash=content_hash,
            )
        except Exception as e:
            # Cleanup stored file on DB failure
            self._storage.delete_file(storage_path)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create document record")

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
        # Get document first to access storage_path
        db_doc = self.repo.get_by_id_and_user(db, document_id, user_id)
        if not db_doc:
            return False
        
        # Delete database record
        deleted = self.repo.delete_by_id_and_user(db, document_id, user_id)
        if not deleted:
            return False
        
        # Delete physical file if it exists
        if db_doc.storage_path:
            self._storage.delete_file(Path(db_doc.storage_path))
        
        return True
