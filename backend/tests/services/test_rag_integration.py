"""
Tests for Task 5.8 - RAG Integration with CurioEngine.

Tests cover:
1. Retrieved passages are included in AIContext correctly
2. AIContext receives serializable context rather than ORM objects
3. RAG-disabled chat follows the existing behavior
4. Empty retrieval results do not break chat
5. Selected document filters are respected
6. Cross-user documents cannot enter source context
7. Invalid document selection is handled safely
8. Retrieval-provider failure follows the intended fallback policy
9. Message, evaluation, and SessionState persistence remain intact
10. Existing Teacher Mode and multi-turn tests remain compatible
11. The native vector column is populated and used by retrieval, verified against PostgreSQL
12. Source references correspond to actual retrieved chunks
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from backend.app.services.chat_service import ChatService
from backend.app.ai.schemas import AIContext, AIResult, AIResponse, CurrentQuestion, Mode, Strategy, TurnEvaluation, LearningDecision, StateUpdates, TeacherIntervention
from backend.app.retrieval import RetrievalService, RetrievalResult, RetrievedChunk, RetrievalError, create_retrieval_service
from backend.app.models.user import User
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.session import Session
from backend.app.schemas.message import MessageCreate
from backend.app.schemas.common import InputType as CommonInputType
from backend.app.embeddings import EmbeddingResult


def create_test_user(db):
    """Create a test user in the database."""
    user = User(email=f"test_{uuid4().hex[:8]}@curio.ai", hashed_password="test", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_chat_service_with_mock_retrieval(mock_engine, query_vector=None):
    """Create a ChatService with a mocked retrieval service for testing."""
    from unittest.mock import Mock
    
    service = ChatService(ai_engine=mock_engine)
    
    # Mock the embedding service on the retrieval service
    mock_embedding_service = Mock()
    if query_vector is None:
        query_vector = [1.0] + [0.0]*1535
    mock_embedding_service.generate_embeddings.return_value = EmbeddingResult(
        embeddings=[query_vector],
        model="test-model",
        dimensions=1536,
        total_tokens=10,
    )
    service.retrieval_service._embedding_service = mock_embedding_service
    
    return service


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


def create_test_chunks(db, document_id, texts, vectors=None, embedding_model="text-embedding-3-small"):
    """Create test chunks for a document with optional native vectors."""
    chunks = []
    for i, text in enumerate(texts):
        vector = vectors[i] if vectors and i < len(vectors) else None
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=i,
            text=text,
            embedding_vector=vector,
            embedding_model=embedding_model if vector else None,
        )
        db.add(chunk)
        chunks.append(chunk)
    db.commit()
    for chunk in chunks:
        db.refresh(chunk)
    return chunks


def create_dummy_db_session(session_id, current_mode="STUDENT", source_type="GENERAL", document_id=None):
    """Helper to mock a database Session and SessionState."""
    class MockSession:
        def __init__(self, session_id, current_mode, source_type, document_id):
            self.id = session_id
            self.topic = "Test Topic"
            self.source_type = source_type
            self.document_id = document_id
            self.user_id = uuid4()
            self.state = MockState(session_id, current_mode)
    
    class MockState:
        def __init__(self, session_id, current_mode):
            self.session_id = session_id
            self.current_mode = current_mode
            self.difficulty = 2
            self.confidence = 0.6
            self.active_concept = "Test Concept"
            self.current_question_id = None
            self.interrupted_question_id = None
            self.consecutive_strong_answers = 0
            self.consecutive_weak_answers = 0
            self.unresolved_misconceptions = []
            self.mastered_concepts = []
            self.teacher_attempt_count = 0
            self.teacher_intervention = None
            self.concept_mastery = {}
            self.misconception_counts = {}
            self.recent_strategy_history = []
            self.mode_switch_history = []
    
    return MockSession(session_id, current_mode, source_type, document_id)


def create_dummy_message(msg_id, session_id, sender, content, input_type="TEXT"):
    """Helper to mock a database Message."""
    class MockMessage:
        def __init__(self, msg_id, session_id, sender, content, input_type):
            self.id = msg_id
            self.session_id = session_id
            self.sender = sender
            self.content = content
            self.input_type = input_type
            self.created_at = datetime.now(timezone.utc)
    
    return MockMessage(msg_id, session_id, sender, content, input_type)


def create_mock_ai_result(
    next_mode=Mode.STUDENT,
    strategy=Strategy.PROBE_WHY,
    state_updates=None,
):
    """Helper to build a strongly-typed AIResult."""
    evaluation = TurnEvaluation(
        correctness=0.9,
        clarity=0.85,
        completeness=0.8,
        depth=0.7,
        relevance=1.0,
        stuck_probability=0.05,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["test_concept"],
        knowledge_gap=None,
        recommended_strategy=Strategy.INCREASE_DIFFICULTY,
        recommended_difficulty=3,
    )

    decision = LearningDecision(
        next_mode=next_mode,
        strategy=strategy,
        difficulty=3,
        confidence=0.8,
        reason="Test reason",
        active_concept="Test Concept",
        should_offer_termination=False,
        should_restore_interrupted_question=False,
    )

    response = AIResponse(
        content="Test response",
        mode=next_mode,
        strategy=strategy,
        difficulty=3,
        confidence=0.8,
    )

    updates = state_updates or StateUpdates(
        confidence=0.8,
        difficulty=3,
        active_concept="Test Concept",
        consecutive_successes=1,
        consecutive_failures=0,
    )

    return AIResult(
        evaluation=evaluation,
        decision=decision,
        response=response,
        state_updates=updates,
    )


class TestRAGIntegration:
    """Test RAG integration in ChatService."""

    def test_retrieved_passages_included_in_aicontext(self, test_db_session, test_user):
        """Test 1: Retrieved passages are included in AIContext correctly."""
        doc = create_test_document(test_db_session, test_user.id)
        
        # Create chunks with native vectors
        vectors = [
            [1.0] + [0.0]*1535,  # High similarity to query
            [0.0]*1536,
        ]
        texts = ["Photosynthesis converts light energy into chemical energy.", "Unrelated content."]
        create_test_chunks(test_db_session, doc.id, texts, vectors)
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc.id)
        db_session.user_id = test_user.id
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "How does photosynthesis work?")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Test response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="How does photosynthesis work?", input_type=CommonInputType.TEXT)
        # Use real test_db_session for retrieval, mock_db for other operations
        service.send_message(test_db_session, session_id, message_in, user_id=test_user.id)
        
        # Verify AIContext was passed with source_context
        mock_engine.process.assert_called_once()
        context: AIContext = mock_engine.process.call_args[0][0]
        
        assert context.source_context is not None
        assert "chunks" in context.source_context
        assert context.source_context["total_matches"] >= 1
        assert len(context.source_context["chunks"]) >= 1
        assert context.source_context["retrieval_status"] == "success"
        assert "Photosynthesis" in context.source_context["chunks"][0]["text"]

    def test_aicontext_receives_serializable_context(self, test_db_session, test_user):
        """Test 2: AIContext receives serializable context rather than ORM objects."""
        doc = create_test_document(test_db_session, test_user.id)
        vectors = [[1.0] + [0.0]*1535]
        texts = ["Serializable content."]
        create_test_chunks(test_db_session, doc.id, texts, vectors)
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc.id)
        db_session.user_id = test_user.id
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "Query")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="Query", input_type=CommonInputType.TEXT)
        # Use real test_db_session for retrieval, mock_db for other operations
        service.send_message(test_db_session, session_id, message_in, user_id=test_user.id)
        
        context: AIContext = mock_engine.process.call_args[0][0]
        
        # Verify source_context is serializable (no ORM objects)
        source_context = context.source_context
        assert source_context is not None
        assert isinstance(source_context, dict)
        assert isinstance(source_context["chunks"], list)
        
        chunk = source_context["chunks"][0]
        assert isinstance(chunk["chunk_id"], str)  # UUID serialized to string
        assert isinstance(chunk["document_id"], str)
        assert isinstance(chunk["chunk_index"], int)
        assert isinstance(chunk["text"], str)
        assert isinstance(chunk["similarity_score"], float)
        assert chunk["chunk_metadata"] is None or isinstance(chunk["chunk_metadata"], dict)
        
        # Verify no SQLAlchemy model objects
        import json
        json.dumps(source_context)  # Should not raise

    def test_rag_disabled_chat_follows_existing_behavior(self, test_db_session, test_user):
        """Test 3: RAG-disabled chat (GENERAL source mode) follows existing behavior."""
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        # Session with GENERAL source mode (no document)
        db_session = create_dummy_db_session(session_id, source_type="GENERAL", document_id=None)
        db_session.user_id = test_user.id
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "Hello")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Hi there!")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="Hello", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in, user_id=test_user.id)
        
        # Verify retrieval was NOT called (no document)
        context: AIContext = mock_engine.process.call_args[0][0]
        
        # source_context should be None or not set for GENERAL mode
        assert context.source_context is None or context.source_context == {}

    def test_empty_retrieval_results_do_not_break_chat(self, test_db_session, test_user):
        """Test 4: Empty retrieval results do not break chat."""
        doc = create_test_document(test_db_session, test_user.id)
        # Create chunks but with vectors that won't match the query
        vectors = [[0.0]*1536]  # Zero vector - low similarity
        texts = ["Irrelevant content."]
        create_test_chunks(test_db_session, doc.id, texts, vectors)
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc.id)
        db_session.user_id = test_user.id
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "Query about something else")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="Query about something else", input_type=CommonInputType.TEXT)
        response = service.send_message(mock_db, session_id, message_in, user_id=test_user.id)
        
        # Chat should still work
        assert response is not None
        
        context: AIContext = mock_engine.process.call_args[0][0]
        
        # source_context should indicate no results
        assert context.source_context is not None
        assert context.source_context["total_matches"] == 0
        assert context.source_context["chunks"] == []
        assert context.source_context["retrieval_status"] == "no_results"

    def test_selected_document_filter_respected(self, test_db_session, test_user):
        """Test 5: Selected document filters are respected."""
        doc1 = create_test_document(test_db_session, test_user.id, filename="doc1.pdf")
        doc2 = create_test_document(test_db_session, test_user.id, filename="doc2.pdf")
        
        # Create chunks with distinct content
        vectors = [[1.0] + [0.0]*1535] * 2
        texts1 = ["Document 1: Photosynthesis details."]
        texts2 = ["Document 2: Cellular respiration details."]
        create_test_chunks(test_db_session, doc1.id, texts1, vectors[:1])
        create_test_chunks(test_db_session, doc2.id, texts2, vectors[1:])
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        # Session linked to doc1 only
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc1.id)
        db_session.user_id = test_user.id
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "Query")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="Query", input_type=CommonInputType.TEXT)
        service.send_message(test_db_session, session_id, message_in, user_id=test_user.id)
        
        context: AIContext = mock_engine.process.call_args[0][0]
        
        # Only doc1 chunks should be retrieved
        assert context.source_context["total_matches"] == 1
        assert context.source_context["chunks"][0]["document_id"] == str(doc1.id)
        assert "Document 1" in context.source_context["chunks"][0]["text"]

    def test_cross_user_documents_cannot_enter_source_context(self, test_db_session):
        """Test 6: Cross-user documents cannot enter source context."""
        user1 = create_test_user(test_db_session)
        user2 = create_test_user(test_db_session)
        
        doc = create_test_document(test_db_session, user1.id)
        vectors = [[1.0] + [0.0]*1535]
        texts = ["User 1's private document."]
        create_test_chunks(test_db_session, doc.id, texts, vectors)
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        # Session owned by user2 but document_id points to user1's doc
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc.id)
        db_session.user_id = user2.id  # Different user!
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "Query")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="Query", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in, user_id=user2.id)
        
        context: AIContext = mock_engine.process.call_args[0][0]
        
        # Should get no results due to ownership check
        assert context.source_context is not None
        assert context.source_context["total_matches"] == 0
        assert context.source_context["chunks"] == []
        assert context.source_context["retrieval_status"] == "no_results"

    def test_invalid_document_selection_handled_safely(self, test_db_session, test_user):
        """Test 7: Invalid document selection is handled safely."""
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        # Session with non-existent document_id
        fake_doc_id = uuid4()
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=fake_doc_id)
        db_session.user_id = test_user.id
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "Query")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="Query", input_type=CommonInputType.TEXT)
        response = service.send_message(mock_db, session_id, message_in, user_id=test_user.id)
        
        # Chat should still work
        assert response is not None
        
        context: AIContext = mock_engine.process.call_args[0][0]
        
        # Should handle gracefully
        assert context.source_context is not None
        assert context.source_context["total_matches"] == 0
        assert context.source_context["retrieval_status"] == "no_results"

    def test_retrieval_provider_failure_fallback_policy(self, test_db_session, test_user):
        """Test 8: Retrieval-provider failure follows the intended fallback policy."""
        doc = create_test_document(test_db_session, test_user.id)
        vectors = [[1.0] + [0.0]*1535]
        texts = ["Relevant content."]
        create_test_chunks(test_db_session, doc.id, texts, vectors)
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        # Mock retrieval service to raise an error
        service.retrieval_service = MagicMock()
        service.retrieval_service.retrieve.side_effect = RetrievalError(
            "Embedding provider unavailable",
            "API timeout",
            retryable=True
        )
        
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc.id)
        db_session.user_id = test_user.id
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "Query")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="Query", input_type=CommonInputType.TEXT)
        response = service.send_message(mock_db, session_id, message_in, user_id=test_user.id)
        
        # Chat should still work despite retrieval failure
        assert response is not None
        
        context: AIContext = mock_engine.process.call_args[0][0]
        
        # source_context should indicate error
        assert context.source_context is not None
        assert context.source_context["total_matches"] == 0
        assert context.source_context["retrieval_status"] == "error"
        assert "error_message" in context.source_context
        assert context.source_context["error_retryable"] is True

    def test_persistence_remains_intact(self, test_db_session, test_user):
        """Test 9: Message, evaluation, and SessionState persistence remain intact."""
        doc = create_test_document(test_db_session, test_user.id)
        vectors = [[1.0] + [0.0]*1535]
        texts = ["Content for persistence test."]
        create_test_chunks(test_db_session, doc.id, texts, vectors)
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc.id)
        db_session.user_id = test_user.id
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "Test query")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Test response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="Test query", input_type=CommonInputType.TEXT)
        response = service.send_message(mock_db, session_id, message_in, user_id=test_user.id)
        
        # Verify all persistence calls were made
        service.message_repo.create_message.assert_called()  # User message
        assert service.message_repo.create_message.call_count == 2  # User + AI
        service.message_repo.create_evaluation.assert_called_once()
        service.session_repo.update_state.assert_called_once()
        
        # Verify response structure
        assert response.user_message.content == "Test query"
        assert response.ai_message.content == "Test response"

    def test_teacher_mode_compatibility(self, test_db_session, test_user):
        """Test 10: Existing Teacher Mode and multi-turn behavior remain compatible."""
        doc = create_test_document(test_db_session, test_user.id)
        vectors = [[1.0] + [0.0]*1535]
        texts = ["Teacher mode content."]
        create_test_chunks(test_db_session, doc.id, texts, vectors)
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        # Mock engine that transitions to TEACHER mode
        intervention = TeacherIntervention(
            active=True,
            gap="Test gap",
            attempt_count=1,
            verification_required=True,
        )
        updates = StateUpdates(
            current_mode=Mode.TEACHER,
            teacher_attempt_count=1,
            teacher_intervention=intervention,
            difficulty=2,
            confidence=0.3,
            active_concept="Test Concept",
        )
        ai_result = create_mock_ai_result(
            next_mode=Mode.TEACHER,
            strategy=Strategy.TEACH_GAP,
            state_updates=updates,
        )
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = ai_result
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc.id)
        db_session.user_id = test_user.id
        db_session.state.current_mode = "STUDENT"
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "I don't understand")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Let me explain")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="I don't understand", input_type=CommonInputType.TEXT)
        response = service.send_message(test_db_session, session_id, message_in, user_id=test_user.id)
        
        # Verify response
        assert response is not None
        assert response.decision.next_mode.value == "TEACHER"
        
        # Verify context had source_context even in teacher mode transition
        context: AIContext = mock_engine.process.call_args[0][0]
        assert context.source_context is not None
        assert context.source_context["retrieval_status"] == "success"
        
        # Verify state updates include teacher fields
        persisted_state = service.session_repo.update_state.call_args[0][2]
        assert persisted_state.teacher_attempt_count == 1
        assert persisted_state.teacher_intervention is not None

    def test_native_vector_column_used_by_retrieval(self, test_db_session, test_user):
        """Test 11: The native vector column is populated and used by retrieval."""
        doc = create_test_document(test_db_session, test_user.id)
        
        # Create chunk with only native vector (no legacy JSON embedding)
        vector = [1.0] + [0.0]*1535
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            text="Native vector test content.",
            embedding_vector=vector,
            embedding_model="text-embedding-3-small",
            # Note: embedding (JSON) is None
        )
        test_db_session.add(chunk)
        test_db_session.commit()
        test_db_session.refresh(chunk)
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc.id)
        db_session.user_id = test_user.id
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "Query about native vector")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="Query about native vector", input_type=CommonInputType.TEXT)
        service.send_message(test_db_session, session_id, message_in, user_id=test_user.id)
        
        context: AIContext = mock_engine.process.call_args[0][0]
        
        # Should retrieve using native vector column
        assert context.source_context is not None
        assert context.source_context["total_matches"] >= 1
        assert context.source_context["chunks"][0]["text"] == "Native vector test content."

    def test_source_references_correspond_to_retrieved_chunks(self, test_db_session, test_user):
        """Test 12: Source references correspond to actual retrieved chunks."""
        doc = create_test_document(test_db_session, test_user.id)
        
        vectors = [
            [0.9] + [0.1]*1535,  # High similarity
            [0.1] + [0.9]*1535,  # Low similarity
        ]
        texts = [
            "Chunk 0: First relevant passage about topic A.",
            "Chunk 1: Second passage about topic B.",
        ]
        create_test_chunks(test_db_session, doc.id, texts, vectors)
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        # Use query vector matching the first chunk (topic A)
        service = create_chat_service_with_mock_retrieval(mock_engine, query_vector=[0.9] + [0.1]*1535)
        
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc.id)
        db_session.user_id = test_user.id
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "Tell me about topic A")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="Tell me about topic A", input_type=CommonInputType.TEXT)
        service.send_message(test_db_session, session_id, message_in, user_id=test_user.id)
        
        context: AIContext = mock_engine.process.call_args[0][0]
        
        # First chunk should be the one about topic A (higher similarity)
        assert context.source_context["total_matches"] >= 1
        retrieved_chunk = context.source_context["chunks"][0]
        assert "topic a" in retrieved_chunk["text"].lower()
        assert retrieved_chunk["chunk_index"] == 0
        assert retrieved_chunk["similarity_score"] > 0.5
        
        # Verify all required fields present
        assert "chunk_id" in retrieved_chunk
        assert "document_id" in retrieved_chunk
        assert "start_char" in retrieved_chunk
        assert "end_char" in retrieved_chunk

    def test_empty_query_no_retrieval(self, test_db_session, test_user):
        """Test that empty queries don't trigger retrieval."""
        doc = create_test_document(test_db_session, test_user.id)
        vectors = [[1.0] + [0.0]*1535]
        texts = ["Content."]
        create_test_chunks(test_db_session, doc.id, texts, vectors)
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc.id)
        db_session.user_id = test_user.id
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in, user_id=test_user.id)
        
        context: AIContext = mock_engine.process.call_args[0][0]
        
        # Empty query should not trigger retrieval
        assert context.source_context is None or context.source_context == {}

    def test_whitespace_only_query_no_retrieval(self, test_db_session, test_user):
        """Test that whitespace-only queries don't trigger retrieval."""
        doc = create_test_document(test_db_session, test_user.id)
        vectors = [[1.0] + [0.0]*1535]
        texts = ["Content."]
        create_test_chunks(test_db_session, doc.id, texts, vectors)
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc.id)
        db_session.user_id = test_user.id
        
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "   ")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        message_in = MessageCreate(content="   ", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in, user_id=test_user.id)
        
        context: AIContext = mock_engine.process.call_args[0][0]
        
        # Whitespace-only query should not trigger retrieval
        assert context.source_context is None or context.source_context == {}

    def test_no_user_id_no_retrieval(self, test_db_session, test_user):
        """Test that retrieval is skipped when no user_id is provided."""
        doc = create_test_document(test_db_session, test_user.id)
        vectors = [[1.0] + [0.0]*1535]
        texts = ["Content."]
        create_test_chunks(test_db_session, doc.id, texts, vectors)
        
        session_id = uuid4()
        mock_db = MagicMock()
        
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result()
        
        service = create_chat_service_with_mock_retrieval(mock_engine)
        
        db_session = create_dummy_db_session(session_id, source_type="DOCUMENT", document_id=doc.id)
        db_session.user_id = test_user.id
        
        # When user_id=None, the code calls session_repo.get() not get_by_id_and_user()
        service.session_repo.get = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        
        user_msg = create_dummy_message(uuid4(), session_id, "USER", "Query")
        ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Response")
        service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
        service.message_repo.create_evaluation = MagicMock()
        
        # Call without user_id
        message_in = MessageCreate(content="Query", input_type=CommonInputType.TEXT)
        service.send_message(test_db_session, session_id, message_in, user_id=None)
        
        context: AIContext = mock_engine.process.call_args[0][0]
        
        # No user_id should skip retrieval
        assert context.source_context is None or context.source_context == {}


# Import settings for migration tests
from backend.app.core.config import settings


class TestMigrationCompatibility:
    """Test migration compatibility and data preservation."""

    def test_migration_head_single(self):
        """Test that migration head is single."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        
        config = Config("backend/alembic.ini")
        script = ScriptDirectory.from_config(config)
        heads = script.get_heads()
        assert len(heads) == 1, f"Expected single head, got: {heads}"

    def test_native_vector_column_exists(self, test_db_session):
        """Test that native vector column exists after migration."""
        from sqlalchemy import inspect
        
        inspector = inspect(test_db_session.bind)
        columns = [c['name'] for c in inspector.get_columns('document_chunks')]
        assert 'embedding_vector' in columns
        
        # Check vector type
        col_info = next(c for c in inspector.get_columns('document_chunks') if c['name'] == 'embedding_vector')
        assert 'vector' in str(col_info['type']).lower() or 'USER-DEFINED' == col_info.get('type', '')

    def test_hnsw_index_exists(self, test_db_session):
        """Test that HNSW index exists with correct parameters."""
        from sqlalchemy import inspect
        
        inspector = inspect(test_db_session.bind)
        indexes = [i['name'] for i in inspector.get_indexes('document_chunks')]
        assert 'ix_document_chunks_embedding_vector_hnsw' in indexes

    def test_existing_embeddings_preserved(self, test_db_session, test_user):
        """Test that existing JSON embeddings are preserved."""
        doc = create_test_document(test_db_session, test_user.id)
        
        # Create chunk with legacy JSON embedding
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            text="Legacy embedding",
            embedding=json.dumps([0.1, 0.2, 0.3] + [0.0]*1533),
            embedding_model="text-embedding-3-small",
        )
        test_db_session.add(chunk)
        test_db_session.commit()
        test_db_session.refresh(chunk)
        
        # Verify legacy embedding preserved
        test_db_session.refresh(chunk)
        assert chunk.embedding is not None
        assert chunk.embedding_model == "text-embedding-3-small"
        loaded = json.loads(chunk.embedding)
        assert loaded[0] == 0.1
        assert loaded[1] == 0.2
        assert loaded[2] == 0.3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])