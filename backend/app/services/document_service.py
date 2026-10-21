from pathlib import Path
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from fastapi import UploadFile, HTTPException, status
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.repositories.document_chunk_repository import DocumentChunkRepository
from backend.app.models.document import DocumentChunk
from backend.app.schemas.document import DocumentResponse, DocumentListResponse
from backend.app.storage import get_storage
from backend.app.extraction import ExtractionService, ExtractionError
from backend.app.chunking import ChunkingService, ChunkingError
from backend.app.embeddings import create_embedding_service
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

        # Persist document metadata with the pre-generated document_id
        try:
            db_doc = self.repo.create(
                db,
                user_id=user_id,
                filename=filename,
                file_size=actual_size,
                mime_type=mime_type,
                storage_path=str(storage_path),
                content_hash=content_hash,
                document_id=document_id,
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

    def process_document(self, db: SQLAlchemySession, document_id: UUID, user_id: UUID) -> DocumentResponse:
        """
        Process a document through the durable, resumable RAG ingestion pipeline:
        EXTRACTING -> CHUNKING -> EMBEDDING -> BUILDING_CURRICULUM -> READY
        """
        # Verify ownership and get document
        db_doc = self.repo.get_by_id_and_user(db, document_id, user_id)
        if not db_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
        # Verify storage path exists
        if not db_doc.storage_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no stored file to process"
            )
        
        storage_path = Path(db_doc.storage_path)
        if not storage_path.exists():
            # File missing - mark as failed
            self.repo.update_processing_result(
                db, document_id, user_id,
                status="FAILED",
                processing_error="Source file not found in storage"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source file not found in storage"
            )

        chunk_repo = DocumentChunkRepository()
        existing_chunks = chunk_repo.get_chunks_by_document(db, document_id, user_id)
        page_count = db_doc.page_count
        
        # Stage 1: Extraction & Chunking (if not already extracted/chunked)
        if not existing_chunks:
            # 1. EXTRACTING
            self.repo.update_status(db, document_id, user_id, status="EXTRACTING", processing_error=None)
            extraction_service = ExtractionService()
            try:
                extraction_res = extraction_service.extract(storage_path, db_doc.mime_type)
                page_count = extraction_res.page_count
            except ExtractionError as e:
                self.repo.update_processing_result(
                    db, document_id, user_id,
                    status="FAILED",
                    processing_error=e.message
                )
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Extraction failed: {e.message}"
                )
            
            # 2. CHUNKING
            self.repo.update_status(db, document_id, user_id, status="CHUNKING", processing_error=None)
            chunking_service = ChunkingService(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            try:
                chunking_res = chunking_service.chunk_text(
                    extraction_res.text,
                    extraction_metadata=extraction_res.extraction_metadata
                )
                
                orm_chunks = [
                    DocumentChunk(
                        document_id=document_id,
                        chunk_index=c.chunk_index,
                        text=c.text,
                        start_char=c.start_char,
                        end_char=c.end_char,
                        chunk_metadata=c.metadata,
                    )
                    for c in chunking_res.chunks
                ]
                existing_chunks = chunk_repo.replace_chunks_for_document(db, document_id, user_id, orm_chunks)
            except Exception as e:
                self.repo.update_processing_result(
                    db, document_id, user_id,
                    status="FAILED",
                    processing_error=f"Chunking failed: {e}"
                )
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Chunking failed: {e}"
                )

        # Stage 2: EMBEDDING & INDEXING
        self.repo.update_status(db, document_id, user_id, status="EMBEDDING", processing_error=None)
        try:
            emb_service = create_embedding_service()
            emb_service.generate_and_persist_embeddings(db, document_id, user_id)
        except Exception as e:
            self.repo.update_status(
                db, document_id, user_id,
                status="FAILED",
                processing_error=f"Embedding generation failed: {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Embedding generation failed: {e}"
            )

        # Stage 3: BUILDING CURRICULUM
        self.repo.update_status(db, document_id, user_id, status="BUILDING_CURRICULUM", processing_error=None)
        try:
            from backend.app.ai.document_curriculum import DocumentCurriculumBuilder
            builder = DocumentCurriculumBuilder()
            builder.build_curriculum(
                document_id=str(document_id),
                chunks=existing_chunks,
                filename=db_doc.filename,
                page_count=page_count,
            )
        except Exception as e:
            # Curriculum build non-fatal warning; can also be hydrated during chat turn
            pass

        # Stage 4: Mark READY (and PROCESSED for backward compatibility)
        self.repo.update_processing_result(
            db, document_id, user_id,
            status="READY",
            page_count=page_count,
            processing_error=None
        )
        self.repo.update_chunk_count(db, document_id, user_id, len(existing_chunks))
        db.refresh(db_doc)

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
