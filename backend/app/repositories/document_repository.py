from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.models.document import Document


class DocumentRepository:
    def create(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
        filename: str,
        file_size: int,
        mime_type: str,
        storage_path: str = None,
        content_hash: str = None,
        document_id: UUID = None,
    ) -> Document:
        db_doc = Document(
            id=document_id,
            user_id=user_id,
            filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            storage_path=storage_path,
            content_hash=content_hash,
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        return db_doc

    def get(self, db: SQLAlchemySession, id: UUID) -> Optional[Document]:
        return db.query(Document).filter(Document.id == id).first()

    def get_by_id_and_user(self, db: SQLAlchemySession, document_id: UUID, user_id: UUID) -> Optional[Document]:
        return db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()

    def list_by_user(self, db: SQLAlchemySession, user_id: UUID, page: int = 1, page_size: int = 20):
        query = db.query(Document).filter(Document.user_id == user_id)
        total = query.count()
        documents = query.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return documents, total

    def delete_by_id_and_user(self, db: SQLAlchemySession, document_id: UUID, user_id: UUID) -> bool:
        db_doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
        if not db_doc:
            return False
        db.delete(db_doc)
        db.commit()
        return True

    def update_status(self, db: SQLAlchemySession, document_id: UUID, user_id: UUID, status: str, processing_error: str = None) -> Optional[Document]:
        db_doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
        if not db_doc:
            return None
        db_doc.status = status
        if processing_error is not None:
            db_doc.processing_error = processing_error
        db.commit()
        db.refresh(db_doc)
        return db_doc

    def update_processing_result(
        self,
        db: SQLAlchemySession,
        document_id: UUID,
        user_id: UUID,
        status: str,
        page_count: Optional[int] = None,
        processing_error: Optional[str] = None,
    ) -> Optional[Document]:
        """
        Update document status, page_count, and processing_error atomically.
        
        Used after extraction to mark PROCESSED with page_count or FAILED with error.
        """
        db_doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
        if not db_doc:
            return None
        db_doc.status = status
        if page_count is not None:
            db_doc.page_count = page_count
        if processing_error is not None:
            db_doc.processing_error = processing_error
        elif status == "PROCESSED":
            # Clear error on successful processing
            db_doc.processing_error = None
        db.commit()
        db.refresh(db_doc)
        return db_doc
