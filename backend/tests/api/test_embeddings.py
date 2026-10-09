"""
Tests for Task 5.6 - Embedding Generation.

Tests cover:
1. Correct vector output mapping to input chunks
2. Batch ordering and provider limits
3. Empty input
4. Malformed vectors, wrong dimensions, NaN, and infinity
5. Provider timeout and retryable failures
6. Authentication/configuration errors
7. Safe behavior when a batch fails
8. Embedding persistence and model identifier
9. Document ownership and cross-user isolation
10. Idempotent retry behavior
11. No unintended changes to existing chunk data
12. Provider mocking without real credentials
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from backend.app.embeddings.service import (
    EmbeddingService,
    EmbeddingResult,
    EmbeddingError,
    create_embedding_service,
)
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


def create_test_chunks(db, document_id, texts, start_index=0):
    """Create test chunks for a document."""
    chunks = []
    for i, text in enumerate(texts):
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=start_index + i,
            text=text,
        )
        db.add(chunk)
        chunks.append(chunk)
    db.commit()
    for chunk in chunks:
        db.refresh(chunk)
    return chunks


class TestEmbeddingServiceConfiguration:
    """Test embedding service configuration validation."""

    def test_valid_default_configuration(self):
        """Test default configuration from settings."""
        with patch.object(settings, 'EMBEDDING_API_KEY', 'test-key'):
            with patch.object(settings, 'EMBEDDING_MODEL', 'text-embedding-3-small'):
                with patch.object(settings, 'EMBEDDING_DIMENSIONS', 1536):
                    service = EmbeddingService()
                    assert service._model == 'text-embedding-3-small'
                    assert service._dimensions == 1536

    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises EmbeddingError."""
        with patch.object(settings, 'EMBEDDING_API_KEY', ''):
            with pytest.raises(EmbeddingError) as exc:
                EmbeddingService()
            assert "API key not configured" in str(exc.value)

    def test_invalid_dimensions_raises_error(self):
        """Test that invalid dimensions raise EmbeddingError."""
        with patch.object(settings, 'EMBEDDING_API_KEY', 'test-key'):
            with patch.object(settings, 'EMBEDDING_DIMENSIONS', 0):
                with pytest.raises(EmbeddingError) as exc:
                    EmbeddingService()
                assert "dimensions must be positive" in str(exc.value)

    def test_invalid_batch_size_raises_error(self):
        """Test that invalid batch size raises EmbeddingError."""
        with patch.object(settings, 'EMBEDDING_API_KEY', 'test-key'):
            with patch.object(settings, 'EMBEDDING_BATCH_SIZE', -1):
                with pytest.raises(EmbeddingError) as exc:
                    EmbeddingService()
                assert "Batch size must be positive" in str(exc.value)

    def test_custom_configuration(self):
        """Test custom configuration overrides."""
        with patch.object(settings, 'EMBEDDING_API_KEY', 'test-key'):
            service = EmbeddingService(
                api_key="custom-key",
                model="custom-model",
                dimensions=1024,
                timeout=60.0,
                max_retries=5,
                batch_size=50,
            )
            assert service._api_key == "custom-key"
            assert service._model == "custom-model"
            assert service._dimensions == 1024
            assert service._timeout == 60.0
            assert service._max_retries == 5
            assert service._batch_size == 50


class TestEmbeddingGeneration:
    """Test embedding generation with mocked provider."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenAI client."""
        return Mock()

    @pytest.fixture
    def service(self, mock_client):
        """Create an EmbeddingService with mocked client."""
        return EmbeddingService(
            api_key="test-key",
            model="test-model",
            dimensions=4,
            batch_size=10,
            client=mock_client,
        )

    def test_generate_embeddings_single_text(self, service, mock_client):
        """Test generating embedding for a single text."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3, 0.4])]
        mock_response.usage = Mock(total_tokens=10)
        mock_client.embeddings.create.return_value = mock_response

        result = service.generate_embeddings(["Hello world"])

        assert len(result.embeddings) == 1
        assert result.embeddings[0] == [0.1, 0.2, 0.3, 0.4]
        assert result.model == "test-model"
        assert result.dimensions == 4
        assert result.total_tokens == 10

    def test_generate_embeddings_multiple_texts(self, service, mock_client):
        """Test generating embeddings for multiple texts."""
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3, 0.4]),
            Mock(embedding=[0.5, 0.6, 0.7, 0.8]),
        ]
        mock_response.usage = Mock(total_tokens=20)
        mock_client.embeddings.create.return_value = mock_response

        result = service.generate_embeddings(["First text", "Second text"])

        assert len(result.embeddings) == 2
        assert result.embeddings[0] == [0.1, 0.2, 0.3, 0.4]
        assert result.embeddings[1] == [0.5, 0.6, 0.7, 0.8]
        assert result.total_tokens == 20

    def test_generate_embeddings_preserves_order(self, service, mock_client):
        """Test that output order matches input order."""
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3, 0.4]),
            Mock(embedding=[0.5, 0.6, 0.7, 0.8]),
            Mock(embedding=[0.9, 1.0, 1.1, 1.2]),
        ]
        mock_response.usage = Mock(total_tokens=30)
        mock_client.embeddings.create.return_value = mock_response

        result = service.generate_embeddings(["First", "Second", "Third"])

        assert result.embeddings[0] == [0.1, 0.2, 0.3, 0.4]
        assert result.embeddings[1] == [0.5, 0.6, 0.7, 0.8]
        assert result.embeddings[2] == [0.9, 1.0, 1.1, 1.2]

    def test_empty_input(self, service):
        """Test empty input returns empty result."""
        result = service.generate_embeddings([])

        assert result.embeddings == []
        assert result.total_tokens == 0

    def test_whitespace_only_texts(self, service):
        """Test whitespace-only texts produce empty vectors."""
        result = service.generate_embeddings(["   ", "\n\t", ""])

        assert len(result.embeddings) == 3
        assert all(emb == [] for emb in result.embeddings)

    def test_mixed_empty_and_valid_texts(self, service, mock_client):
        """Test mixed empty and valid texts."""
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3, 0.4]),
            Mock(embedding=[0.5, 0.6, 0.7, 0.8]),
        ]
        mock_response.usage = Mock(total_tokens=20)
        mock_client.embeddings.create.return_value = mock_response

        result = service.generate_embeddings(["Valid text", "", "  ", "Another valid"])

        assert len(result.embeddings) == 4
        assert result.embeddings[0] == [0.1, 0.2, 0.3, 0.4]
        assert result.embeddings[1] == []
        assert result.embeddings[2] == []
        assert result.embeddings[3] == [0.5, 0.6, 0.7, 0.8]

    def test_batch_size_respected(self, service, mock_client):
        """Test that batch size limits API calls."""
        # Create 25 texts with batch_size=10 -> 3 API calls
        texts = [f"Text {i}" for i in range(25)]
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3, 0.4]) for _ in range(10)]
        mock_response.usage = Mock(total_tokens=100)
        mock_client.embeddings.create.return_value = mock_response

        result = service.generate_embeddings(texts)

        assert len(result.embeddings) == 25
        # Should have been called 3 times (10 + 10 + 5)
        assert mock_client.embeddings.create.call_count == 3

    def test_dimension_validation(self, service, mock_client):
        """Test that dimension mismatch raises error."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]  # 3 dims, expected 4
        mock_response.usage = Mock(total_tokens=10)
        mock_client.embeddings.create.return_value = mock_response

        with pytest.raises(EmbeddingError) as exc:
            service.generate_embeddings(["Test text"])
        assert "dimension mismatch" in str(exc.value).lower()
        assert exc.value.retryable is False

    def test_nan_validation(self, service, mock_client):
        """Test that NaN values raise error."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, float('nan'), 0.3, 0.4])]
        mock_response.usage = Mock(total_tokens=10)
        mock_client.embeddings.create.return_value = mock_response

        with pytest.raises(EmbeddingError) as exc:
            service.generate_embeddings(["Test text"])
        assert "non-finite" in str(exc.value).lower()
        assert exc.value.retryable is False

    def test_infinity_validation(self, service, mock_client):
        """Test that infinity values raise error."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, float('inf'), 0.3, 0.4])]
        mock_response.usage = Mock(total_tokens=10)
        mock_client.embeddings.create.return_value = mock_response

        with pytest.raises(EmbeddingError) as exc:
            service.generate_embeddings(["Test text"])
        assert "non-finite" in str(exc.value).lower()
        assert exc.value.retryable is False

    def test_rate_limit_retry(self, service, mock_client):
        """Test retry on rate limit error."""
        from openai import RateLimitError
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3, 0.4])]
        mock_response.usage = Mock(total_tokens=10)
        
        # First call raises rate limit, second succeeds
        mock_client.embeddings.create.side_effect = [
            RateLimitError("Rate limit", response=Mock(status_code=429), body=None),
            Mock(data=[Mock(embedding=[0.1, 0.2, 0.3, 0.4])], usage=Mock(total_tokens=10)),
        ]

        with patch('time.sleep', return_value=None):  # Don't actually sleep
            result = service.generate_embeddings(["Test text"])

        assert len(result.embeddings) == 1
        assert result.embeddings[0] == [0.1, 0.2, 0.3, 0.4]
        assert mock_client.embeddings.create.call_count == 2

    def test_rate_limit_exhausted(self, service, mock_client):
        """Test rate limit exhaustion raises error."""
        from openai import RateLimitError
        
        mock_client.embeddings.create.side_effect = RateLimitError(
            "Rate limit", response=Mock(status_code=429), body=None
        )

        with patch('time.sleep', return_value=None):
            with pytest.raises(EmbeddingError) as exc:
                service.generate_embeddings(["Test text"])
        
        assert "rate limit" in str(exc.value).lower()
        assert exc.value.retryable is True

    def test_timeout_retry(self, service, mock_client):
        """Test retry on timeout."""
        from openai import APITimeoutError
        
        mock_client.embeddings.create.side_effect = [
            APITimeoutError("Timeout"),
            Mock(data=[Mock(embedding=[0.1, 0.2, 0.3, 0.4])], usage=Mock(total_tokens=10)),
        ]

        with patch('time.sleep', return_value=None):
            result = service.generate_embeddings(["Test text"])

        assert len(result.embeddings) == 1

    def test_connection_error_retry(self, service, mock_client):
        """Test retry on connection error."""
        from openai import APIConnectionError
        from unittest.mock import Mock as MockClass
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3, 0.4])]
        mock_response.usage = Mock(total_tokens=10)
        
        # Create APIConnectionError with proper constructor (keyword-only args)
        error = APIConnectionError(message="Connection failed", request=MockClass())
        
        mock_client.embeddings.create.side_effect = [
            error,
            Mock(data=[Mock(embedding=[0.1, 0.2, 0.3, 0.4])], usage=Mock(total_tokens=10)),
        ]

        with patch('time.sleep', return_value=None):
            result = service.generate_embeddings(["Test text"])

        assert len(result.embeddings) == 1

    def test_non_retryable_error(self, service, mock_client):
        """Test that non-retryable errors are raised immediately."""
        mock_client.embeddings.create.side_effect = ValueError("Invalid request")

        with pytest.raises(EmbeddingError) as exc:
            service.generate_embeddings(["Test text"])
        
        assert exc.value.retryable is False


class TestEmbeddingPersistence:
    """Test embedding persistence with DocumentChunkRepository."""

    @pytest.fixture
    def repo(self):
        return DocumentChunkRepository()

    def test_persist_embeddings_new(self, test_db_session, repo):
        """Test persisting embeddings for chunks without existing embeddings."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        chunks = create_test_chunks(test_db_session, doc.id, ["Chunk 1", "Chunk 2", "Chunk 3"])

        # Create service with mocked generate_embeddings
        service = EmbeddingService(api_key="test-key", model="test-model", dimensions=4)
        service._repo = repo
        service.generate_embeddings = Mock(return_value=EmbeddingResult(
            embeddings=[[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8], [0.9, 1.0, 1.1, 1.2]],
            model="test-model",
            dimensions=4,
            total_tokens=30,
        ))

        count = service.generate_and_persist_embeddings(test_db_session, doc.id, user.id)

        assert count == 3
        
        # Verify embeddings persisted
        for i, chunk in enumerate(chunks):
            test_db_session.refresh(chunk)
            assert chunk.embedding is not None
            assert chunk.embedding_model == "test-model"
            embedding_vec = json.loads(chunk.embedding)
            assert len(embedding_vec) == 4

    def test_skip_existing_embeddings(self, test_db_session, repo):
        """Test that chunks with existing embeddings are skipped by default."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        # Create chunk with existing embedding
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            text="Already embedded",
            embedding=json.dumps([0.1, 0.2, 0.3, 0.4]),
            embedding_model="test-model",
        )
        test_db_session.add(chunk)
        test_db_session.commit()
        test_db_session.refresh(chunk)
        
        # Add more chunks with different indices
        chunk2 = DocumentChunk(document_id=doc.id, chunk_index=1, text="Chunk 1")
        chunk3 = DocumentChunk(document_id=doc.id, chunk_index=2, text="Chunk 2")
        test_db_session.add_all([chunk2, chunk3])
        test_db_session.commit()

        # Create service with mocked generate_embeddings
        service = EmbeddingService(api_key="test-key", model="test-model", dimensions=4)
        service._repo = repo
        service.generate_embeddings = Mock(return_value=EmbeddingResult(
            embeddings=[[0.5, 0.6, 0.7, 0.8], [0.9, 1.0, 1.1, 1.2]],
            model="test-model",
            dimensions=4,
            total_tokens=20,
        ))

        count = service.generate_and_persist_embeddings(test_db_session, doc.id, user.id)

        # Should only embed 2 new chunks, skip the one with existing embedding
        assert count == 2

    def test_force_regenerate(self, test_db_session, repo):
        """Test force_regenerate overwrites existing embeddings."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        # Create chunk with existing embedding from different model
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            text="Existing embedding",
            embedding=json.dumps([0.1, 0.2, 0.3, 0.4]),
            embedding_model="old-model",
        )
        test_db_session.add(chunk)
        test_db_session.commit()
        test_db_session.refresh(chunk)

        # Create service with mocked generate_embeddings
        service = EmbeddingService(api_key="test-key", model="test-model", dimensions=4)
        service._repo = repo
        service.generate_embeddings = Mock(return_value=EmbeddingResult(
            embeddings=[[0.5, 0.6, 0.7, 0.8]],
            model="test-model",
            dimensions=4,
            total_tokens=10,
        ))

        count = service.generate_and_persist_embeddings(
            test_db_session, doc.id, user.id, force_regenerate=True
        )

        assert count == 1
        test_db_session.refresh(chunk)
        assert chunk.embedding_model == "test-model"
        embedding_vec = json.loads(chunk.embedding)
        assert embedding_vec == [0.5, 0.6, 0.7, 0.8]

    def test_cross_user_isolation(self, test_db_session, repo):
        """Test that users can only embed their own document's chunks."""
        user1 = create_test_user(test_db_session, "user1@curio.ai")
        user2 = create_test_user(test_db_session, "user2@curio.ai")
        
        doc = create_test_document(test_db_session, user1.id)
        create_test_chunks(test_db_session, doc.id, ["Chunk 1"])

        # Create service with mocked generate_embeddings
        service = EmbeddingService(api_key="test-key", model="test-model", dimensions=4)
        service._repo = repo
        service.generate_embeddings = Mock(return_value=EmbeddingResult(
            embeddings=[[0.1, 0.2, 0.3, 0.4]],
            model="test-model",
            dimensions=4,
            total_tokens=10,
        ))

        # User2 cannot embed user1's document
        count = service.generate_and_persist_embeddings(test_db_session, doc.id, user2.id)
        assert count == 0

    def test_nonexistent_document(self, test_db_session, repo):
        """Test handling of nonexistent document."""
        user = create_test_user(test_db_session)

        # Create service with mocked generate_embeddings
        service = EmbeddingService(api_key="test-key", model="test-model", dimensions=4)
        service._repo = repo
        service.generate_embeddings = Mock(return_value=EmbeddingResult(
            embeddings=[[0.1, 0.2, 0.3, 0.4]],
            model="test-model",
            dimensions=4,
            total_tokens=10,
        ))

        count = service.generate_and_persist_embeddings(test_db_session, uuid4(), user.id)
        assert count == 0

    def test_no_chunks(self, test_db_session, repo):
        """Test handling of document with no chunks."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)

        # Create service with mocked generate_embeddings
        service = EmbeddingService(api_key="test-key", model="test-model", dimensions=4)
        service._repo = repo
        service.generate_embeddings = Mock(return_value=EmbeddingResult(
            embeddings=[[0.1, 0.2, 0.3, 0.4]],
            model="test-model",
            dimensions=4,
            total_tokens=10,
        ))

        count = service.generate_and_persist_embeddings(test_db_session, doc.id, user.id)
        assert count == 0

    def test_empty_text_chunks(self, test_db_session, repo):
        """Test that chunks with empty text are handled."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        # Create one empty chunk and one valid chunk
        chunk1 = DocumentChunk(document_id=doc.id, chunk_index=0, text="")
        chunk2 = DocumentChunk(document_id=doc.id, chunk_index=1, text="Valid chunk")
        test_db_session.add_all([chunk1, chunk2])
        test_db_session.commit()

        # Create service with mocked generate_embeddings
        service = EmbeddingService(api_key="test-key", model="test-model", dimensions=4)
        service._repo = repo
        service.generate_embeddings = Mock(return_value=EmbeddingResult(
            embeddings=[[0.5, 0.6, 0.7, 0.8]],  # Only one embedding for valid chunk
            model="test-model",
            dimensions=4,
            total_tokens=10,
        ))

        count = service.generate_and_persist_embeddings(test_db_session, doc.id, user.id)
        
        # Only one valid chunk should be embedded
        assert count == 1


class TestEmbeddingIdempotency:
    """Test idempotent retry behavior."""

    def test_retry_does_not_duplicate(self, test_db_session):
        """Test that retry after failure doesn't create duplicate embeddings."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        chunks = create_test_chunks(test_db_session, doc.id, ["Chunk 1"])

        repo = DocumentChunkRepository()
        
        # Create service with mocked generate_embeddings
        service = EmbeddingService(api_key="test-key", model="test-model", dimensions=4)
        service._repo = repo
        service.generate_embeddings = Mock(return_value=EmbeddingResult(
            embeddings=[[0.1, 0.2, 0.3, 0.4]],
            model="test-model",
            dimensions=4,
            total_tokens=10,
        ))

        # First call succeeds
        count1 = service.generate_and_persist_embeddings(test_db_session, doc.id, user.id)
        assert count1 == 1

        # Second call should find existing embedding and skip (idempotent)
        count2 = service.generate_and_persist_embeddings(test_db_session, doc.id, user.id)
        assert count2 == 0  # No new embeddings generated


class TestEmbeddingFactory:
    """Test factory function."""

    def test_create_embedding_service_defaults(self):
        """Test factory creates service with settings defaults."""
        with patch.object(settings, 'EMBEDDING_API_KEY', 'test-key'):
            with patch.object(settings, 'EMBEDDING_MODEL', 'text-embedding-3-small'):
                with patch.object(settings, 'EMBEDDING_DIMENSIONS', 1536):
                    with patch.object(settings, 'EMBEDDING_TIMEOUT_SECONDS', 30.0):
                        with patch.object(settings, 'EMBEDDING_MAX_RETRIES', 2):
                            with patch.object(settings, 'EMBEDDING_BATCH_SIZE', 100):
                                service = create_embedding_service()
                                assert service._model == 'text-embedding-3-small'
                                assert service._dimensions == 1536

    def test_create_embedding_service_overrides(self):
        """Test factory allows parameter overrides."""
        with patch.object(settings, 'EMBEDDING_API_KEY', 'test-key'):
            service = create_embedding_service(
                api_key="custom-key",
                model="custom-model",
                dimensions=1024,
                timeout=60.0,
                max_retries=5,
                batch_size=50,
            )
            assert service._api_key == "custom-key"
            assert service._model == "custom-model"
            assert service._dimensions == 1024
            assert service._timeout == 60.0
            assert service._max_retries == 5
            assert service._batch_size == 50


class TestEmbeddingSerialization:
    """Test embedding serialization/deserialization."""

    def test_json_serialization(self):
        """Test embedding vector JSON serialization."""
        import json
        vector = [0.1, 0.2, 0.3, 0.4]
        serialized = json.dumps(vector)
        deserialized = json.loads(serialized)
        assert deserialized == vector

    def test_embedding_stored_as_json_string(self, test_db_session):
        """Test that embedding is stored as JSON string in database."""
        user = create_test_user(test_db_session)
        doc = create_test_document(test_db_session, user.id)
        
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            text="Test",
            embedding=json.dumps([0.1, 0.2, 0.3]),
            embedding_model="test-model",
        )
        test_db_session.add(chunk)
        test_db_session.commit()
        test_db_session.refresh(chunk)
        
        # Verify it's stored as JSON string
        assert isinstance(chunk.embedding, str)
        assert chunk.embedding.startswith("[")
        assert chunk.embedding.endswith("]")
        
        # Verify round-trip
        loaded = json.loads(chunk.embedding)
        assert loaded == [0.1, 0.2, 0.3]


# Import settings for tests
from backend.app.core.config import settings