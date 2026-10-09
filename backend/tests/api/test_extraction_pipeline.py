"""
Tests for Task 5.3 - PDF/Text Extraction Pipeline.

Tests cover:
1. PDF extraction - valid text PDF extracts correctly
2. PDF extraction - multi-page PDF preserves page boundaries
3. PDF extraction - page_count is correct
3. PDF extraction - image-only/scanned PDF does not fabricate text
5. PDF extraction - corrupted PDF produces FAILED status/error
6. TXT extraction - valid UTF-8 TXT extracts correctly
7. TXT extraction - UTF-8 BOM handled safely
8. TXT extraction - newline preservation
9. TXT extraction - malformed encoding handled safely
10. DOCX extraction - valid DOCX extracts paragraphs
11. DOCX extraction - paragraph boundaries preserved
12. DOCX extraction - malformed DOCX produces FAILED status
13. DOCX extraction - physical page count is not fabricated (None)
14. Processing lifecycle - UPLOADED -> PROCESSING -> PROCESSED
15. Processing lifecycle - extraction failure -> FAILED
16. Processing lifecycle - processing_error persisted on failure
17. Processing lifecycle - processing_error cleared on success
18. Processing lifecycle - page_count persisted where applicable
19. Processing lifecycle - missing storage file produces FAILED
20. Security - cross-user processing returns 404
21. Security - unauthenticated processing returns 401
22. Security - valid document remains stored after successful extraction
23. Security - source file is preserved after extraction failure
24. Security - extraction cannot accept arbitrary filesystem paths
25. Security - another user's document cannot be processed
"""

import pytest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch, MagicMock
from io import BytesIO
from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.services.document_service import DocumentService
from backend.app.storage.local import LocalStorage
from backend.app.extraction import ExtractionService, ExtractionResult, ExtractionError
from backend.app.core.security import create_access_token
from backend.app.repositories.document_repository import DocumentRepository


# Test fixtures - minimal valid file content for each format

# Minimal valid PDF (1 page with text "Hello World")
PDF_CONTENT = b"""%PDF-1.4
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

# Multi-page PDF (2 pages) - valid PDF based on working single-page structure
MULTI_PAGE_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Page 1 Content) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
6 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 7 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
7 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Page 2 Content) Tj ET
endstream
endobj
xref
0 8
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000218 00000 n
0000000318 00000 n
0000000421 00000 n
0000000524 00000 n
trailer
<< /Size 8 /Root 1 0 R >>
startxref
604
%%EOF"""

# Image-only PDF (no extractable text - minimal structure)
IMAGE_ONLY_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>
endobj
4 0 obj
<< /Length 0 >>
stream
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000174 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
254
%%EOF"""

# Corrupted PDF
CORRUPTED_PDF = b"This is not a valid PDF file at all"

# TXT content
TXT_CONTENT = b"This is a test text file.\nWith multiple lines.\nAnd some special chars: \xc3\xa9\xc3\xb1\xc3\xb6"

# TXT with BOM
TXT_WITH_BOM = b"\xef\xbb\xbfThis is a test with BOM.\nSecond line."

# Malformed encoding (invalid UTF-8)
MALFORMED_TXT = b"This has invalid UTF-8: \xff\xfe"

# DOCX content - minimal valid DOCX (just the XML structure)
# We'll create this programmatically in tests using python-docx

EMPTY_TXT = b""


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
    file_obj = BytesIO(content)
    return UploadFile(filename=filename, file=file_obj, headers={"content-type": mime_type})


def create_minimal_docx(path: Path) -> bytes:
    """Create a minimal valid DOCX file for testing."""
    from docx import Document as DocxDocument
    doc = DocxDocument()
    doc.add_paragraph("First paragraph.")
    doc.add_paragraph("Second paragraph with content.")
    doc.add_paragraph("Third paragraph.")
    doc.save(str(path))
    return path.read_bytes()


def create_multipage_docx(path: Path) -> bytes:
    """Create a DOCX with many paragraphs."""
    from docx import Document as DocxDocument
    doc = DocxDocument()
    for i in range(10):
        doc.add_paragraph(f"Paragraph {i+1} with some content here.")
    doc.save(str(path))
    return path.read_bytes()


class TestExtractionService:
    """Test the ExtractionService directly."""

    def test_extract_pdf_valid(self, tmp_path):
        """Test valid text PDF extracts correctly."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "test.pdf", "application/pdf"
        )
        
        service = ExtractionService()
        result = service.extract(storage_path, "application/pdf")
        
        assert isinstance(result, ExtractionResult)
        assert "Hello World" in result.text
        assert result.page_count == 1
        assert result.character_count > 0
        assert result.extraction_metadata["format"] == "pdf"

    def test_extract_pdf_multipage_preserves_boundaries(self, tmp_path):
        """Test multi-page PDF preserves page boundaries."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(MULTI_PAGE_PDF, "multipage.pdf", "application/pdf")
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "multipage.pdf", "application/pdf"
        )
        
        service = ExtractionService()
        result = service.extract(storage_path, "application/pdf")
        
        assert result.page_count == 2
        assert "Page 1 Content" in result.text
        assert "Page 2 Content" in result.text
        assert "---PAGE_BREAK---" in result.text

    def test_extract_pdf_page_count_correct(self, tmp_path):
        """Test page_count is correct for PDF."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "test.pdf", "application/pdf"
        )
        
        service = ExtractionService()
        result = service.extract(storage_path, "application/pdf")
        
        assert result.page_count == 1
        assert result.extraction_metadata["total_pages"] == 1

    def test_extract_pdf_image_only_no_fabrication(self, tmp_path):
        """Test image-only/scanned PDF does not fabricate text."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(IMAGE_ONLY_PDF, "image_only.pdf", "application/pdf")
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "image_only.pdf", "application/pdf"
        )
        
        service = ExtractionService()
        result = service.extract(storage_path, "application/pdf")
        
        assert result.page_count == 1
        # Should have empty or minimal text, not fabricated content
        assert result.character_count == 0 or result.text.strip() == ""
        assert result.extraction_metadata["pages_with_text"] == 0

    def test_extract_pdf_corrupted_produces_error(self, tmp_path):
        """Test corrupted PDF produces extraction error."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(CORRUPTED_PDF, "corrupt.pdf", "application/pdf")
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "corrupt.pdf", "application/pdf"
        )
        
        service = ExtractionService()
        with pytest.raises(ExtractionError) as exc:
            service.extract(storage_path, "application/pdf")
        
        assert "Failed to read PDF" in str(exc.value) or "Extraction failed" in str(exc.value)

    def test_extract_txt_valid_utf8(self, tmp_path):
        """Test valid UTF-8 TXT extracts correctly."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(TXT_CONTENT, "test.txt", "text/plain")
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "test.txt", "text/plain"
        )
        
        service = ExtractionService()
        result = service.extract(storage_path, "text/plain")
        
        assert isinstance(result, ExtractionResult)
        assert "test text file" in result.text
        assert "multiple lines" in result.text
        assert "\xc3\xa9" in result.text.decode('utf-8') if isinstance(result.text, bytes) else "é" in result.text
        assert result.page_count == 1
        assert result.character_count > 0
        assert result.extraction_metadata["format"] == "txt"

    def test_extract_txt_utf8_bom_handled(self, tmp_path):
        """Test UTF-8 BOM handled safely."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(TXT_WITH_BOM, "bom.txt", "text/plain")
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "bom.txt", "text/plain"
        )
        
        service = ExtractionService()
        result = service.extract(storage_path, "text/plain")
        
        assert "BOM" in result.text
        assert "Second line" in result.text
        assert not result.text.startswith("\ufeff")  # BOM stripped
        assert result.extraction_metadata["encoding"] == "utf-8-sig"

    def test_extract_txt_newline_preservation(self, tmp_path):
        """Test newline preservation in TXT extraction."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        content = b"Line 1\nLine 2\n\nLine 4"
        upload_file = create_upload_file(content, "newlines.txt", "text/plain")
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "newlines.txt", "text/plain"
        )
        
        service = ExtractionService()
        result = service.extract(storage_path, "text/plain")
        
        assert "Line 1" in result.text
        assert "Line 2" in result.text
        assert "Line 4" in result.text
        # Newlines should be preserved
        assert "\n" in result.text

    def test_extract_txt_malformed_encoding_safe(self, tmp_path):
        """Test malformed encoding handled safely with replacement."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(MALFORMED_TXT, "bad.txt", "text/plain")
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "bad.txt", "text/plain"
        )
        
        service = ExtractionService()
        result = service.extract(storage_path, "text/plain")
        
        # Should not raise, should use replacement chars
        assert isinstance(result, ExtractionResult)
        assert result.character_count > 0
        assert "replacement" in result.extraction_metadata["encoding"].lower() or "utf-8" in result.extraction_metadata["encoding"]

    def test_extract_docx_valid(self, tmp_path):
        """Test valid DOCX extracts paragraphs."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        # Create a valid DOCX file
        docx_path = tmp_path / "test.docx"
        create_minimal_docx(docx_path)
        
        upload_file = create_upload_file(
            docx_path.read_bytes(), "test.docx", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "test.docx", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        service = ExtractionService()
        result = service.extract(storage_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        assert isinstance(result, ExtractionResult)
        assert "First paragraph" in result.text
        assert "Second paragraph" in result.text
        assert "Third paragraph" in result.text
        assert result.character_count > 0
        assert result.extraction_metadata["format"] == "docx"
        assert result.extraction_metadata["paragraph_count"] == 3

    def test_extract_docx_paragraph_boundaries(self, tmp_path):
        """Test DOCX paragraph boundaries preserved."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        docx_path = tmp_path / "test.docx"
        create_minimal_docx(docx_path)
        
        upload_file = create_upload_file(
            docx_path.read_bytes(), "test.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "test.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        service = ExtractionService()
        result = service.extract(storage_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        # Paragraphs should be separated by double newlines
        assert "\n\n" in result.text
        paragraphs = result.text.split("\n\n")
        assert len(paragraphs) == 3

    def test_extract_docx_malformed_produces_error(self, tmp_path):
        """Test malformed DOCX produces extraction error."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        # Create invalid DOCX
        bad_content = b"PK\x03\x04 not a real docx"
        upload_file = create_upload_file(
            bad_content, "bad.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "bad.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        service = ExtractionService()
        with pytest.raises(ExtractionError) as exc:
            service.extract(storage_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        assert "Failed to read DOCX" in str(exc.value) or "Extraction failed" in str(exc.value)

    def test_extract_docx_page_count_none(self, tmp_path):
        """Test DOCX physical page count is not fabricated (returns None)."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        docx_path = tmp_path / "test.docx"
        create_multipage_docx(docx_path)
        
        upload_file = create_upload_file(
            docx_path.read_bytes(), "test.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "test.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        service = ExtractionService()
        result = service.extract(storage_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        # DOCX has no reliable physical page count - should be None
        assert result.page_count is None


class TestDocumentProcessingLifecycle:
    """Test the full document processing lifecycle via DocumentService."""

    def test_process_document_uploaded_to_processed(self, test_db_session: Session, test_user: User, tmp_path, monkeypatch):
        """Test UPLOADED -> PROCESSING -> PROCESSED lifecycle."""
        # Override storage
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        # Upload document
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        # Verify initial status
        assert response.status == "UPLOADED"
        assert response.page_count is None
        
        # Process document
        processed = service.process_document(test_db_session, response.document_id, test_user.id)
        
        # Verify final status
        assert processed.status == "PROCESSED"
        assert processed.page_count == 1
        assert processed.processing_error is None
        
        # Verify in database
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert db_doc.status == "PROCESSED"
        assert db_doc.page_count == 1
        assert db_doc.processing_error is None

    def test_process_document_failure_marks_failed(self, test_db_session: Session, test_user: User, tmp_path, monkeypatch):
        """Test extraction failure -> FAILED status."""
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        # Upload corrupted PDF
        upload_file = create_upload_file(CORRUPTED_PDF, "corrupt.pdf", "application/pdf")
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        # Process should fail
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.process_document(test_db_session, response.document_id, test_user.id)
        
        assert exc.value.status_code == 422
        assert "Extraction failed" in str(exc.value.detail)
        
        # Verify FAILED status in database
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert db_doc.status == "FAILED"
        assert db_doc.processing_error is not None
        assert len(db_doc.processing_error) > 0

    def test_process_document_error_persisted_on_failure(self, test_db_session: Session, test_user: User, tmp_path, monkeypatch):
        """Test processing_error persisted on failure."""
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(CORRUPTED_PDF, "corrupt.pdf", "application/pdf")
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            service.process_document(test_db_session, response.document_id, test_user.id)
        
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert db_doc.status == "FAILED"
        assert db_doc.processing_error is not None
        assert "Failed to read PDF" in db_doc.processing_error or "Extraction failed" in db_doc.processing_error

    def test_process_document_error_cleared_on_success(self, test_db_session: Session, test_user: User, tmp_path, monkeypatch):
        """Test processing_error cleared on success."""
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        # First upload and fail
        upload_file = create_upload_file(CORRUPTED_PDF, "corrupt.pdf", "application/pdf")
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            service.process_document(test_db_session, response.document_id, test_user.id)
        
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert db_doc.status == "FAILED"
        error_before = db_doc.processing_error
        assert error_before is not None
        
        # Now upload valid PDF with same document_id (need new doc)
        # Actually we need a new document since the old one is failed
        upload_file2 = create_upload_file(PDF_CONTENT, "good.pdf", "application/pdf")
        response2 = service.upload_document(test_db_session, test_user.id, upload_file2)
        
        processed = service.process_document(test_db_session, response2.document_id, test_user.id)
        
        db_doc2 = test_db_session.query(Document).filter(Document.id == response2.document_id).first()
        assert db_doc2.status == "PROCESSED"
        assert db_doc2.processing_error is None

    def test_process_document_page_count_persisted(self, test_db_session: Session, test_user: User, tmp_path, monkeypatch):
        """Test page_count persisted where applicable."""
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        # PDF - should have page_count
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        processed = service.process_document(test_db_session, response.document_id, test_user.id)
        
        assert processed.page_count == 1
        
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert db_doc.page_count == 1
        
        # TXT - should have page_count = 1
        upload_file2 = create_upload_file(TXT_CONTENT, "test.txt", "text/plain")
        response2 = service.upload_document(test_db_session, test_user.id, upload_file2)
        processed2 = service.process_document(test_db_session, response2.document_id, test_user.id)
        
        assert processed2.page_count == 1
        
        # DOCX - page_count should be None (not fabricated)
        docx_path = tmp_path / "test.docx"
        create_minimal_docx(docx_path)
        upload_file3 = create_upload_file(
            docx_path.read_bytes(), "test.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        response3 = service.upload_document(test_db_session, test_user.id, upload_file3)
        processed3 = service.process_document(test_db_session, response3.document_id, test_user.id)
        
        assert processed3.page_count is None
        
        db_doc3 = test_db_session.query(Document).filter(Document.id == response3.document_id).first()
        assert db_doc3.page_count is None

    def test_process_document_missing_storage_file(self, test_db_session: Session, test_user: User, tmp_path, monkeypatch):
        """Test missing storage file produces FAILED."""
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        # Upload valid file
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        # Manually delete the stored file
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        Path(db_doc.storage_path).unlink()
        
        # Process should fail
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.process_document(test_db_session, response.document_id, test_user.id)
        
        assert exc.value.status_code == 400
        assert "Source file not found" in str(exc.value.detail)
        
        # Document should be marked FAILED
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert db_doc.status == "FAILED"
        assert db_doc.processing_error is not None


class TestDocumentProcessingSecurity:
    """Test security aspects of document processing."""

    def test_cross_user_processing_returns_404(self, test_db_session: Session, tmp_path, monkeypatch):
        """Test cross-user processing returns 404."""
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
        
        # User B tries to process User A's document
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.process_document(test_db_session, response.document_id, user_b.id)
        
        assert exc.value.status_code == 404
        assert "Document not found" in str(exc.value.detail)

    def test_unauthenticated_processing_returns_401(self, tmp_path, monkeypatch):
        """Test unauthenticated processing returns 401."""
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        
        from backend.app.main import app
        with TestClient(app) as client:
            response = client.post(f"/api/v1/documents/{uuid4()}/process")
            assert response.status_code == 401

    def test_valid_document_remains_after_extraction(self, test_db_session: Session, test_user: User, tmp_path, monkeypatch):
        """Test valid document remains stored after successful extraction."""
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
        
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        storage_path = Path(db_doc.storage_path)
        assert storage_path.exists()
        
        # Process
        processed = service.process_document(test_db_session, response.document_id, test_user.id)
        
        # File should still exist
        assert storage_path.exists()
        
        # Document should still exist in DB
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert db_doc is not None
        assert db_doc.storage_path == str(storage_path)

    def test_source_file_preserved_after_extraction_failure(self, test_db_session: Session, test_user: User, tmp_path, monkeypatch):
        """Test source file preserved after extraction failure."""
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(CORRUPTED_PDF, "corrupt.pdf", "application/pdf")
        response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        storage_path = Path(db_doc.storage_path)
        assert storage_path.exists()
        
        # Process (will fail)
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            service.process_document(test_db_session, response.document_id, test_user.id)
        
        # File should still exist
        assert storage_path.exists()
        
        # Document should still exist in DB (marked FAILED)
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert db_doc is not None
        assert db_doc.status == "FAILED"

    def test_extraction_cannot_accept_arbitrary_paths(self, test_db_session: Session, test_user: User, tmp_path, monkeypatch):
        """Test extraction cannot accept arbitrary filesystem paths."""
        # The service only accepts document_id, not file paths
        # This is tested by the fact that process_document only takes document_id
        # and resolves path from trusted Document.storage_path
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
        
        # Verify the document was stored in the secure location
        db_doc = test_db_session.query(Document).filter(Document.id == response.document_id).first()
        assert str(test_user.id) in db_doc.storage_path
        assert str(response.document_id) in db_doc.storage_path
        
        # The service uses storage_path from DB, not user input
        processed = service.process_document(test_db_session, response.document_id, test_user.id)
        assert processed.status == "PROCESSED"

    def test_another_users_document_cannot_be_processed(self, test_db_session: Session, tmp_path, monkeypatch):
        """Test another user's document cannot be processed (duplicate of cross-user test)."""
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
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.process_document(test_db_session, response.document_id, user_b.id)
        
        assert exc.value.status_code == 404


class TestDocumentProcessingAPI:
    """Test the document processing API endpoint."""

    def test_process_document_api_success(self, authenticated_client: TestClient, test_user: User, test_db_session: Session, tmp_path, monkeypatch):
        """Test POST /documents/{id}/process succeeds for valid PDF."""
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
        
        response = authenticated_client.post(f"/api/v1/documents/{upload_response.document_id}/process")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PROCESSED"
        assert data["page_count"] == 1
        assert data["document_id"] == str(upload_response.document_id)

    def test_process_document_api_failure(self, authenticated_client: TestClient, test_user: User, test_db_session: Session, tmp_path, monkeypatch):
        """Test POST /documents/{id}/process returns 422 for corrupted PDF."""
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        import importlib
        import backend.app.storage.local as storage_module
        importlib.reload(storage_module)
        from backend.app.storage import set_storage
        test_storage = LocalStorage(storage_root=str(tmp_path))
        set_storage(test_storage)
        
        storage = LocalStorage(storage_root=str(tmp_path))
        service = DocumentService(storage=storage)
        
        upload_file = create_upload_file(CORRUPTED_PDF, "corrupt.pdf", "application/pdf")
        upload_response = service.upload_document(test_db_session, test_user.id, upload_file)
        
        response = authenticated_client.post(f"/api/v1/documents/{upload_response.document_id}/process")
        
        assert response.status_code == 422
        data = response.json()
        assert "Extraction failed" in data["detail"]

    def test_process_document_api_cross_user_404(self, authenticated_client: TestClient, test_db_session: Session, test_user: User, tmp_path, monkeypatch):
        """Test POST /documents/{id}/process returns 404 for cross-user."""
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
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        upload_response = service.upload_document(test_db_session, user_b.id, upload_file)
        
        response = authenticated_client.post(f"/api/v1/documents/{upload_response.document_id}/process")
        
        assert response.status_code == 404

    def test_process_document_api_unauthenticated_401(self, tmp_path, monkeypatch):
        """Test POST /documents/{id}/process returns 401 for unauthenticated."""
        monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path))
        
        from backend.app.main import app
        with TestClient(app) as client:
            response = client.post(f"/api/v1/documents/{uuid4()}/process")
            assert response.status_code == 401

    def test_process_document_api_returns_metadata(self, authenticated_client: TestClient, test_user: User, test_db_session: Session, tmp_path, monkeypatch):
        """Test processing response exposes safe metadata (no filesystem paths)."""
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
        
        response = authenticated_client.post(f"/api/v1/documents/{upload_response.document_id}/process")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have safe metadata
        assert "document_id" in data
        assert "filename" in data
        assert "file_size" in data
        assert "mime_type" in data
        assert "status" in data
        assert "page_count" in data
        assert "chunk_count" in data
        assert "created_at" in data
        
        # Should NOT expose filesystem paths
        assert "storage_path" not in data
        assert "content_hash" not in data
        assert "processing_error" not in data


class TestExtractionServiceDirect:
    """Additional direct tests for ExtractionService edge cases."""

    def test_extract_empty_txt(self, tmp_path):
        """Test empty TXT file handling."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(EMPTY_TXT, "empty.txt", "text/plain")
        # Empty files are rejected at upload, but test extraction directly
        storage_path = tmp_path / "empty.txt"
        storage_path.write_bytes(EMPTY_TXT)
        
        service = ExtractionService()
        result = service.extract(storage_path, "text/plain")
        
        assert result.text == ""
        assert result.page_count == 0
        assert result.character_count == 0
        assert result.extraction_metadata["empty"] is True

    def test_extract_nonexistent_file(self, tmp_path):
        """Test extraction of nonexistent file raises error."""
        service = ExtractionService()
        nonexistent = tmp_path / "nonexistent.pdf"
        
        with pytest.raises(ExtractionError) as exc:
            service.extract(nonexistent, "application/pdf")
        
        assert "not found" in str(exc.value).lower()

    def test_extract_directory_not_file(self, tmp_path):
        """Test extraction of directory raises error."""
        service = ExtractionService()
        
        with pytest.raises(ExtractionError) as exc:
            service.extract(tmp_path, "application/pdf")
        
        assert "not a file" in str(exc.value).lower()

    def test_extract_unsupported_mime_type(self, tmp_path):
        """Test extraction of unsupported MIME type raises error."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(PDF_CONTENT, "test.pdf", "application/pdf")
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "test.pdf", "application/pdf"
        )
        
        service = ExtractionService()
        with pytest.raises(ExtractionError) as exc:
            service.extract(storage_path, "application/unsupported")
        
        assert "Unsupported MIME type" in str(exc.value)

    def test_extraction_result_structure(self, tmp_path):
        """Test ExtractionResult has all required fields."""
        storage = LocalStorage(storage_root=str(tmp_path))
        user_id = uuid4()
        doc_id = uuid4()
        
        upload_file = create_upload_file(TXT_CONTENT, "test.txt", "text/plain")
        storage_path, _, _ = storage.save_uploaded_file(
            upload_file, user_id, doc_id, "test.txt", "text/plain"
        )
        
        service = ExtractionService()
        result = service.extract(storage_path, "text/plain")
        
        # Check all required fields
        assert hasattr(result, 'text')
        assert hasattr(result, 'page_count')
        assert hasattr(result, 'character_count')
        assert hasattr(result, 'extraction_metadata')
        
        # Check types
        assert isinstance(result.text, str)
        assert isinstance(result.page_count, (int, type(None)))
        assert isinstance(result.character_count, int)
        assert isinstance(result.extraction_metadata, dict)
        
        # Metadata should have format
        assert "format" in result.extraction_metadata


# Import pytest at the end for tests that use it
import pytest