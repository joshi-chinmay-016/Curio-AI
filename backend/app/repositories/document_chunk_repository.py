"""Repository for document chunks persistence."""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.models.document import DocumentChunk


class DocumentChunkRepository:
    """Repository for managing persistent document chunks."""

    def create_chunks(
        self,
        db: SQLAlchemySession,
        document_id: UUID,
        chunks: List[DocumentChunk],
    ) -> List[DocumentChunk]:
        """
        Insert a batch of chunks for a document.
        
        Args:
            db: Database session
            document_id: Parent document UUID
            chunks: List of DocumentChunk objects to insert
            
        Returns:
            List of created DocumentChunk objects
        """
        for chunk in chunks:
            chunk.document_id = document_id
            db.add(chunk)
        db.commit()
        for chunk in chunks:
            db.refresh(chunk)
        return chunks

    def get_chunks_by_document(
        self,
        db: SQLAlchemySession,
        document_id: UUID,
        user_id: UUID,
    ) -> List[DocumentChunk]:
        """
        List chunks for a document in stable chunk_index order.
        
        Args:
            db: Database session
            document_id: Parent document UUID
            user_id: User ID for ownership verification
            
        Returns:
            List of DocumentChunk objects ordered by chunk_index
        """
        from backend.app.models.document import Document
        # Verify ownership through document
        doc = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        if not doc:
            return []
        
        return db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()

    def get_chunk_by_id(
        self,
        db: SQLAlchemySession,
        chunk_id: UUID,
        user_id: UUID,
    ) -> Optional[DocumentChunk]:
        """
        Retrieve a chunk by ID only within a verified ownership scope.
        
        Args:
            db: Database session
            chunk_id: Chunk UUID
            user_id: User ID for ownership verification
            
        Returns:
            DocumentChunk if found and owned by user, None otherwise
        """
        from backend.app.models.document import Document
        return db.query(DocumentChunk).join(
            Document, DocumentChunk.document_id == Document.id
        ).filter(
            DocumentChunk.id == chunk_id,
            Document.user_id == user_id
        ).first()

    def delete_chunks_by_document(
        self,
        db: SQLAlchemySession,
        document_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Delete all chunks for a specific owned document.
        
        Args:
            db: Database session
            document_id: Parent document UUID
            user_id: User ID for ownership verification
            
        Returns:
            True if chunks were deleted, False if document not found/not owned
        """
        from backend.app.models.document import Document
        doc = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        if not doc:
            return False
        
        deleted = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).delete()
        db.commit()
        return deleted > 0

    def replace_chunks_for_document(
        self,
        db: SQLAlchemySession,
        document_id: UUID,
        user_id: UUID,
        new_chunks: List[DocumentChunk],
    ) -> List[DocumentChunk]:
        """
        Atomically replace all chunks for a document with new chunks.
        
        Args:
            db: Database session
            document_id: Parent document UUID
            user_id: User ID for ownership verification
            new_chunks: List of new DocumentChunk objects
            
        Returns:
            List of created DocumentChunk objects
            
        Raises:
            ValueError: If document not found or not owned by user
        """
        from backend.app.models.document import Document
        doc = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        if not doc:
            raise ValueError("Document not found or not owned by user")
        
        # Delete existing chunks
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).delete()
        
        # Insert new chunks
        for chunk in new_chunks:
            chunk.document_id = document_id
            db.add(chunk)
        db.commit()
        for chunk in new_chunks:
            db.refresh(chunk)
        return new_chunks

    def update_chunk_embedding(
        self,
        db: SQLAlchemySession,
        chunk_id: UUID,
        user_id: UUID,
        embedding: str,
        embedding_model: str,
    ) -> Optional[DocumentChunk]:
        """
        Update an existing chunk's embedding.
        
        Args:
            db: Database session
            chunk_id: Chunk UUID
            user_id: User ID for ownership verification
            embedding: Embedding vector as string
            embedding_model: Embedding model name
            
        Returns:
            Updated DocumentChunk if found and owned, None otherwise
        """
        chunk = self.get_chunk_by_id(db, chunk_id, user_id)
        if not chunk:
            return None
        
        chunk.embedding = embedding
        chunk.embedding_model = embedding_model
        db.commit()
        db.refresh(chunk)
        return chunk

    def count_chunks(
        self,
        db: SQLAlchemySession,
        document_id: UUID,
        user_id: UUID,
    ) -> int:
        """
        Count chunks for a document.
        
        Args:
            db: Database session
            document_id: Parent document UUID
            user_id: User ID for ownership verification
            
        Returns:
            Number of chunks for the document
        """
        from backend.app.models.document import Document
        doc = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        if not doc:
            return 0
        
        return db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).count()