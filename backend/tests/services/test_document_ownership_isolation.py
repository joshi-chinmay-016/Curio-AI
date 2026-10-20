"""
Test suite verifying Document Ownership Isolation in ChatService and AI Context building.

Security Invariants Verified:
1. Authenticated user owning a document with chunks retrieves all chunks cleanly.
2. An authenticated user CANNOT access chunks of a document owned by another user.
3. An unauthenticated session (missing user_id) CANNOT access any document chunks.
4. Nonexistent document IDs fail safely and never trigger chunk retrieval.
5. Authorized empty documents (0 chunks) produce legitimate generic scaffold curricula
   without triggering any unscoped fallback queries.
6. Under no circumstances are unscoped DocumentChunk queries executed.
"""
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from backend.app.ai.document_curriculum import DocumentCurriculumStatus
from backend.app.ai.nodes.student_nodes import evaluation_node
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import AIContext, Mode, SessionInfo, SessionState, SourceMode
from backend.app.models.document import Document, DocumentChunk
from backend.app.services.chat_service import ChatService


def _create_mock_db_session(session_id: UUID, user_id: UUID = None, document_id: UUID = None, topic: str = "Test Topic"):
    db_session = MagicMock()
    db_session.id = session_id
    db_session.session_id = session_id
    db_session.user_id = user_id
    db_session.document_id = document_id
    db_session.topic = topic
    db_session.source_type = "DOCUMENT" if document_id else "GENERAL"
    db_session.state = MagicMock()
    db_session.state.current_mode = "STUDENT"
    db_session.state.difficulty = 1
    db_session.state.confidence = 0.5
    db_session.state.active_concept = ""
    db_session.state.current_question_id = None
    db_session.state.interrupted_question_id = None
    db_session.state.consecutive_strong_answers = 0
    db_session.state.consecutive_weak_answers = 0
    db_session.state.unresolved_misconceptions = []
    db_session.state.teacher_attempt_count = 0
    db_session.state.teacher_intervention = None
    db_session.state.concept_mastery = {}
    db_session.state.misconception_counts = {}
    db_session.state.recent_strategy_history = []
    db_session.state.mode_switch_history = []
    db_session.state.concept_model = None
    return db_session


def test_authenticated_user_owns_document_with_chunks():
    """
    Case 1: Authenticated user owns the requested document and it has chunks.
    Chunks are retrieved via repository scoped to user_id, and populated in AIContext.
    """
    chat_service = ChatService()
    user_id = uuid4()
    doc_id = uuid4()
    session_id = uuid4()

    db_session = _create_mock_db_session(session_id, user_id=user_id, document_id=doc_id, topic="Compilers")

    # Mock DB where user_id owns doc_id
    doc_rec = MagicMock()
    doc_rec.id = doc_id
    doc_rec.user_id = user_id
    doc_rec.filename = "compilers.pdf"
    doc_rec.file_size = 1024
    doc_rec.mime_type = "application/pdf"
    doc_rec.content_hash = "hash_compilers_v1"

    chunk_1 = MagicMock()
    chunk_1.id = uuid4()
    chunk_1.document_id = doc_id
    chunk_1.chunk_index = 0
    chunk_1.text = "Parsing transforms tokens into an AST."
    chunk_1.start_char = 0
    chunk_1.end_char = 38
    chunk_1.chunk_metadata = {"page_number": 1}

    chunk_2 = MagicMock()
    chunk_2.id = uuid4()
    chunk_2.document_id = doc_id
    chunk_2.chunk_index = 1
    chunk_2.text = "Code generation produces machine instructions."
    chunk_2.start_char = 39
    chunk_2.end_char = 85
    chunk_2.chunk_metadata = {"page_number": 2}

    mock_db = MagicMock()

    # Query mock: Document filter returns doc_rec if user_id matches
    def mock_query(model):
        q = MagicMock()
        if model is Document:
            def filter_mock(*args, **kwargs):
                f = MagicMock()
                f.first.return_value = doc_rec
                return f
            q.filter = filter_mock
            return q
        elif model is DocumentChunk:
            # DocumentChunk query should NOT be called directly with unscoped filter
            raise AssertionError("Unscoped db.query(DocumentChunk) was called! Must use repository.")
        return q

    mock_db.query = mock_query

    with patch("backend.app.repositories.document_chunk_repository.DocumentChunkRepository.get_chunks_by_document") as mock_get_chunks:
        mock_get_chunks.return_value = [chunk_1, chunk_2]

        ai_context = chat_service._build_ai_context(mock_db, session_id, db_session)

        # Verification
        assert ai_context.session.document_id == str(doc_id)
        assert ai_context.session.document_version == "hash_compilers_v1"
        assert ai_context.all_document_chunks is not None
        assert len(ai_context.all_document_chunks) == 2
        assert ai_context.all_document_chunks[0].chunk_id == str(chunk_1.id)
        assert ai_context.all_document_chunks[0].text == "Parsing transforms tokens into an AST."
        assert ai_context.all_document_chunks[1].page_number == 2

        # Verify repo method was called with verified user_id
        mock_get_chunks.assert_called_once_with(mock_db, str(doc_id), user_id)


def test_user_cannot_access_another_users_document_chunks():
    """
    Case 2: The requested document belongs to a different user.
    Ownership validation fails; document_id is cleared and zero chunks are retrieved.
    Under NO circumstance are chunks of another user returned.
    """
    chat_service = ChatService()
    owner_id = uuid4()
    attacker_user_id = uuid4()
    doc_id = uuid4()
    session_id = uuid4()

    # Session is run by attacker_user_id, referencing doc_id owned by owner_id
    db_session = _create_mock_db_session(session_id, user_id=attacker_user_id, document_id=doc_id, topic="Secret Financials")

    mock_db = MagicMock()

    # Document query enforces Document.user_id == attacker_user_id -> returns None!
    def mock_query(model):
        q = MagicMock()
        if model is Document:
            def filter_mock(*args, **kwargs):
                f = MagicMock()
                # Attacker is not the owner
                f.first.return_value = None
                return f
            q.filter = filter_mock
            return q
        elif model is DocumentChunk:
            raise AssertionError("Unscoped db.query(DocumentChunk) was called! Must enforce ownership.")
        return q

    mock_db.query = mock_query

    with patch("backend.app.repositories.document_chunk_repository.DocumentChunkRepository.get_chunks_by_document") as mock_get_chunks:
        ai_context = chat_service._build_ai_context(mock_db, session_id, db_session)

        # Verification: document_id is cleared from session, chunks are None
        assert ai_context.session.document_id is None
        assert ai_context.session.document_version is None
        assert ai_context.all_document_chunks is None
        # Repository must not be called with an unauthorized document
        mock_get_chunks.assert_not_called()


def test_missing_user_id_access_denied():
    """
    Case 3: User ID is missing (None / unauthenticated).
    Access is explicitly denied; no unscoped query is executed.
    """
    chat_service = ChatService()
    doc_id = uuid4()
    session_id = uuid4()

    db_session = _create_mock_db_session(session_id, user_id=None, document_id=doc_id, topic="General Topic")

    mock_db = MagicMock()

    def mock_query(model):
        if model is DocumentChunk:
            raise AssertionError("Unscoped db.query(DocumentChunk) was called without user_id!")
        q = MagicMock()
        q.filter.return_value.first.return_value = None
        return q

    mock_db.query = mock_query

    with patch("backend.app.repositories.document_chunk_repository.DocumentChunkRepository.get_chunks_by_document") as mock_get_chunks:
        ai_context = chat_service._build_ai_context(mock_db, session_id, db_session)

        assert ai_context.session.document_id is None
        assert ai_context.session.document_version is None
        assert ai_context.all_document_chunks is None
        mock_get_chunks.assert_not_called()


def test_nonexistent_document_cannot_load_chunks():
    """
    Case 4: The document ID does not exist in the database.
    Query returns None; chunks are None and unscoped retrieval is not performed.
    """
    chat_service = ChatService()
    user_id = uuid4()
    doc_id = uuid4()
    session_id = uuid4()

    db_session = _create_mock_db_session(session_id, user_id=user_id, document_id=doc_id, topic="Missing Doc")

    mock_db = MagicMock()

    def mock_query(model):
        q = MagicMock()
        if model is Document:
            q.filter.return_value.first.return_value = None
            return q
        elif model is DocumentChunk:
            raise AssertionError("Unscoped db.query(DocumentChunk) was called for nonexistent document!")
        return q

    mock_db.query = mock_query

    with patch("backend.app.repositories.document_chunk_repository.DocumentChunkRepository.get_chunks_by_document") as mock_get_chunks:
        ai_context = chat_service._build_ai_context(mock_db, session_id, db_session)

        assert ai_context.session.document_id is None
        assert ai_context.all_document_chunks is None
        mock_get_chunks.assert_not_called()


def test_authorized_empty_document_uses_scaffold_no_unscoped_retrieval():
    """
    Case 5: The authenticated user owns the document, but it has no chunks (e.g. empty PDF).
    AIContext sets all_document_chunks = [].
    evaluation_node builds a generic scaffold curriculum without triggering unscoped retrieval.
    """
    chat_service = ChatService()
    user_id = uuid4()
    doc_id = uuid4()
    session_id = uuid4()

    db_session = _create_mock_db_session(session_id, user_id=user_id, document_id=doc_id, topic="Empty PDF Topic")

    doc_rec = MagicMock()
    doc_rec.id = doc_id
    doc_rec.user_id = user_id
    doc_rec.filename = "empty.pdf"
    doc_rec.file_size = 0
    doc_rec.mime_type = "application/pdf"
    doc_rec.content_hash = "empty_hash_1"

    mock_db = MagicMock()

    def mock_query(model):
        q = MagicMock()
        if model is Document:
            q.filter.return_value.first.return_value = doc_rec
            return q
        elif model is DocumentChunk:
            raise AssertionError("Unscoped db.query(DocumentChunk) fallback was triggered for empty document!")
        return q

    mock_db.query = mock_query

    with patch("backend.app.repositories.document_chunk_repository.DocumentChunkRepository.get_chunks_by_document") as mock_get_chunks:
        # Document is owned by user, but has 0 chunks
        mock_get_chunks.return_value = []

        ai_context = chat_service._build_ai_context(mock_db, session_id, db_session)

        assert ai_context.session.document_id == str(doc_id)
        assert ai_context.session.document_version == "empty_hash_1"
        assert ai_context.all_document_chunks == []  # Explicit empty list, NOT None

        # Verify evaluation_node builds a legitimate generic scaffold curriculum
        state = {
            "context": ai_context,
            "provider": MockLLMProvider(),
        }
        eval_result = evaluation_node(state)
        concept_model = eval_result["concept_model"]

        assert concept_model is not None
        assert concept_model.metadata.get("is_generic_scaffold") is True
        assert concept_model.metadata.get("document_id") == str(doc_id)
        assert len(concept_model.concepts) == 4
        # Verify scaffold does not count as real source evidence
        assert all(c.metadata.get("is_generic_scaffold") is True for c in concept_model.concepts)
