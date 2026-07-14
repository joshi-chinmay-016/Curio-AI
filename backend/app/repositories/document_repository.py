from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.models.document import Document

class DocumentRepository:
    def create(self, db: SQLAlchemySession, filename: str, file_size: int, mime_type: str) -> Document:
        db_doc = Document(
            filename=filename,
            file_size=file_size,
            mime_type=mime_type
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        return db_doc

    def get(self, db: SQLAlchemySession, id: UUID) -> Optional[Document]:
        return db.query(Document).filter(Document.id == id).first()
