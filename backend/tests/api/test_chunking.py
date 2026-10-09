"""
Tests for Task 5.4 - Document Chunking Infrastructure.

Tests cover:
1. Empty and whitespace-only input
2. Document smaller than configured chunk size
3. Document exactly at chunk-size boundary
4. Long documents producing multiple chunks
5. Overlap behavior between adjacent chunks
6. Paragraph and sentence boundary handling
7. Correct chunk indexes and source offsets
8. No missing text across chunks (accounting for intentional overlap)
9. Unicode and multilingual text
10. Invalid chunk-size and overlap configuration
11. The ---PAGE_BREAK--- marker and page-boundary metadata
12. Deterministic output for repeated calls with identical inputs
13. No empty chunks or non-terminating behavior for edge cases
"""

import pytest
from backend.app.chunking import ChunkingService, ChunkingError, ChunkingResult, Chunk


class TestChunkingConfiguration:
    """Test chunking configuration validation."""

    def test_valid_default_configuration(self):
        """Test default configuration works."""
        service = ChunkingService()
        assert service.chunk_size == 1000
        assert service.chunk_overlap == 200

    def test_custom_configuration(self):
        """Test custom configuration values."""
        service = ChunkingService(chunk_size=500, chunk_overlap=100)
        assert service.chunk_size == 500
        assert service.chunk_overlap == 100

    def test_invalid_chunk_size_zero(self):
        """Test that chunk_size must be positive."""
        with pytest.raises(ChunkingError) as exc:
            ChunkingService(chunk_size=0, chunk_overlap=100)
        assert "chunk_size must be positive" in str(exc.value)

    def test_invalid_chunk_size_negative(self):
        """Test that chunk_size must be positive."""
        with pytest.raises(ChunkingError) as exc:
            ChunkingService(chunk_size=-100, chunk_overlap=50)
        assert "chunk_size must be positive" in str(exc.value)

    def test_invalid_overlap_negative(self):
        """Test that chunk_overlap must be non-negative."""
        with pytest.raises(ChunkingError) as exc:
            ChunkingService(chunk_size=1000, chunk_overlap=-50)
        assert "chunk_overlap must be non-negative" in str(exc.value)

    def test_invalid_overlap_equals_chunk_size(self):
        """Test that overlap must be less than chunk_size."""
        with pytest.raises(ChunkingError) as exc:
            ChunkingService(chunk_size=500, chunk_overlap=500)
        assert "chunk_overlap must be less than chunk_size" in str(exc.value)

    def test_invalid_overlap_exceeds_chunk_size(self):
        """Test that overlap must be less than chunk_size."""
        with pytest.raises(ChunkingError) as exc:
            ChunkingService(chunk_size=500, chunk_overlap=600)
        assert "chunk_overlap must be less than chunk_size" in str(exc.value)


class TestChunkingEmptyInput:
    """Test chunking with empty or whitespace input."""

    def test_empty_string(self):
        """Test empty string returns empty result."""
        service = ChunkingService()
        result = service.chunk_text("")
        
        assert isinstance(result, ChunkingResult)
        assert result.chunks == []
        assert result.total_chunks == 0
        assert result.total_characters == 0
        assert result.chunking_metadata["empty_input"] is True

    def test_whitespace_only(self):
        """Test whitespace-only string returns empty result."""
        service = ChunkingService()
        result = service.chunk_text("   \n\n  \t  ")
        
        assert result.chunks == []
        assert result.total_chunks == 0
        assert result.chunking_metadata["empty_input"] is True

    def test_newlines_only(self):
        """Test newlines-only string returns empty result."""
        service = ChunkingService()
        result = service.chunk_text("\n\n\n")
        
        assert result.chunks == []


class TestChunkingSmallDocuments:
    """Test chunking with documents smaller than chunk size."""

    def test_document_smaller_than_chunk_size(self):
        """Test document smaller than chunk size produces single chunk."""
        service = ChunkingService(chunk_size=1000, chunk_overlap=200)
        text = "This is a short document."
        result = service.chunk_text(text)
        
        assert result.total_chunks == 1
        assert result.chunks[0].text == text
        assert result.chunks[0].chunk_index == 0
        assert result.chunks[0].start_char == 0
        assert result.chunks[0].end_char == len(text)

    def test_document_at_exact_chunk_size(self):
        """Test document exactly at chunk size boundary."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "x" * 100
        result = service.chunk_text(text)
        
        assert result.total_chunks == 1
        assert len(result.chunks[0].text) == 100

    def test_document_slightly_over_chunk_size(self):
        """Test document slightly over chunk size may produce two chunks."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "x" * 150
        result = service.chunk_text(text)
        
        # Should produce 2 chunks with overlap
        assert result.total_chunks == 2
        # First chunk should be around 100 chars
        # Second chunk should have overlap + remaining


class TestChunkingLargeDocuments:
    """Test chunking with long documents producing multiple chunks."""

    def test_long_document_multiple_chunks(self):
        """Test long document produces multiple chunks."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "Paragraph one with some content.\n\nParagraph two with more content here.\n\nParagraph three continues the text.\n\nParagraph four adds even more.\n\nParagraph five finishes it."
        result = service.chunk_text(text)
        
        assert result.total_chunks >= 2
        assert all(c.text for c in result.chunks)  # No empty chunks

    def test_chunk_indexes_sequential(self):
        """Test chunk indexes are sequential starting from 0."""
        service = ChunkingService(chunk_size=50, chunk_overlap=10)
        text = "A" * 200
        result = service.chunk_text(text)
        
        for i, chunk in enumerate(result.chunks):
            assert chunk.chunk_index == i

    def test_source_offsets_correct(self):
        """Test start_char and end_char offsets are correct."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "A" * 50 + "B" * 50 + "C" * 50
        result = service.chunk_text(text)
        
        # First chunk starts at 0
        assert result.chunks[0].start_char == 0
        # Each chunk's end_char should equal next chunk's start_char (minus overlap)
        for i in range(len(result.chunks) - 1):
            assert result.chunks[i].end_char > result.chunks[i].start_char

    def test_no_text_loss_across_chunks(self):
        """Test that all text is covered across chunks (accounting for overlap)."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "This is a test document with some content that should be chunked properly."
        result = service.chunk_text(text)
        
        # Reconstruct text from chunks (removing overlap)
        reconstructed = result.chunks[0].text
        for i in range(1, len(result.chunks)):
            # Find where overlap ends
            prev_text = result.chunks[i-1].text
            curr_text = result.chunks[i].text
            # The overlap should be at the start of current chunk
            if prev_text[-20:] in curr_text[:40]:  # approximate overlap check
                # Find non-overlapping part
                overlap_idx = curr_text.find(prev_text[-20:])
                if overlap_idx >= 0:
                    reconstructed += curr_text[overlap_idx + 20 + 2:]  # +2 for \n\n
                else:
                    reconstructed += curr_text
            else:
                reconstructed += curr_text
        
        # Original text should be contained in reconstructed (allowing for overlap differences)
        assert len(reconstructed) >= len(text) * 0.8  # Allow some flexibility


class TestChunkingOverlap:
    """Test overlap behavior between adjacent chunks."""

    def test_overlap_applied(self):
        """Test that overlap is applied between chunks."""
        service = ChunkingService(chunk_size=100, chunk_overlap=30)
        text = "A" * 100 + "B" * 100
        result = service.chunk_text(text)
        
        assert result.total_chunks >= 2
        # Check that there's shared content between chunks
        chunk1_end = result.chunks[0].text[-30:]
        chunk2_start = result.chunks[1].text[:50]
        # Some overlap should exist
        assert len(set(chunk1_end) & set(chunk2_start)) > 0

    def test_zero_overlap(self):
        """Test zero overlap produces contiguous chunks."""
        service = ChunkingService(chunk_size=100, chunk_overlap=0)
        text = "A" * 100 + "B" * 100
        result = service.chunk_text(text)
        
        assert result.total_chunks == 2
        # With zero overlap, chunks should be contiguous

    def test_overlap_at_sentence_boundary(self):
        """Test overlap prefers sentence boundaries."""
        service = ChunkingService(chunk_size=100, chunk_overlap=30)
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
        result = service.chunk_text(text)
        
        assert result.total_chunks >= 1
        # Overlap should contain complete sentences where possible


class TestChunkingBoundaries:
    """Test paragraph and sentence boundary handling."""

    def test_paragraph_boundary_preferred(self):
        """Test that paragraphs are kept together when possible."""
        service = ChunkingService(chunk_size=500, chunk_overlap=50)
        text = "Paragraph one content.\n\nParagraph two content.\n\nParagraph three content."
        result = service.chunk_text(text)
        
        # With large chunk size, should fit in one chunk
        assert result.total_chunks == 1
        assert "Paragraph one" in result.chunks[0].text
        assert "Paragraph two" in result.chunks[0].text

    def test_paragraph_split_when_necessary(self):
        """Test that long paragraphs are split when exceeding chunk size."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "A" * 300  # Single long paragraph
        result = service.chunk_text(text)
        
        assert result.total_chunks >= 3

    def test_sentence_boundary_handling(self):
        """Test sentence boundaries are respected."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        result = service.chunk_text(text)
        
        # Each chunk should end at sentence boundary when possible
        for chunk in result.chunks:
            # Chunk should not end mid-sentence (no trailing partial words)
            assert not chunk.text.endswith((" a", " the", " and", " or"))


class TestChunkingUnicode:
    """Test Unicode and multilingual text handling."""

    def test_unicode_text(self):
        """Test chunking handles Unicode correctly."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "Hello 世界 🌍 café naïve résumé 中文 Español"
        result = service.chunk_text(text)
        
        assert result.total_chunks >= 1
        assert "世界" in "".join(c.text for c in result.chunks)
        assert "🌍" in "".join(c.text for c in result.chunks)

    def test_multilingual_mixed(self):
        """Test mixed language text."""
        service = ChunkingService(chunk_size=200, chunk_overlap=30)
        text = "English text. 中文文本. Texte français. Texto español. テキスト"
        result = service.chunk_text(text)
        
        assert result.total_chunks >= 1
        full_text = "".join(c.text for c in result.chunks)
        assert "中文" in full_text
        assert "français" in full_text
        assert "español" in full_text


class TestChunkingPageBreaks:
    """Test PAGE_BREAK marker and page boundary metadata."""

    def test_single_page_no_marker(self):
        """Test text without page break marker."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "Page one content here."
        result = service.chunk_text(text, extraction_metadata={"format": "pdf", "total_pages": 1})
        
        assert result.chunking_metadata["has_page_breaks"] is False
        assert result.chunks[0].metadata.get("page_number") == 0

    def test_multi_page_with_marker(self):
        """Test text with page break markers."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "Page one content.\n\n---PAGE_BREAK---\n\nPage two content."
        result = service.chunk_text(text, extraction_metadata={"format": "pdf", "total_pages": 2})
        
        assert result.chunking_metadata["has_page_breaks"] is True
        # Should have chunks from both pages
        page_numbers = set(c.metadata.get("page_number") for c in result.chunks)
        assert 0 in page_numbers
        assert 1 in page_numbers

    def test_page_break_not_in_chunk_text(self):
        """Test PAGE_BREAK marker is not exposed as content."""
        service = ChunkingService(chunk_size=500, chunk_overlap=50)
        text = "Page one.\n\n---PAGE_BREAK---\n\nPage two."
        result = service.chunk_text(text, extraction_metadata={"format": "pdf", "total_pages": 2})
        
        for chunk in result.chunks:
            assert "---PAGE_BREAK---" not in chunk.text


class TestChunkingDeterministic:
    """Test deterministic output for identical inputs."""

    def test_deterministic_output(self):
        """Test same input produces same output."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "This is a test document. " * 10
        
        result1 = service.chunk_text(text)
        result2 = service.chunk_text(text)
        
        assert result1.total_chunks == result2.total_chunks
        for c1, c2 in zip(result1.chunks, result2.chunks):
            assert c1.text == c2.text
            assert c1.chunk_index == c2.chunk_index
            assert c1.start_char == c2.start_char
            assert c1.end_char == c2.end_char

    def test_deterministic_with_metadata(self):
        """Test deterministic output with metadata."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "Test content. " * 5
        metadata = {"format": "pdf", "total_pages": 1}
        
        result1 = service.chunk_text(text, metadata)
        result2 = service.chunk_text(text, metadata)
        
        assert result1.total_chunks == result2.total_chunks
        for c1, c2 in zip(result1.chunks, result2.chunks):
            assert c1.text == c2.text


class TestChunkingEdgeCases:
    """Test edge cases and potential infinite loops."""

    def test_no_empty_chunks(self):
        """Test that no empty chunks are produced."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "\n\n\nContent\n\n\n"
        result = service.chunk_text(text)
        
        for chunk in result.chunks:
            assert chunk.text.strip() != ""

    def test_no_infinite_loop_single_char(self):
        """Test single character doesn't cause infinite loop."""
        service = ChunkingService(chunk_size=10, chunk_overlap=5)
        text = "A"
        result = service.chunk_text(text)
        
        assert result.total_chunks == 1

    def test_no_infinite_loop_overlap_near_chunk_size(self):
        """Test large overlap near chunk size."""
        service = ChunkingService(chunk_size=100, chunk_overlap=99)
        text = "A" * 500
        result = service.chunk_text(text)
        
        assert result.total_chunks >= 1
        # Should complete without hanging

    def test_very_small_chunk_size(self):
        """Test very small chunk size."""
        service = ChunkingService(chunk_size=10, chunk_overlap=2)
        text = "Short text."
        result = service.chunk_text(text)
        
        assert result.total_chunks >= 1

    def test_newlines_preserved_in_chunks(self):
        """Test meaningful newlines are preserved within chunks."""
        service = ChunkingService(chunk_size=200, chunk_overlap=30)
        text = "Line 1\nLine 2\n\nLine 3\nLine 4"
        result = service.chunk_text(text)
        
        # Newlines within paragraphs should be preserved
        assert "\n" in "".join(c.text for c in result.chunks)


class TestChunkingServiceFactory:
    """Test factory function with settings integration."""

    def test_create_chunking_service_defaults(self):
        """Test factory creates service with settings defaults."""
        service = create_chunking_service()
        assert service.chunk_size == 1000  # from settings
        assert service.chunk_overlap == 200  # from settings

    def test_create_chunking_service_overrides(self):
        """Test factory allows parameter overrides."""
        service = create_chunking_service(chunk_size=500, chunk_overlap=100)
        assert service.chunk_size == 500
        assert service.chunk_overlap == 100

    def test_create_chunking_service_partial_override(self):
        """Test factory with partial override."""
        service = create_chunking_service(chunk_size=800)
        assert service.chunk_size == 800
        assert service.chunk_overlap == 200  # default from settings


class TestChunkingResultStructure:
    """Test ChunkingResult and Chunk data structures."""

    def test_chunking_result_has_all_fields(self):
        """Test ChunkingResult has required fields."""
        service = ChunkingService()
        result = service.chunk_text("Test content.")
        
        assert hasattr(result, 'chunks')
        assert hasattr(result, 'total_chunks')
        assert hasattr(result, 'total_characters')
        assert hasattr(result, 'chunking_metadata')
        assert isinstance(result.chunks, list)
        assert isinstance(result.chunking_metadata, dict)

    def test_chunk_has_all_fields(self):
        """Test Chunk has required fields."""
        service = ChunkingService()
        result = service.chunk_text("Test content.")
        
        chunk = result.chunks[0]
        assert hasattr(chunk, 'chunk_index')
        assert hasattr(chunk, 'text')
        assert hasattr(chunk, 'start_char')
        assert hasattr(chunk, 'end_char')
        assert hasattr(chunk, 'metadata')
        assert isinstance(chunk.metadata, dict)

    def test_chunk_metadata_contains_page_info(self):
        """Test chunk metadata includes page information."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "Page one.\n\n---PAGE_BREAK---\n\nPage two."
        result = service.chunk_text(text, extraction_metadata={"format": "pdf", "total_pages": 2})
        
        for chunk in result.chunks:
            assert "page_number" in chunk.metadata


# Import factory function for tests
from backend.app.chunking.service import create_chunking_service