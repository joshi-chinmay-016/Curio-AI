"""
Text extraction service for PDF, TXT, and DOCX documents.

Provides safe, format-specific text extraction with page count tracking.
Does not perform OCR, chunking, embedding, or AI processing.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of document text extraction."""
    text: str
    page_count: Optional[int]
    character_count: int
    extraction_metadata: dict


class ExtractionError(Exception):
    """Raised when document extraction fails."""
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(message)


class ExtractionService:
    """
    Service for extracting text from stored document files.
    
    Supports:
    - PDF: page-by-page text extraction with page count
    - TXT: safe UTF-8 decoding with BOM handling
    - DOCX: paragraph text extraction with logical separation
    
    Does NOT perform:
    - OCR or scanned PDF recognition
    - Chunking
    - Embedding generation
    - AI-based content cleaning
    """

    def extract(self, file_path: Path, mime_type: str) -> ExtractionResult:
        """
        Extract text from a stored document file.
        
        Args:
            file_path: Path to the stored file (trusted, from Document.storage_path)
            mime_type: MIME type of the document
            
        Returns:
            ExtractionResult with text, page_count, character_count
            
        Raises:
            ExtractionError: If extraction fails
        """
        if not file_path.exists():
            raise ExtractionError("Source file not found", f"Path does not exist: {file_path}")
        
        if not file_path.is_file():
            raise ExtractionError("Source path is not a file", f"Path is not a regular file: {file_path}")
        
        try:
            if mime_type == "application/pdf":
                return self._extract_pdf(file_path)
            elif mime_type == "text/plain":
                return self._extract_txt(file_path)
            elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return self._extract_docx(file_path)
            else:
                raise ExtractionError(
                    "Unsupported MIME type for extraction",
                    f"MIME type: {mime_type}"
                )
        except ExtractionError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected extraction error for {file_path}")
            raise ExtractionError(
                "Extraction failed due to internal error",
                str(e)
            )

    def _extract_pdf(self, file_path: Path) -> ExtractionResult:
        """Extract text from PDF page by page."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ExtractionError("PDF extraction library not available", "pypdf not installed")
        
        try:
            reader = PdfReader(str(file_path))
        except Exception as e:
            raise ExtractionError("Failed to read PDF file", f"pypdf error: {e}")
        
        page_texts = []
        total_chars = 0
        
        for page_num, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                text = ""
            
            page_texts.append(text)
            total_chars += len(text)
        
        # Join with page boundaries preserved
        full_text = "\n\n---PAGE_BREAK---\n\n".join(page_texts)
        
        return ExtractionResult(
            text=full_text,
            page_count=len(reader.pages),
            character_count=total_chars,
            extraction_metadata={
                "format": "pdf",
                "pages_with_text": sum(1 for t in page_texts if t.strip()),
                "total_pages": len(reader.pages),
            }
        )

    def _extract_txt(self, file_path: Path) -> ExtractionResult:
        """Extract text from plain text file with safe UTF-8 handling."""
        try:
            # Read as binary first to handle BOM
            with open(file_path, "rb") as f:
                raw_content = f.read()
        except Exception as e:
            raise ExtractionError("Failed to read text file", f"IO error: {e}")
        
        if not raw_content:
            return ExtractionResult(
                text="",
                page_count=0,
                character_count=0,
                extraction_metadata={"format": "txt", "encoding": "utf-8", "empty": True}
            )
        
        # Handle UTF-8 BOM
        if raw_content.startswith(b"\xef\xbb\xbf"):
            raw_content = raw_content[3:]
            encoding_used = "utf-8-sig"
        else:
            encoding_used = "utf-8"
        
        # Decode with error handling
        try:
            text = raw_content.decode(encoding_used)
        except UnicodeDecodeError:
            # Fallback: replace undecodable bytes
            text = raw_content.decode("utf-8", errors="replace")
            encoding_used = "utf-8 (with replacement)"
        
        char_count = len(text)
        # For plain text, page_count is 1 if non-empty
        page_count = 1 if text.strip() else 0
        
        return ExtractionResult(
            text=text,
            page_count=page_count,
            character_count=char_count,
            extraction_metadata={
                "format": "txt",
                "encoding": encoding_used,
                "empty": char_count == 0,
            }
        )

    def _extract_docx(self, file_path: Path) -> ExtractionResult:
        """Extract paragraph text from DOCX file."""
        try:
            from docx import Document as DocxDocument
        except ImportError:
            raise ExtractionError("DOCX extraction library not available", "python-docx not installed")
        
        try:
            doc = DocxDocument(str(file_path))
        except Exception as e:
            raise ExtractionError("Failed to read DOCX file", f"python-docx error: {e}")
        
        paragraphs = []
        total_chars = 0
        
        for para in doc.paragraphs:
            text = para.text
            if text:
                paragraphs.append(text)
                total_chars += len(text)
        
        # Preserve paragraph boundaries with double newlines
        full_text = "\n\n".join(paragraphs)
        
        # DOCX doesn't have reliable physical page count through python-docx
        # Return None for page_count rather than fabricating
        return ExtractionResult(
            text=full_text,
            page_count=None,
            character_count=total_chars,
            extraction_metadata={
                "format": "docx",
                "paragraph_count": len(paragraphs),
            }
        )