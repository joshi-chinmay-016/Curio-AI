"""
Tests for Task 5.1 - Document Ownership & Status.

Tests cover:
- Document creation with authenticated owner
- Document ownership persistence
- GET own document
- Cross-user GET -> 404
- List documents -> only owner's documents
- Cross-user DELETE -> 404
- Own DELETE
- Unauthenticated access -> 401
- Status persistence
- Migration/schema compatibility
- Existing session/document relationship
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.session import Session
from backend.app.core.security import create_access_token


class TestDocumentOwnership:
    """Test document ownership and access control."""

    def create_test_user(self, db: Session, email: str = None) -> User:
        """Create a test user in the database."""
        user_email = email or f"test_{uuid4().hex[:8]}@curio.ai"
        user = User(email=user_email, hashed_password="test", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_auth_headers(self, user: User) -> dict:
        """Get authorization headers for a user."""
        token = create_access_token(subject=str(user.id))
        return {"Authorization": f"Bearer {token}"}

    def test_upload_document_creates_with_owner(self, test_db_session: Session, test_user: User):
        """Test that uploaded document is associated with the authenticated user."""
        from backend.app.services.document_service import DocumentService

        service = DocumentService()
        doc = service.upload_document(
            test_db_session,
            user_id=test_user.id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )

        assert doc.document_id is not None
        assert doc.filename == "test.pdf"
        assert doc.file_size == 1024
        assert doc.mime_type == "application/pdf"
        assert doc.status == "UPLOADED"
        assert doc.chunk_count == 0
        assert doc.page_count is None
        assert doc.created_at is not None

        # Verify in database
        db_doc = test_db_session.query(Document).filter(Document.id == doc.document_id).first()
        assert db_doc is not None
        assert db_doc.user_id == test_user.id
        assert db_doc.status == "UPLOADED"

    def test_get_own_document(self, test_db_session: Session, test_user: User):
        """Test that a user can retrieve their own document."""
        from backend.app.services.document_service import DocumentService

        service = DocumentService()
        created = service.upload_document(
            test_db_session,
            user_id=test_user.id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )

        retrieved = service.get_document(test_db_session, created.document_id, test_user.id)
        assert retrieved is not None
        assert retrieved.document_id == created.document_id
        assert retrieved.filename == "test.pdf"

    def test_get_cross_user_document_returns_none(self, test_db_session: Session):
        """Test that a user cannot retrieve another user's document."""
        from backend.app.services.document_service import DocumentService

        user_a = self.create_test_user(test_db_session, "user_a@curio.ai")
        user_b = self.create_test_user(test_db_session, "user_b@curio.ai")

        service = DocumentService()
        doc = service.upload_document(
            test_db_session,
            user_id=user_a.id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )

        # User B tries to access User A's document
        retrieved = service.get_document(test_db_session, doc.document_id, user_b.id)
        assert retrieved is None

    def test_list_documents_only_own(self, test_db_session: Session):
        """Test that listing documents returns only the owner's documents."""
        from backend.app.services.document_service import DocumentService

        user_a = self.create_test_user(test_db_session, "user_a@curio.ai")
        user_b = self.create_test_user(test_db_session, "user_b@curio.ai")

        service = DocumentService()
        
        # User A creates 2 documents
        service.upload_document(test_db_session, user_a.id, "doc1.pdf", 1024, "application/pdf")
        service.upload_document(test_db_session, user_a.id, "doc2.pdf", 2048, "application/pdf")
        
        # User B creates 1 document
        service.upload_document(test_db_session, user_b.id, "doc3.pdf", 512, "application/pdf")

        # User A lists documents
        result_a = service.list_documents(test_db_session, user_a.id, page=1, page_size=10)
        assert result_a.total == 2
        assert len(result_a.documents) == 2
        assert all(d.filename in ["doc1.pdf", "doc2.pdf"] for d in result_a.documents)

        # User B lists documents
        result_b = service.list_documents(test_db_session, user_b.id, page=1, page_size=10)
        assert result_b.total == 1
        assert len(result_b.documents) == 1
        assert result_b.documents[0].filename == "doc3.pdf"

    def test_delete_own_document(self, test_db_session: Session, test_user: User):
        """Test that a user can delete their own document."""
        from backend.app.services.document_service import DocumentService

        service = DocumentService()
        doc = service.upload_document(
            test_db_session,
            user_id=test_user.id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )

        result = service.delete_document(test_db_session, doc.document_id, test_user.id)
        assert result is True

        # Verify document is deleted
        db_doc = test_db_session.query(Document).filter(Document.id == doc.document_id).first()
        assert db_doc is None

    def test_delete_cross_user_document_returns_false(self, test_db_session: Session):
        """Test that a user cannot delete another user's document."""
        from backend.app.services.document_service import DocumentService

        user_a = self.create_test_user(test_db_session, "user_a@curio.ai")
        user_b = self.create_test_user(test_db_session, "user_b@curio.ai")

        service = DocumentService()
        doc = service.upload_document(
            test_db_session,
            user_id=user_a.id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )

        # User B tries to delete User A's document
        result = service.delete_document(test_db_session, doc.document_id, user_b.id)
        assert result is False

        # Verify document still exists
        db_doc = test_db_session.query(Document).filter(Document.id == doc.document_id).first()
        assert db_doc is not None

    def test_update_status(self, test_db_session: Session, test_user: User):
        """Test that document status can be updated."""
        from backend.app.repositories.document_repository import DocumentRepository

        repo = DocumentRepository()
        doc = repo.create(test_db_session, test_user.id, "test.pdf", 1024, "application/pdf")
        
        updated = repo.update_status(test_db_session, doc.id, test_user.id, "PROCESSING")
        assert updated is not None
        assert updated.status == "PROCESSING"

        # Cross-user update should return None
        other_user = self.create_test_user(test_db_session, "other@curio.ai")
        updated = repo.update_status(test_db_session, doc.id, other_user.id, "COMPLETED")
        assert updated is None

        # Verify status unchanged
        db_doc = test_db_session.query(Document).filter(Document.id == doc.id).first()
        assert db_doc.status == "PROCESSING"


class TestDocumentAPI:
    """Test document API endpoints with authentication and ownership."""

    def test_upload_document_api(self, authenticated_client: TestClient, test_user: User):
        """Test POST /documents creates document with owner."""
        files = {"file": ("test.pdf", b"test content", "application/pdf")}
        response = authenticated_client.post("/api/v1/documents", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["file_size"] == 12
        assert data["mime_type"] == "application/pdf"
        assert data["status"] == "UPLOADED"
        assert data["chunk_count"] == 0
        assert data["page_count"] is None
        assert "document_id" in data
        assert "created_at" in data

    def test_get_own_document_api(self, authenticated_client: TestClient, test_user: User, test_db_session: Session):
        """Test GET /documents/{id} returns own document."""
        # Create document directly
        doc = Document(
            user_id=test_user.id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            status="UPLOADED"
        )
        test_db_session.add(doc)
        test_db_session.commit()
        test_db_session.refresh(doc)

        response = authenticated_client.get(f"/api/v1/documents/{doc.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == str(doc.id)
        assert data["filename"] == "test.pdf"

    def test_get_cross_user_document_returns_404(self, test_db_session: Session):
        """Test GET /documents/{id} returns 404 for cross-user access."""
        user_a = User(email="user_a@curio.ai", hashed_password="test", is_active=True)
        user_b = User(email="user_b@curio.ai", hashed_password="test", is_active=True)
        test_db_session.add_all([user_a, user_b])
        test_db_session.commit()
        test_db_session.refresh(user_a)
        test_db_session.refresh(user_b)

        doc = Document(user_id=user_a.id, filename="test.pdf", file_size=1024, mime_type="application/pdf")
        test_db_session.add(doc)
        test_db_session.commit()
        test_db_session.refresh(doc)

        # User B tries to access
        token = create_access_token(subject=str(user_b.id))
        headers = {"Authorization": f"Bearer {token}"}
        
        from backend.app.main import app
        with TestClient(app) as client:
            client.headers.update(headers)
            response = client.get(f"/api/v1/documents/{doc.id}")
        
        assert response.status_code == 404

    def test_list_documents_api(self, authenticated_client: TestClient, test_user: User, test_db_session: Session):
        """Test GET /documents returns only owner's documents."""
        user_b = User(email="user_b@curio.ai", hashed_password="test", is_active=True)
        test_db_session.add(user_b)
        test_db_session.commit()
        test_db_session.refresh(user_b)

        doc1 = Document(user_id=test_user.id, filename="doc1.pdf", file_size=1024, mime_type="application/pdf")
        doc2 = Document(user_id=test_user.id, filename="doc2.pdf", file_size=2048, mime_type="application/pdf")
        doc3 = Document(user_id=user_b.id, filename="doc3.pdf", file_size=512, mime_type="application/pdf")
        test_db_session.add_all([doc1, doc2, doc3])
        test_db_session.commit()

        response = authenticated_client.get("/api/v1/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["documents"]) == 2
        assert all(d["filename"] in ["doc1.pdf", "doc2.pdf"] for d in data["documents"])
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_delete_document_api(self, authenticated_client: TestClient, test_user: User, test_db_session: Session):
        """Test DELETE /documents/{id} deletes own document."""
        doc = Document(user_id=test_user.id, filename="test.pdf", file_size=1024, mime_type="application/pdf")
        test_db_session.add(doc)
        test_db_session.commit()
        test_db_session.refresh(doc)

        response = authenticated_client.delete(f"/api/v1/documents/{doc.id}")
        assert response.status_code == 204

        # Verify deleted
        db_doc = test_db_session.query(Document).filter(Document.id == doc.id).first()
        assert db_doc is None

    def test_delete_cross_user_document_returns_404(self, test_db_session: Session):
        """Test DELETE /documents/{id} returns 404 for cross-user access."""
        user_a = User(email="user_a@curio.ai", hashed_password="test", is_active=True)
        user_b = User(email="user_b@curio.ai", hashed_password="test", is_active=True)
        test_db_session.add_all([user_a, user_b])
        test_db_session.commit()
        test_db_session.refresh(user_a)
        test_db_session.refresh(user_b)

        doc = Document(user_id=user_a.id, filename="test.pdf", file_size=1024, mime_type="application/pdf")
        test_db_session.add(doc)
        test_db_session.commit()
        test_db_session.refresh(doc)

        token = create_access_token(subject=str(user_b.id))
        headers = {"Authorization": f"Bearer {token}"}
        
        from backend.app.main import app
        with TestClient(app) as client:
            client.headers.update(headers)
            response = client.delete(f"/api/v1/documents/{doc.id}")
        
        assert response.status_code == 404

    def test_unauthenticated_access_returns_401(self, test_db_session: Session):
        """Test that unauthenticated requests return 401."""
        from backend.app.main import app
        with TestClient(app) as client:
            # No auth headers
            response = client.post("/api/v1/documents", files={"file": ("test.pdf", b"test", "application/pdf")})
            assert response.status_code == 401

            response = client.get("/api/v1/documents")
            assert response.status_code == 401

            response = client.get(f"/api/v1/documents/{uuid4()}")
            assert response.status_code == 401

            response = client.delete(f"/api/v1/documents/{uuid4()}")
            assert response.status_code == 401

    def test_document_status_persistence(self, test_db_session: Session, test_user: User):
        """Test that document status field persists correctly."""
        doc = Document(
            user_id=test_user.id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            status="UPLOADED"
        )
        test_db_session.add(doc)
        test_db_session.commit()
        test_db_session.refresh(doc)

        assert doc.status == "UPLOADED"

        # Update status
        doc.status = "PROCESSING"
        test_db_session.commit()
        test_db_session.refresh(doc)
        assert doc.status == "PROCESSING"

    def test_document_all_new_fields(self, test_db_session: Session, test_user: User):
        """Test that all new document fields can be set and retrieved."""
        doc = Document(
            user_id=test_user.id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            status="COMPLETED",
            storage_path="/storage/test.pdf",
            content_hash="abc123",
            page_count=10,
            processing_error=None,
            chunk_count=5,
            embedding_model="text-embedding-3-small"
        )
        test_db_session.add(doc)
        test_db_session.commit()
        test_db_session.refresh(doc)

        assert doc.status == "COMPLETED"
        assert doc.storage_path == "/storage/test.pdf"
        assert doc.content_hash == "abc123"
        assert doc.page_count == 10
        assert doc.processing_error is None
        assert doc.chunk_count == 5
        assert doc.embedding_model == "text-embedding-3-small"

    def test_session_document_relationship_preserved(self, test_db_session: Session, test_user: User):
        """Test that existing Session->Document relationship still works."""
        doc = Document(
            user_id=test_user.id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        test_db_session.add(doc)
        test_db_session.commit()
        test_db_session.refresh(doc)

        session = Session(
            user_id=test_user.id,
            topic="Test Topic",
            source_type="DOCUMENT",
            document_id=doc.id,
            status="ACTIVE"
        )
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        # Verify relationship
        assert session.document_id == doc.id
        assert session.document is not None
        assert session.document.id == doc.id
        assert session.document.user_id == test_user.id


class TestDocumentPagination:
    """Test document listing pagination."""

    def test_pagination_first_page(self, test_db_session: Session, test_user: User):
        """Test pagination returns first page correctly."""
        from backend.app.services.document_service import DocumentService

        service = DocumentService()
        for i in range(5):
            service.upload_document(test_db_session, test_user.id, f"doc{i}.pdf", 1024, "application/pdf")

        result = service.list_documents(test_db_session, test_user.id, page=1, page_size=2)
        assert result.total == 5
        assert len(result.documents) == 2
        assert result.page == 1
        assert result.page_size == 2

    def test_pagination_second_page(self, test_db_session: Session, test_user: User):
        """Test pagination returns second page correctly."""
        from backend.app.services.document_service import DocumentService

        service = DocumentService()
        for i in range(5):
            service.upload_document(test_db_session, test_user.id, f"doc{i}.pdf", 1024, "application/pdf")

        result = service.list_documents(test_db_session, test_user.id, page=2, page_size=2)
        assert result.total == 5
        assert len(result.documents) == 2
        assert result.page == 2
        assert result.page_size == 2

    def test_pagination_beyond_last_page(self, test_db_session: Session, test_user: User):
        """Test pagination returns empty list beyond last page."""
        from backend.app.services.document_service import DocumentService

        service = DocumentService()
        service.upload_document(test_db_session, test_user.id, "doc1.pdf", 1024, "application/pdf")

        result = service.list_documents(test_db_session, test_user.id, page=5, page_size=10)
        assert result.total == 1
        assert len(result.documents) == 0
        assert result.page == 5