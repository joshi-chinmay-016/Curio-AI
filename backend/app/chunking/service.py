"""
Chunking service for document text processing.

Provides deterministic, configurable text chunking with overlap support.
Designed for educational document RAG pipeline.
"""
from dataclasses import dataclass
from typing import List, Optional
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a single text chunk with metadata."""
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    metadata: dict


@dataclass
class ChunkingResult:
    """Result of document chunking operation."""
    chunks: List[Chunk]
    total_chunks: int
    total_characters: int
    chunking_metadata: dict


class ChunkingError(Exception):
    """Raised when chunking fails."""
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(message)


class ChunkingService:
    """
    Service for chunking extracted document text.
    
    Features:
    - Configurable target chunk size and overlap
    - Splits at paragraph/sentence boundaries when possible
    - Preserves page boundary metadata from extraction
    - Deterministic output for identical inputs
    - No empty chunks
    - Handles Unicode text correctly
    
    Does NOT perform:
    - Embedding generation
    - Vector search
    - AI-based content processing
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize chunking service with configuration.
        
        Args:
            chunk_size: Target chunk size in characters (must be > 0)
            chunk_overlap: Overlap between adjacent chunks in characters (must be >= 0 and < chunk_size)
            
        Raises:
            ChunkingError: If configuration is invalid
        """
        if chunk_size <= 0:
            raise ChunkingError("chunk_size must be positive", f"chunk_size={chunk_size}")
        if chunk_overlap < 0:
            raise ChunkingError("chunk_overlap must be non-negative", f"chunk_overlap={chunk_overlap}")
        if chunk_overlap >= chunk_size:
            raise ChunkingError("chunk_overlap must be less than chunk_size", f"chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Regex patterns for boundary detection
        self._paragraph_split = re.compile(r'\n\s*\n')
        self._sentence_split = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
        self._page_break_marker = "---PAGE_BREAK---"

    def chunk_text(self, text: str, extraction_metadata: Optional[dict] = None) -> ChunkingResult:
        """
        Chunk extracted text into overlapping segments.
        
        Args:
            text: Full extracted text from document
            extraction_metadata: Metadata from extraction (format, page boundaries, etc.)
            
        Returns:
            ChunkingResult with ordered chunks and metadata
            
        Raises:
            ChunkingError: If chunking fails
        """
        if not text or not text.strip():
            return ChunkingResult(
                chunks=[],
                total_chunks=0,
                total_characters=0,
                chunking_metadata={
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                    "empty_input": True,
                    "format": extraction_metadata.get("format", "unknown") if extraction_metadata else "unknown",
                }
            )
        
        try:
            chunks = self._create_chunks(text, extraction_metadata)
        except Exception as e:
            logger.exception("Unexpected chunking error")
            raise ChunkingError(
                "Chunking failed due to internal error",
                str(e)
            )
        
        return ChunkingResult(
            chunks=chunks,
            total_chunks=len(chunks),
            total_characters=len(text),
            chunking_metadata={
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "format": extraction_metadata.get("format", "unknown") if extraction_metadata else "unknown",
                "has_page_breaks": extraction_metadata.get("total_pages", 1) > 1 if extraction_metadata else False,
            }
        )

    def _create_chunks(self, text: str, extraction_metadata: Optional[dict] = None) -> List[Chunk]:
        """Create chunks using sliding window with boundary awareness."""
        # First, split by page breaks if present
        page_sections = self._split_by_page_breaks(text)
        
        all_chunks = []
        chunk_index = 0
        char_offset = 0
        
        for page_num, page_text in enumerate(page_sections):
            if not page_text.strip():
                # Skip empty pages but track character offset
                char_offset += len(page_text)
                if page_num < len(page_sections) - 1:
                    char_offset += len(self._page_break_marker) + 4  # \n\n + marker + \n\n
                continue
            
            page_chunks = self._chunk_page_text(
                page_text, 
                page_num, 
                chunk_index, 
                char_offset
            )
            all_chunks.extend(page_chunks)
            chunk_index += len(page_chunks)
            
            # Update character offset for next page
            char_offset += len(page_text)
            if page_num < len(page_sections) - 1:
                char_offset += len(self._page_break_marker) + 4
        
        # Apply overlap between chunks
        self._apply_overlap(all_chunks)
        
        return all_chunks

    def _split_by_page_breaks(self, text: str) -> List[str]:
        """Split text by page break markers."""
        if self._page_break_marker not in text:
            return [text]
        
        sections = text.split("\n\n---PAGE_BREAK---\n\n")
        return sections

    def _chunk_page_text(self, text: str, page_num: int, start_chunk_index: int, char_offset: int) -> List[Chunk]:
        """Chunk a single page's text using sliding window with boundary preference."""
        chunks = []
        text_len = len(text)
        
        if text_len <= self.chunk_size:
            # Text fits in one chunk
            chunk = Chunk(
                chunk_index=start_chunk_index,
                text=text.strip(),
                start_char=char_offset,
                end_char=char_offset + len(text.strip()),
                metadata={"page_number": page_num}
            )
            return [chunk]
        
        # Use sliding window approach with boundary preference
        position = 0
        while position < text_len:
            # Calculate window end
            window_end = min(position + self.chunk_size, text_len)
            
            # If not at end, try to find a good boundary
            if window_end < text_len:
                # Try paragraph boundary first
                para_boundary = self._find_paragraph_boundary(text, position, window_end)
                if para_boundary > position:
                    window_end = para_boundary
                else:
                    # Try sentence boundary
                    sent_boundary = self._find_sentence_boundary(text, position, window_end)
                    if sent_boundary > position:
                        window_end = sent_boundary
            
            chunk_text = text[position:window_end].strip()
            if chunk_text:
                chunk = Chunk(
                    chunk_index=start_chunk_index + len(chunks),
                    text=chunk_text,
                    start_char=char_offset + position,
                    end_char=char_offset + window_end,
                    metadata={"page_number": page_num}
                )
                chunks.append(chunk)
            
            # Move position forward
            if window_end >= text_len:
                break
                
            # Next position with overlap
            position = window_end - self.chunk_overlap
            if position <= chunks[-1].start_char - char_offset:
                # Ensure forward progress
                position = window_end
        
        return chunks

    def _find_paragraph_boundary(self, text: str, start: int, preferred_end: int) -> int:
        """Find paragraph boundary (double newline) near preferred_end."""
        # Search backward from preferred_end for paragraph break
        search_start = max(start, preferred_end - 200)
        search_end = min(preferred_end + 200, len(text))
        
        # Look for \n\n pattern
        for match in re.finditer(r'\n\s*\n', text[search_start:search_end]):
            abs_pos = search_start + match.end()
            if abs_pos > start and abs_pos <= preferred_end + 100:
                return abs_pos
        return preferred_end

    def _find_sentence_boundary(self, text: str, start: int, preferred_end: int) -> int:
        """Find sentence boundary near preferred_end."""
        search_start = max(start, preferred_end - 100)
        search_end = min(preferred_end + 100, len(text))
        
        # Look for sentence endings followed by space and capital
        for match in re.finditer(r'(?<=[.!?])\s+(?=[A-Z])', text[search_start:search_end]):
            abs_pos = search_start + match.end()
            if abs_pos > start and abs_pos <= preferred_end + 50:
                return abs_pos
        return preferred_end

    def _apply_overlap(self, chunks: List[Chunk]) -> None:
        """Apply overlap between adjacent chunks by prepending overlap from previous chunk."""
        if self.chunk_overlap <= 0 or len(chunks) < 2:
            return
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            
            # Get overlap text from end of previous chunk
            overlap_text = self._get_overlap_text(prev_chunk.text)
            
            if overlap_text and overlap_text not in curr_chunk.text[:len(overlap_text) + 10]:
                # Prepend overlap to current chunk
                new_text = overlap_text + "\n\n" + curr_chunk.text
                curr_chunk.text = new_text
                curr_chunk.start_char = curr_chunk.start_char - len(overlap_text) - 2
                curr_chunk.end_char = curr_chunk.start_char + len(new_text)

    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from the end of a chunk, preferring sentence boundaries."""
        if not text or self.chunk_overlap <= 0:
            return ""
        
        if len(text) <= self.chunk_overlap:
            return text
        
        # Take the last chunk_overlap characters
        overlap_region = text[-self.chunk_overlap:]
        
        # Try to find a sentence boundary in the overlap region
        sentences = re.split(r'(?<=[.!?])\s+', overlap_region)
        if len(sentences) > 1:
            # Return from the last sentence boundary
            return sentences[-1]
        
        return overlap_region


def create_chunking_service(
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> ChunkingService:
    """
    Factory function to create ChunkingService with settings from config.
    
    Args:
        chunk_size: Override default chunk size (from settings if None)
        chunk_overlap: Override default overlap (from settings if None)
        
    Returns:
        Configured ChunkingService instance
    """
    from backend.app.core.config import settings
    
    size = chunk_size if chunk_size is not None else settings.CHUNK_SIZE
    overlap = chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP
    
    return ChunkingService(chunk_size=size, chunk_overlap=overlap)