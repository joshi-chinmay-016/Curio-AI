"""
Tests for Task 5.5 - Vector Database Schema & Persistent Chunk Storage.

Tests cover:
1. Creating a document and its chunks
2. Persisting chunk text, indexes, offsets, and metadata
3. Stable ordering when chunks are retrieved
4. Unique chunk indexes within a document
5. Multiple documents maintaining separate chunk sets
6. Unembedded chunks being valid
7. Embedding persistence when a valid vector representation is configured
8. Ownership-scoped access and cross-user isolation
9. Chunk deletion when the parent document is deleted (CASCADE)
10. Replacing a document's chunks atomically
11. Rollback after a failed batch operation
12. Existing document upload, ownership, storage, and extraction behavior remaining intact
13. Migration compatibility and a single valid migration head
"""

import pytest
from uuid import uuid4
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.user import User
from backend.app.repositories.document_chunk_repository import DocumentChunkRepository
from backend.app.repositories.document_repository import DocumentRepository


def create_test_user(db, email=None):
    """Create a test user in the database."""
    user_email = email or f"test_{uuid4().hex[:8]}@curio.ai"
    user = User(email=user_email, hashed_password="test", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_document(db, user_id, **kwargs):
    """Create a test document in the database."""
    doc = Document(
        id=uuid4(),
        user_id=user_id,
        filename=kwargs.get("filename", "test.pdf"),
        file_size=kwargs.get("file_size", 1024),
        mime_type=kwargs.get("mime_type", "application/pdf"),
        status=kwargs.get("status", "PROCESSED"),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


class TestDocumentChunkModel:
    """Test DocumentChunk model creation and constraints."""

    def test_create_chunk_with_all_fields(self, test_db_session):
        """Test creating a chunk with all fields."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            text="Test chunk content",
            start_char=0,
            end_char=18,
            chunk_metadata={"page_number": 0},
            embedding=None,
            embedding_model=None,
        )
        test_db_session.add(chunk)
        test_db_session.commit()
        test_db_session.refresh(chunk)
        
        assert chunk.id is not None
        assert chunk.document_id == doc.id
        assert chunk.chunk_index == 0
        assert chunk.text == "Test chunk content"
        assert chunk.start_char == 0
        assert chunk.end_char == 18
        assert chunk.chunk_metadata == {"page_number": 0}
        assert chunk.embedding is None
        assert chunk.embedding_model is None
        assert chunk.created_at is not None
        assert chunk.updated_at is not None

    def test_chunk_unique_index_per_document(self, test_db_session):
        """Test unique constraint on (document_id, chunk_index)."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        chunk1 = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            text="First chunk",
        )
        test_db_session.add(chunk1)
        test_db_session.commit()
        
        # Try to insert another chunk with same index
        chunk2 = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            text="Duplicate chunk",
        )
        test_db_session.add(chunk2)
        
        with pytest.raises(Exception) as exc:
            test_db_session.commit()
        # Should be integrity error
        assert "uq_document_chunk_index" in str(exc.value) or "unique" in str(exc.value).lower()
        test_db_session.rollback()

    def test_multiple_documents_separate_chunks(self, test_db_session):
        """Test that different documents can have same chunk indexes."""
        user = create_test_user(test_db_session)
        doc1 = create_test_document(test_db_session, user.id, filename="doc1.pdf")
        doc2 = create_test_document(test_db_session, user.id, filename="doc2.pdf")
        
        chunk1 = DocumentChunk(document_id=doc1.id, chunk_index=0, text="Doc1 chunk 0")
        chunk2 = DocumentChunk(document_id=doc2.id, chunk_index=0, text="Doc2 chunk 0")
        test_db_session.add_all([chunk1, chunk2])
        test_db_session.commit()
        
        assert chunk1.id is not None
        assert chunk2.id is not None
        assert chunk1.document_id != chunk2.document_id


class TestDocumentChunkRepository:
    """Test DocumentChunkRepository operations."""

    @pytest.fixture
    def repo(self):
        return DocumentChunkRepository()

    def test_create_chunks_batch(self, test_db_session, repo):
        """Test inserting a batch of chunks for a document."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        chunks = [
            DocumentChunk(document_id=doc.id, chunk_index=0, text="First chunk", start_char=0, end_char=11),
            DocumentChunk(document_id=doc.id, chunk_index=1, text="Second chunk", start_char=12, end_char=24),
        ]
        
        created = repo.create_chunks(test_db_session, doc.id, chunks)
        
        assert len(created) == 2
        assert created[0].id is not None
        assert created[1].id is not None
        assert created[0].chunk_index == 0
        assert created[1].chunk_index == 1

    def test_get_chunks_by_document_ordered(self, test_db_session, repo):
        """Test retrieving chunks in stable chunk_index order."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        chunks = [
            DocumentChunk(document_id=doc.id, chunk_index=2, text="Third"),
            DocumentChunk(document_id=doc.id, chunk_index=0, text="First"),
            DocumentChunk(document_id=doc.id, chunk_index=1, text="Second"),
        ]
        repo.create_chunks(test_db_session, doc.id, chunks)
        
        retrieved = repo.get_chunks_by_document(test_db_session, doc.id, user.id)
        
        assert len(retrieved) == 3
        assert retrieved[0].chunk_index == 0
        assert retrieved[1].chunk_index == 1
        assert retrieved[2].chunk_index == 2
        assert retrieved[0].text == "First"
        assert retrieved[1].text == "Second"
        assert retrieved[2].text == "Third"

    def test_get_chunk_by_id_with_ownership(self, test_db_session, repo):
        """Test retrieving chunk by ID with ownership verification."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        chunks = [DocumentChunk(document_id=doc.id, chunk_index=0, text="Test chunk")]
        repo.create_chunks(test_db_session, doc.id, chunks)
        chunk_id = chunks[0].id
        
        # Owner can retrieve
        retrieved = repo.get_chunk_by_id(test_db_session, chunk_id, user.id)
        assert retrieved is not None
        assert retrieved.id == chunk_id
        
        # Other user cannot retrieve
        other_user = create_test_user(test_db_session)
        retrieved = repo.get_chunk_by_id(test_db_session, chunk_id, other_user.id)
        assert retrieved is None

    def test_delete_chunks_by_document(self, test_db_session, repo):
        """Test deleting all chunks for a document."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        chunks = [
            DocumentChunk(document_id=doc.id, chunk_index=0, text="Chunk 1"),
            DocumentChunk(document_id=doc.id, chunk_index=1, text="Chunk 2"),
        ]
        repo.create_chunks(test_db_session, doc.id, chunks)
        
        # Delete chunks
        result = repo.delete_chunks_by_document(test_db_session, doc.id, user.id)
        assert result is True
        
        # Verify chunks are gone
        retrieved = repo.get_chunks_by_document(test_db_session, doc.id, user.id)
        assert len(retrieved) == 0
        
        # Cross-user deletion should fail
        other_user = create_test_user(test_db_session)
        result = repo.delete_chunks_by_document(test_db_session, doc.id, other_user.id)
        assert result is False

    def test_replace_chunks_atomically(self, test_db_session, repo):
        """Test replacing all chunks for a document atomically."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        # Initial chunks
        old_chunks = [
            DocumentChunk(document_id=doc.id, chunk_index=0, text="Old 1"),
            DocumentChunk(document_id=doc.id, chunk_index=1, text="Old 2"),
        ]
        repo.create_chunks(test_db_session, doc.id, old_chunks)
        
        # Replace with new chunks
        new_chunks = [
            DocumentChunk(chunk_index=0, text="New 1"),
            DocumentChunk(chunk_index=1, text="New 2"),
            DocumentChunk(chunk_index=2, text="New 3"),
        ]
        created = repo.replace_chunks_for_document(test_db_session, doc.id, user.id, new_chunks)
        
        assert len(created) == 3
        assert created[0].text == "New 1"
        assert created[2].text == "New 3"
        
        # Verify old chunks are gone
        retrieved = repo.get_chunks_by_document(test_db_session, doc.id, user.id)
        assert len(retrieved) == 3
        assert all(c.text.startswith("New") for c in retrieved)

    def test_replace_chunks_rollback_on_failure(self, test_db_session, repo):
        """Test that failed batch replacement rolls back."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        old_chunks = [DocumentChunk(document_id=doc.id, chunk_index=0, text="Old")]
        repo.create_chunks(test_db_session, doc.id, old_chunks)
        
        # Try to replace with invalid chunks (duplicate index)
        new_chunks = [
            DocumentChunk(chunk_index=0, text="New 1"),
            DocumentChunk(chunk_index=0, text="New 2 duplicate"),  # Duplicate index
        ]
        
        with pytest.raises(Exception):
            repo.replace_chunks_for_document(test_db_session, doc.id, user.id, new_chunks)
        
        # Rollback the session after the exception
        test_db_session.rollback()
        
        # Old chunk should still exist
        retrieved = repo.get_chunks_by_document(test_db_session, doc.id, user.id)
        assert len(retrieved) == 1
        assert retrieved[0].text == "Old"

    def test_update_chunk_embedding(self, test_db_session, repo):
        """Test updating a chunk's embedding."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        chunks = [DocumentChunk(document_id=doc.id, chunk_index=0, text="Test chunk")]
        repo.create_chunks(test_db_session, doc.id, chunks)
        chunk_id = chunks[0].id
        
        # Update embedding
        updated = repo.update_chunk_embedding(
            test_db_session, chunk_id, user.id,
            embedding="[0.1, 0.2, 0.3]",
            embedding_model="text-embedding-3-small"
        )
        
        assert updated is not None
        assert updated.embedding == "[0.1, 0.2, 0.3]"
        assert updated.embedding_model == "text-embedding-3-small"
        
        # Cross-user update should fail
        other_user = create_test_user(test_db_session)
        updated = repo.update_chunk_embedding(test_db_session, chunk_id, other_user.id, "[0.4]", "model")
        assert updated is None

    def test_count_chunks(self, test_db_session, repo):
        """Test counting chunks for a document."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        assert repo.count_chunks(test_db_session, doc.id, user.id) == 0
        
        chunks = [
            DocumentChunk(document_id=doc.id, chunk_index=i, text=f"Chunk {i}")
            for i in range(5)
        ]
        repo.create_chunks(test_db_session, doc.id, chunks)
        
        assert repo.count_chunks(test_db_session, doc.id, user.id) == 5
        
        # Cross-user should return 0
        other_user = create_test_user(test_db_session)
        assert repo.count_chunks(test_db_session, doc.id, other_user.id) == 0

    def test_unembedded_chunks_valid(self, test_db_session, repo):
        """Test that unembedded chunks are valid database records."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        chunks = [DocumentChunk(document_id=doc.id, chunk_index=0, text="No embedding")]
        repo.create_chunks(test_db_session, doc.id, chunks)
        
        retrieved = repo.get_chunks_by_document(test_db_session, doc.id, user.id)
        assert len(retrieved) == 1
        assert retrieved[0].embedding is None
        assert retrieved[0].embedding_model is None


class TestCascadeDeletion:
    """Test cascade deletion behavior."""

    def test_chunk_deleted_when_document_deleted(self, test_db_session, test_user):
        """Test that chunks are deleted when parent document is deleted (CASCADE)."""
        from backend.app.repositories.document_repository import DocumentRepository
        from backend.app.repositories.document_chunk_repository import DocumentChunkRepository
        
        doc_repo = DocumentRepository()
        chunk_repo = DocumentChunkRepository()
        
        # Create document
        doc = doc_repo.create(
            test_db_session, test_user.id,
            filename="test.pdf", file_size=1024,
            mime_type="application/pdf",
            storage_path="/tmp/test.pdf",
            content_hash="abc123"
        )
        
        # Create chunks
        chunks = [
            DocumentChunk(document_id=doc.id, chunk_index=0, text="Chunk 1"),
            DocumentChunk(document_id=doc.id, chunk_index=1, text="Chunk 2"),
        ]
        chunk_repo.create_chunks(test_db_session, doc.id, chunks)
        
        # Verify chunks exist
        assert chunk_repo.count_chunks(test_db_session, doc.id, test_user.id) == 2
        
        # Delete document
        doc_repo.delete_by_id_and_user(test_db_session, doc.id, test_user.id)
        
        # Chunks should be cascade deleted
        assert chunk_repo.count_chunks(test_db_session, doc.id, test_user.id) == 0


class TestDocumentIntegration:
    """Test that existing document behavior remains intact."""

    def test_document_upload_ownership_storage_extraction(self, test_db_session, test_user, tmp_path):
        """Test existing document upload, ownership, storage, extraction behavior."""
        from backend.app.services.document_service import DocumentService
        from backend.app.storage.local import LocalStorage
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        # Upload document
        from io import BytesIO
        from fastapi import UploadFile
        
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Hello World) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000218 00000 n
0000000318 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
406
%%EOF"""
        
        from io import BytesIO
        from fastapi import UploadFile
        
        upload_file = UploadFile(filename="test.pdf", file=BytesIO(pdf_content), headers={"content-type": "application/pdf"})
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        assert response.document_id is not None
        assert response.filename == "test.pdf"
        assert response.status == "UPLOADED"
        
        # Process document
        processed = service.process_document(test_db_session, response.document_id, test_user.id)
        assert processed.status == "PROCESSED"
        assert processed.page_count == 1
        
        # Verify document has chunk_count field (from model)
        from backend.app.models.document import Document
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert db_doc.chunk_count == 0  # Not yet chunked


class TestMigrationCompatibility:
    """Test migration compatibility and single valid head."""

    def test_migration_head_single(self):
        """Test that migration head is single."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        
        config = Config("backend/alembic.ini")
        script = ScriptDirectory.from_config(config)
        heads = script.get_heads()
        assert len(heads) == 1, f"Expected single head, got: {heads}"

    def test_document_chunks_table_exists(self, test_db_session):
        """Test that document_chunks table exists after migration."""
        from sqlalchemy import inspect
        
        inspector = inspect(test_db_session.bind)
        tables = inspector.get_table_names()
        assert 'document_chunks' in tables
        
        columns = [c['name'] for c in inspector.get_columns('document_chunks')]
        expected_columns = {'id', 'document_id', 'chunk_index', 'text', 'start_char', 'end_char', 
                           'chunk_metadata', 'embedding', 'embedding_model', 'created_at', 'updated_at'}
        assert expected_columns.issubset(set(columns))
        
        # Check indexes (PostgreSQL may name PK index differently)
        indexes = [i['name'] for i in inspector.get_indexes('document_chunks')]
        # Primary key index exists (name varies by PostgreSQL - check for any index on 'id')
        pk_columns = [i for i in inspector.get_indexes('document_chunks') if 'id' in i.get('column_names', [])]
        # At minimum there should be some indexes
        assert len(indexes) >= 2  # PK + unique constraint + document_id index
        assert 'ix_document_chunks_document_id' in indexes
        assert 'uq_document_chunk_index' in indexes
        
        # Check foreign key
        fks = inspector.get_foreign_keys('document_chunks')
        assert len(fks) == 1
        assert fks[0]['referred_table'] == 'documents'
        assert fks[0]['options'].get('ondelete') == 'CASCADE'