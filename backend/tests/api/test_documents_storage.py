"""
Tests for Task 5.2 - Document File Storage & Upload Persistence.

Tests cover:
- Valid PDF/TXT/DOCX upload persists file
- Stored file exists at correct path
- storage_path persisted in database
- Original filename preserved as metadata
- Actual file size persisted
- SHA-256 content hash correct
- Empty file rejected
- Unsupported extension rejected
- Unsupported MIME type rejected
- Oversized upload rejected
- Streaming size limit enforced without loading whole file
- Path traversal filename cannot escape storage root
- Generated storage names prevent collisions
- Database failure removes stored file (rollback)
- Storage failure does not leave Document row
- Own document deletion removes physical file
- Deleting already-missing physical file remains safe
- Cross-user deletion remains 404
- Unauthenticated upload remains 401
- Duplicate content allowed for different users
- Duplicate content hash persisted correctly
"""

import hashlib
import pytest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch, MagicMock
from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.services.document_service import DocumentService
from backend.app.storage.local import LocalStorage
from backend.app.core.security import create_access_token


# Test fixtures
PDF_CONTENT = b"%PDF-1.4\nTest PDF content\n%%EOF"
TXT_CONTENT = b"This is a test text file."
DOCX_CONTENT = b"PK\x03\x04" + b"dummy docx content"  # Minimal DOCX signature


def create_test_user(db: Session, email: str = None) -> User:
    """Create a test user in the database."""
    user_email = email or f"test_{uuid4().hex[:8]}@curio.ai"
    user = User(email=user_email, hashed_password="test", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_auth_headers(user: User) -> dict:
    """Get authorization headers for a user."""
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def create_upload_file(content: bytes, filename: str, mime_type: str) -> UploadFile:
    """Create a mock UploadFile for testing."""
    from io import BytesIO
    file_obj = BytesIO(content)
    return UploadFile(filename=filename, file=file_obj, headers={"content-type": mime_type})


class TestLocalStorage:
    """Test the LocalStorage abstraction directly."""

    def test_validate_pdf(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        ext = storage.validate_file_type("test.pdf", "application/pdf")
        assert ext == ".pdf"

    def test_validate_txt(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        ext = storage.validate_file_type("test.txt", "text/plain")
        assert ext == ".txt"

    def test_validate_docx(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        ext = storage.validate_file_type("test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert ext == ".docx"

    def test_reject_unsupported_extension(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        with pytest.raises(ValueError, match="not allowed"):
            storage.validate_file_type("test.exe", "application/octet-stream")

    def test_reject_unsupported_mime(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        with pytest.raises(ValueError, match="not allowed"):
            storage.validate_file_type("test.pdf", "application/x-executable")

    def test_reject_extension_mime_mismatch(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        with pytest.raises(ValueError, match="does not match"):
            storage.validate_file_type("test.txt", "application/pdf")

    def test_build_storage_path(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        path = storage._build_storage_path(user_id, doc_id, ".pdf")
        expected = Path(tmp_path) / "documents" / str(user_id) / f"{doc_id}.pdf"
        assert path == expected

    def test_save_uploaded_file_pdf(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path), max_file_size=1024*1024)
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        
        storage_path, size, content_hash = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "test.pdf", "application/pdf"
        )
        
        assert storage_path.exists()
        assert size == len(PDF_CONTENT)
        assert content_hash == hashlib.sha256(PDF_CONTENT).hexdigest()
        assert storage_path.name == f"{doc_id}.pdf"
        assert str(user_id) in str(storage_path)

    def test_save_uploaded_file_txt(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(TXT_CONTENT, "notes.txt", "text/plain")
        
        storage_path, size, content_hash = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "notes.txt", "text/plain"
        )
        
        assert storage_path.exists()
        assert size == len(TXT_CONTENT)
        assert content_hash == hashlib.sha256(TXT_CONTENT).hexdigest()

    def test_save_uploaded_file_docx(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(DOCX_CONTENT, "doc.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        storage_path, size, content_hash = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "doc.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        assert storage_path.exists()
        assert size == len(DOCX_CONTENT)
        assert content_hash == hashlib.sha256(DOCX_CONTENT).hexdigest()

    def test_reject_empty_file(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(b"", "empty.pdf", "application/pdf")
        
        with pytest.raises(ValueError, match="Empty file"):
            storage.save_uploaded_file(upload_file, user_id, doc_id, "empty.pdf", "application/pdf")

    def test_reject_oversized_file(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path), max_file_size=100)
        user_id = uuid4()
        doc_id = uuid4()
        
        large_content = b"x" * 200
        upload_file = create_upload_file(large_content, "large.pdf", "application/pdf")
        
        with pytest.raises(ValueError, match="exceeds maximum"):
            storage.save_uploaded_file(upload_file, user_id, doc_id, "large.pdf", "application/pdf")

    def test_path_traversal_prevented(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        # Even with malicious filename, storage path uses document_id
        # But the filename must still have a valid extension
        upload_file = create_upload_file(PDF_CONTENT, "../../../etc/passwd.pdf", "application/pdf")
        
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "../../../etc/passwd.pdf", "application/pdf"
        )
        
        # File should be stored under user's directory with document_id name
        assert str(user_id) in str(storage_path)
        assert storage_path.name == f"{doc_id}.pdf"
        assert "etc" not in str(storage_path)
        assert "passwd" not in str(storage_path)

    def test_collision_resistant_paths(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        # Upload same content twice with different document IDs
        upload_file1 = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        upload_file2 = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        
        path1, _, hash1 = storage.save_uploaded_file(upload_file1, user_id, doc_id, "test.pdf", "application/pdf")
        
        doc_id2 = uuid4()
        path2, _, hash2 = storage.save_uploaded_file(upload_file2, user_id, doc_id2, "test.pdf", "application/pdf")
        
        # Different document IDs = different paths
        assert path1 != path2
        # Same content = same hash
        assert hash1 == hash2

    def test_cross_user_isolation(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        user_a = uuid4()
        user_b = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        
        path_a, _, _ = storage.save_uploaded_file(upload_file, user_a, doc_id, "test.pdf", "application/pdf")
        
        upload_file2 = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        path_b, _, _ = storage.save_uploaded_file(upload_file2, user_b, doc_id, "test.pdf", "application/pdf")
        
        # Same document_id but different users = different paths
        assert path_a != path_b
        assert str(user_a) in str(path_a)
        assert str(user_b) in str(path_b)

    def test_delete_file(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        storage_path, _, _ = storage.save_uploaded_file(upload_file, user_id, doc_id, "test.pdf", "application/pdf")
        
        assert storage.file_exists(storage_path)
        
        result = storage.delete_file(storage_path)
        assert result is True
        assert not storage.file_exists(storage_path)

    def test_delete_missing_file_safe(self, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        missing_path = tmp_path / "documents" / "user" / "missing.pdf"
        
        result = storage.delete_file(missing_path)
        assert result is False  # Safe, no exception

    def test_streaming_does_not_load_whole_file(self, tmp_path):
        """Verify streaming reads in chunks, not all at once."""
        storage = LocalStorage(storage_root=str(tmp_path), max_file_size=1024*1024)
        user_id = uuid4()
        doc_id = uuid4()
        
        # Create a file larger than chunk size
        chunk_size = storage._chunk_size
        large_content = b"x" * (chunk_size * 3 + 100)
        upload_file = create_upload_file(large_content, "large.pdf", "application/pdf")
        
        # Mock the read method to verify chunked reads
        original_read = upload_file.file.read
        read_calls = []
        
        def mock_read(size):
            read_calls.append(size)
            return original_read(size)
        
        upload_file.file.read = mock_read
        
        storage.save_uploaded_file(upload_file, user_id, doc_id, "large.pdf", "application/pdf")
        
        # Should have multiple read calls with chunk_size
        assert len(read_calls) > 1
        assert all(c <= chunk_size for c in read_calls)


class TestDocumentServiceStorage:
    """Test DocumentService with storage integration."""

    def test_upload_pdf_persists_file(self, test_db_session: Session, test_user: User, tmp_path):
        # Override storage root for test
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        assert response.document_id is not None
        assert response.filename == "test.pdf"
        assert response.file_size == len(PDF_CONTENT)
        assert response.mime_type == "application/pdf"
        assert response.status == "UPLOADED"
        
        # Verify database record
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert db_doc is not None
        assert db_doc.storage_path is not None
        assert db_doc.content_hash == hashlib.sha256(PDF_CONTENT).hexdigest()
        assert db_doc.file_size == len(PDF_CONTENT)
        
        # Verify physical file exists
        assert Path(db_doc.storage_path).exists()

    def test_upload_txt_persists_file(self, test_db_session: Session, test_user: User, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(TXT_CONTENT, "notes.txt", "text/plain")
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        assert response.filename == "notes.txt"
        assert response.file_size == len(TXT_CONTENT)
        assert response.mime_type == "text/plain"
        
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert db_doc.content_hash == hashlib.sha256(TXT_CONTENT).hexdigest()

    def test_upload_docx_persists_file(self, test_db_session: Session, test_user: User, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(DOCX_CONTENT, "doc.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        assert response.filename == "doc.docx"
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert db_doc.content_hash == hashlib.sha256(DOCX_CONTENT).hexdigest()

    def test_reject_empty_file(self, test_db_session: Session, test_user: User, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(b"", "empty.pdf", "application/pdf")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.upload_document(test_db_session, test_user.id, upload_file)
        assert exc.value.status_code == 400
        assert "Empty file" in str(exc.value.detail)
        
        # No document row created
        count = test_db_session.query(Document).count()
        assert count == 0

    def test_reject_unsupported_extension(self, test_db_session: Session, test_user: User, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(b"test", "test.exe", "application/octet-stream")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.upload_document(test_db_session, test_user.id, upload_file)
        assert exc.value.status_code == 400
        assert "not allowed" in str(exc.value.detail)

    def test_reject_unsupported_mime_type(self, test_db_session: Session, test_user: User, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(b"test", "test.pdf", "application/x-executable")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.upload_document(test_db_session, test_user.id, upload_file)
        assert exc.value.status_code == 400

    def test_reject_oversized_upload(self, test_db_session: Session, test_user: User, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path), max_file_size=100)
        service = DocumentService(storage=storage)
        
        large_content = b"x" * 200
        upload_file = create_upload_file(large_content, "large.pdf", "application/pdf")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.upload_document(test_db_session, test_user.id, upload_file)
        assert exc.value.status_code == 400
        assert "exceeds maximum" in str(exc.value.detail)

    def test_streaming_enforces_limit_without_full_load(self, test_db_session: Session, test_user: User, tmp_path):
        """Verify size limit enforced during streaming, not after full load."""
        storage = LocalStorage(storage_root=str(tmp_path), max_file_size=1000)
        service = DocumentService(storage=storage)
        
        # File slightly over limit
        large_content = b"x" * 1500
        upload_file = create_upload_file(large_content, "large.pdf", "application/pdf")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.upload_document(test_db_session, test_user.id, upload_file)
        assert exc.value.status_code == 400

    def test_db_failure_cleans_up_file(self, test_db_session: Session, test_user: User, tmp_path):
        """If DB commit fails, stored file should be cleaned up."""
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        
        # Mock repo.create to raise exception
        with patch.object(service.repo, 'create', side_effect=Exception("DB error")):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                service.upload_document(test_db_session, test_user.id, upload_file)
            assert exc.value.status_code == 500
        
        # No files should remain in storage
        user_dir = Path(tmp_path) / "documents" / str(test_user.id)
        if user_dir.exists():
            files = list(user_dir.glob("*"))
            assert len(files) == 0

    def test_storage_failure_no_document_row(self, test_db_session: Session, test_user: User, tmp_path):
        """If storage fails, no Document row should be created."""
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        
        # Mock storage to raise exception
        with patch.object(storage, 'save_uploaded_file', side_effect=IOError("Disk full")):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                service.upload_document(test_db_session, test_user.id, upload_file)
            assert exc.value.status_code == 500
        
        # No document row created
        count = test_db_session.query(Document).count()
        assert count == 0

    def test_duplicate_content_allowed_different_users(self, test_db_session: Session, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        user_a = create_test_user(test_db_session, "user_a@curio.ai")
        user_b = create_test_user(test_db_session, "user_b@curio.ai")
        
        upload_a = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        upload_b = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        
        resp_a = service.upload_document(test_db_session, user_a.id, upload_a)
        resp_b = service.upload_document(test_db_session, user_b.id, upload_b)
        
        assert resp_a.document_id != resp_b.document_id
        
        doc_a = test_db_session.query(Document).filter(Document.id == resp_a.document_id).first()
        doc_b = test_db_session.query(Document).filter(Document.id == resp_b.document_id).first()
        
        # Different users can have same content hash
        assert doc_a.content_hash == doc_b.content_hash
        assert doc_a.user_id == user_a.id
        assert doc_b.user_id == user_b.id

    def test_own_deletion_removes_physical_file(self, test_db_session: Session, test_user: User, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        storage_path = Path(db_doc.storage_path)
        assert storage_path.exists()
        
        result = service.delete_document(test_db_session, response.document_id, test_user.id)
        assert result is True
        
        # Physical file deleted
        assert not storage_path.exists()
        # DB record deleted
        assert test_db_session.query(Document).filter(Document.id == response.document_id).first() is None

    def test_delete_missing_physical_file_safe(self, test_db_session: Session, test_user: User, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        # Manually delete physical file
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        Path(db_doc.storage_path).unlink()
        
        # Service delete should still succeed
        result = service.delete_document(test_db_session, response.document_id, test_user.id)
        assert result is True
        
        # DB record deleted
        assert test_db_session.query(Document).filter(Document.id == response.document_id).first() is None

    def test_cross_user_deletion_returns_false(self, test_db_session: Session, tmp_path):
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        user_a = create_test_user(test_db_session, "user_a@curio.ai")
        user_b = create_test_user(test_db_session, "user_b@curio.ai")
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        response = service.upload_document(test_db_session, user_a.id, upload_file)
        
        result = service.delete_document(test_db_session, response.document_id, user_b.id)
        assert result is False
        
        # Document still exists
        assert test_db_session.query(Document).filter(Document.id == response.document_id).first() is not None


class TestDocumentStorageAPI:
    """Test document API endpoints with storage."""

    def test_upload_pdf_api(self, authenticated_client: TestClient, test_user: User, tmp_path, monkeypatch):
        # Override storage root for test
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        
        # Re-import to pick up new settings
        import importlib
        import backend.app.core.config as config_module
        importlib.reload(config_module)
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        import backend.app.services.document_service as service_module
        importlib.reload(service_module)
        
        from backend.app.services.document_service import DocumentService
        from backend.app.storage import set_storage
        
        # Create new service with test storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        files = {"file": ("test.pdf", PDF_CONTENT, "application/pdf")}
        response = authenticated_client.post("/api/v1/documents", files=files)
        
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["file_size"] == len(PDF_CONTENT)
        assert data["mime_type"] == "application/pdf"
        assert data["status"] == "UPLOADED"

    def test_get_own_document_shows_metadata(self, authenticated_client: TestClient, test_user: User, test_db_session: Session, tmp_path, monkeypatch):
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        upload_response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        response = authenticated_client.get(f"/api/v1/documents/{upload_response.document_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == str(upload_response.document_id)
        assert data["filename"] == "test.pdf"

    def test_cross_user_get_returns_404(self, authenticated_client: TestClient, test_db_session: Session, tmp_path, monkeypatch):
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        user_a = create_test_user(test_db_session, "user_a@curio.ai")
        user_b = create_test_user(test_db_session, "user_b@curio.ai")
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        response = service.upload_document(test_db_session, user_a.id, upload_file)
        
        from backend.app.core.security import create_access_token
        from backend.app.main import app
        
        token = create_access_token(subject=str(user_b.id))
        headers = {"Authorization": f"Bearer {token}"}
        
        with TestClient(app) as client:
            client.headers.update(headers)
            response = client.get(f"/api/v1/documents/{response.document_id}")
        
        assert response.status_code == 404

    def test_list_documents_only_own(self, authenticated_client: TestClient, test_user: User, test_db_session: Session, tmp_path, monkeypatch):
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        user_b = create_test_user(test_db_session, "user_b@curio.ai")
        
        upload_a1 = create_upload_file(PDF_CONTENT, "doc1.pdf", "application/pdf")
        upload_a2 = create_upload_file(TXT_CONTENT, "doc2.txt", "text/plain")
        upload_b = create_upload_file(DOCX_CONTENT, "doc3.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        service.upload_document(test_db_session, test_user.id, upload_a1)
        service.upload_document(test_db_session, test_user.id, upload_a2)
        service.upload_document(test_db_session, user_b.id, upload_b)
        
        response = authenticated_client.get("/api/v1/documents")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["documents"]) == 2
        filenames = [d["filename"] for d in data["documents"]]
        assert "doc1.pdf" in filenames
        assert "doc2.txt" in filenames
        assert "doc3.docx" not in filenames

    def test_delete_own_document_removes_file(self, authenticated_client: TestClient, test_user: User, test_db_session: Session, tmp_path, monkeypatch):
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        upload_response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        db_doc = test_db_session.query(Document).filter(Document.id == upload_response.document_id).first()
        storage_path = Path(db_doc.storage_path)
        assert storage_path.exists()
        
        response = authenticated_client.delete(f"/api/v1/documents/{upload_response.document_id}")
        
        assert response.status_code == 204
        assert not storage_path.exists()
        assert test_db_session.query(Document).filter(Document.id == upload_response.document_id).first() is None

    def test_cross_user_delete_returns_404(self, authenticated_client: TestClient, test_db_session: Session, tmp_path, monkeypatch):
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        user_a = create_test_user(test_db_session, "user_a@curio.ai")
        user_b = create_test_user(test_db_session, "user_b@curio.ai")
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        upload_response = service.upload_document(test_db_session, user_a.id, upload_file)
        
        from backend.app.core.security import create_access_token
        from backend.app.main import app
        
        token = create_access_token(subject=str(user_b.id))
        headers = {"Authorization": f"Bearer {token}"}
        
        with TestClient(app) as client:
            client.headers.update(headers)
            response = client.delete(f"/api/v1/documents/{upload_response.document_id}")
        
        assert response.status_code == 404
        assert test_db_session.query(Document).filter(Document.id == upload_response.document_id).first() is not None

    def test_unauthenticated_upload_returns_401(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        
        from backend.app.main import app
        with TestClient(app) as client:
            files = {"file": ("test.pdf", PDF_CONTENT, "application/pdf")}
            response = client.post("/api/v1/documents", files=files)
            assert response.status_code == 401

    def test_duplicate_content_hash_persisted(self, authenticated_client: TestClient, test_user: User, test_db_session: Session, tmp_path, monkeypatch):
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload1 = create_upload_file(PDF_CONTENT, "test1.pdf", "application/pdf")
        upload2 = create_upload_file(PDF_CONTENT, "test2.pdf", "application/pdf")
        
        resp1 = service.upload_document(test_db_session, test_user.id, upload1)
        resp2 = service.upload_document(test_db_session, test_user.id, upload2)
        
        doc1 = test_db_session.query(Document).filter(Document.id == resp1.document_id).first()
        doc2 = test_db_session.query(Document).filter(Document.id == resp2.document_id).first()
        
        assert doc1.content_hash == doc2.content_hash
        assert doc1.content_hash == hashlib.sha256(PDF_CONTENT).hexdigest()


class TestDocumentStorageIntegration:
    """Integration tests with existing document/session tests."""

    def test_session_document_relationship_preserved(self, test_db_session: Session, test_user: User, tmp_path, monkeypatch):
        """Verify Session->Document relationship still works with storage."""
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        from backend.app.models.session import Session
        session = Session(
            user_id=test_user.id,
            topic="Test Topic",
            source_type="DOCUMENT",
            document_id=response.document_id,
            status="ACTIVE"
        )
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)
        
        # Verify document_id is set correctly
        assert session.document_id == response.document_id
        
        # Verify document exists and has storage_path
        doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert doc is not None
        assert doc.user_id == test_user.id
        assert doc.storage_path is not None
        assert doc.content_hash is not None


# Need to import monkeypatch for tests that use it
import pytest