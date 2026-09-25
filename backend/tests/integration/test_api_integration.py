"""
Comprehensive FastAPI Endpoint Integration Tests for Curio AI Backend.

These tests execute against the dedicated, isolated 'curio_test_db'
through FastAPI's dependency override system with connection-level savepoint transactions.

Safety & Isolation Guarantees:
- Strictly operates against TEST_DATABASE_URL (curio_test_db).
- Never touches or writes to curio_db.
- Uses nested transaction savepoints so all writes roll back on teardown.
- No Base.metadata.create_all() or Alembic downgrades.
"""

from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.session import SessionState
from backend.app.models.user import User
import uuid
from backend.app.core.security import create_access_token


pytestmark = pytest.mark.db_integration


@pytest.fixture
def api_client(override_get_db, test_db_session):
    """
    TestClient fixture bound to the isolated PostgreSQL test database session.
    All commits within route handlers are captured by the nested savepoint
    and rolled back cleanly on fixture exit.

    Dynamically provisions a unique test user in the test database and
    sets a valid JWT Authorization header so all authenticated endpoints work.
    """
    user = User(email=f"api_test_{uuid.uuid4().hex[:8]}@curio.ai", is_active=True)
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)

    token = create_access_token(subject=str(user.id))
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


def test_api_health_check(api_client):
    """Verify GET /health returns status 200 and expected payload structure."""
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert data["database"] == "connected"


def test_api_create_and_get_session(api_client):
    """Verify POST /api/v1/sessions creates a session and GET /api/v1/sessions/{id} retrieves it."""
    payload = {
        "topic": "Quantum Computing Fundamentals",
        "source_type": "GENERAL"
    }
    create_res = api_client.post("/api/v1/sessions", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()

    assert "id" in created_data
    session_id = created_data["id"]
    assert created_data["topic"] == "Quantum Computing Fundamentals"
    assert created_data["source_type"] == "GENERAL"
    assert created_data["status"] == "ACTIVE"
    assert created_data["state"] is not None
    assert created_data["state"]["current_mode"] == "STUDENT"
    assert created_data["state"]["difficulty"] == 1
    assert created_data["state"]["confidence"] == 0.0

    # Retrieve session by ID
    get_res = api_client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    retrieved_data = get_res.json()
    assert retrieved_data["id"] == session_id
    assert retrieved_data["topic"] == "Quantum Computing Fundamentals"


def test_api_create_session_validation_error(api_client):
    """Verify POST /api/v1/sessions returns 422 on invalid or missing payload fields."""
    # Missing required 'topic' field
    res_missing_topic = api_client.post("/api/v1/sessions", json={"source_type": "GENERAL"})
    assert res_missing_topic.status_code == 422

    # Invalid enum value for 'source_type'
    res_invalid_enum = api_client.post("/api/v1/sessions", json={
        "topic": "Calculus",
        "source_type": "NON_EXISTENT_SOURCE"
    })
    assert res_invalid_enum.status_code == 422


def test_api_list_sessions(api_client):
    """Verify GET /api/v1/sessions returns a list of session summaries."""
    # Create two sessions
    s1 = api_client.post("/api/v1/sessions", json={"topic": "Linear Algebra", "source_type": "GENERAL"}).json()
    s2 = api_client.post("/api/v1/sessions", json={"topic": "Graph Theory", "source_type": "GENERAL"}).json()

    res = api_client.get("/api/v1/sessions")
    assert res.status_code == 200
    session_list = res.json()
    assert isinstance(session_list, list)
    assert len(session_list) >= 2

    session_ids = [item["session_id"] for item in session_list]
    assert s1["id"] in session_ids
    assert s2["id"] in session_ids

    # Validate summary fields
    first_summary = next(item for item in session_list if item["session_id"] == s1["id"])
    assert first_summary["topic"] == "Linear Algebra"
    assert first_summary["status"] == "ACTIVE"
    assert first_summary["current_mode"] == "STUDENT"
    assert "difficulty" in first_summary
    assert "confidence" in first_summary


def test_api_patch_session(api_client):
    """Verify PATCH /api/v1/sessions/{session_id} updates session attributes."""
    created = api_client.post("/api/v1/sessions", json={"topic": "Organic Chemistry", "source_type": "GENERAL"}).json()
    session_id = created["id"]

    patch_res = api_client.patch(f"/api/v1/sessions/{session_id}", json={
        "topic": "Advanced Organic Chemistry",
        "status": "PAUSED"
    })
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["topic"] == "Advanced Organic Chemistry"
    assert updated_data["status"] == "PAUSED"


def test_api_pause_and_resume_session(api_client):
    """Verify POST /api/v1/sessions/{session_id}/pause and /resume lifecycle transitions."""
    created = api_client.post("/api/v1/sessions", json={"topic": "World History", "source_type": "GENERAL"}).json()
    session_id = created["id"]

    # Pause
    pause_res = api_client.post(f"/api/v1/sessions/{session_id}/pause")
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "PAUSED"

    # Resume
    resume_res = api_client.post(f"/api/v1/sessions/{session_id}/resume")
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "ACTIVE"


def test_api_delete_session(api_client):
    """Verify DELETE /api/v1/sessions/{session_id} deletes the session and returns 204."""
    created = api_client.post("/api/v1/sessions", json={"topic": "Temporary Session", "source_type": "GENERAL"}).json()
    session_id = created["id"]

    # Delete session
    delete_res = api_client.delete(f"/api/v1/sessions/{session_id}")
    assert delete_res.status_code == 204

    # Subsequent GET returns 404
    get_res = api_client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 404

    # Subsequent DELETE returns 404
    delete_res_again = api_client.delete(f"/api/v1/sessions/{session_id}")
    assert delete_res_again.status_code == 404


def test_api_session_not_found_errors(api_client):
    """Verify 404 responses when operating on nonexistent session UUIDs."""
    random_id = uuid4()
    assert api_client.get(f"/api/v1/sessions/{random_id}").status_code == 404
    assert api_client.patch(f"/api/v1/sessions/{random_id}", json={"topic": "Ghost"}).status_code == 404
    assert api_client.delete(f"/api/v1/sessions/{random_id}").status_code == 404
    assert api_client.post(f"/api/v1/sessions/{random_id}/pause").status_code == 404
    assert api_client.post(f"/api/v1/sessions/{random_id}/resume").status_code == 404
    assert api_client.post(f"/api/v1/sessions/{random_id}/end").status_code == 404


def test_api_send_and_get_messages(api_client):
    """Verify POST /api/v1/sessions/{session_id}/messages processes a turn and GET returns history."""
    created = api_client.post("/api/v1/sessions", json={"topic": "Microbiology", "source_type": "GENERAL"}).json()
    session_id = created["id"]

    # Send first message
    msg_payload = {
        "content": "Bacteria reproduce through binary fission, doubling their population exponentially.",
        "input_type": "TEXT"
    }
    chat_res = api_client.post(f"/api/v1/sessions/{session_id}/messages", json=msg_payload)
    assert chat_res.status_code == 200
    turn = chat_res.json()

    # Verify user message
    assert turn["user_message"]["sender"] == "USER"
    assert turn["user_message"]["content"] == msg_payload["content"]
    assert turn["user_message"]["input_type"] == "TEXT"

    # Verify AI message
    assert turn["ai_message"]["sender"] == "AI"
    assert len(turn["ai_message"]["content"]) > 0

    # Verify evaluation
    assert "correctness" in turn["evaluation"]
    assert "clarity" in turn["evaluation"]
    assert "stuck_probability" in turn["evaluation"]
    assert "recommended_strategy" in turn["evaluation"]

    # Verify decision
    assert "next_mode" in turn["decision"]
    assert "strategy" in turn["decision"]
    assert "difficulty" in turn["decision"]

    # Retrieve message history
    history_res = api_client.get(f"/api/v1/sessions/{session_id}/messages")
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 2
    assert history[0]["sender"] == "USER"
    assert history[1]["sender"] == "AI"


def test_api_send_message_missing_session(api_client):
    """Verify POST /api/v1/sessions/{session_id}/messages returns 404 for missing session."""
    random_id = uuid4()
    msg_payload = {"content": "Hello", "input_type": "TEXT"}
    res = api_client.post(f"/api/v1/sessions/{random_id}/messages", json=msg_payload)
    assert res.status_code == 404


def test_api_send_message_validation_error(api_client):
    """Verify POST /api/v1/sessions/{session_id}/messages returns 422 on invalid payload."""
    created = api_client.post("/api/v1/sessions", json={"topic": "Physics", "source_type": "GENERAL"}).json()
    session_id = created["id"]

    # Missing content
    res_empty = api_client.post(f"/api/v1/sessions/{session_id}/messages", json={})
    assert res_empty.status_code == 422

    # Invalid input_type
    res_invalid = api_client.post(f"/api/v1/sessions/{session_id}/messages", json={
        "content": "Hello",
        "input_type": "TELEPATHY"
    })
    assert res_invalid.status_code == 422


def test_api_teacher_mode_interaction(api_client, override_get_db):
    """Verify chat turn handling when the session state is set to TEACHER mode."""
    created = api_client.post("/api/v1/sessions", json={"topic": "Thermodynamics", "source_type": "GENERAL"}).json()
    session_id = created["id"]

    # Transition state to TEACHER mode in the isolated database session
    db_session = override_get_db
    state = db_session.query(SessionState).filter_by(session_id=UUID(session_id)).first()
    assert state is not None
    state.current_mode = "TEACHER"
    db_session.commit()

    # Send message in TEACHER mode
    msg_payload = {
        "content": "I am struggling to understand why entropy always increases in an isolated system.",
        "input_type": "TEXT"
    }
    chat_res = api_client.post(f"/api/v1/sessions/{session_id}/messages", json=msg_payload)
    assert chat_res.status_code == 200
    turn = chat_res.json()

    assert turn["user_message"]["sender"] == "USER"
    assert turn["ai_message"]["sender"] == "AI"
    assert turn["evaluation"] is not None
    assert turn["decision"] is not None


def test_api_end_session_and_get_report(api_client):
    """Verify POST /api/v1/sessions/{session_id}/end compiles report and GET retrieves it."""
    created = api_client.post("/api/v1/sessions", json={"topic": "Economics", "source_type": "GENERAL"}).json()
    session_id = created["id"]

    # Generate at least one message turn
    api_client.post(f"/api/v1/sessions/{session_id}/messages", json={
        "content": "Supply and demand reach equilibrium when market quantity matches consumer demand.",
        "input_type": "TEXT"
    })

    # End session and compile report
    end_res = api_client.post(f"/api/v1/sessions/{session_id}/end")
    assert end_res.status_code == 200
    report = end_res.json()

    assert report["session_id"] == session_id
    assert "understanding_score" in report
    assert "mastery_level" in report
    assert "strengths" in report
    assert "concepts_mastered" in report
    assert "created_at" in report
    assert report["created_at"] is not None

    # Verify session is marked COMPLETED
    session_res = api_client.get(f"/api/v1/sessions/{session_id}")
    assert session_res.status_code == 200
    assert session_res.json()["status"] == "COMPLETED"
    assert session_res.json()["ended_at"] is not None

    # Retrieve report via GET endpoint
    get_report_res = api_client.get(f"/api/v1/sessions/{session_id}/report")
    assert get_report_res.status_code == 200
    retrieved_report = get_report_res.json()
    assert retrieved_report["session_id"] == session_id
    assert retrieved_report["understanding_score"] == report["understanding_score"]


def test_api_get_report_not_found(api_client):
    """Verify GET /api/v1/sessions/{session_id}/report returns 404 when report has not been compiled."""
    created = api_client.post("/api/v1/sessions", json={"topic": "Incomplete Session", "source_type": "GENERAL"}).json()
    session_id = created["id"]

    res = api_client.get(f"/api/v1/sessions/{session_id}/report")
    assert res.status_code == 404
    assert "Report not found" in res.json()["detail"]


def test_api_document_upload_and_retrieval(api_client):
    """Verify POST /api/v1/documents uploads file and GET /api/v1/documents/{id} retrieves metadata."""
    file_content = b"Photosynthesis is the process by which green plants make carbohydrates."
    upload_res = api_client.post(
        "/api/v1/documents",
        files={"file": ("biology_notes.txt", file_content, "text/plain")}
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()

    assert "document_id" in doc_data
    doc_id = doc_data["document_id"]
    assert doc_data["filename"] == "biology_notes.txt"
    assert doc_data["file_size"] == len(file_content)
    assert doc_data["mime_type"] == "text/plain"

    # Retrieve document metadata
    get_doc_res = api_client.get(f"/api/v1/documents/{doc_id}")
    assert get_doc_res.status_code == 200
    retrieved_doc = get_doc_res.json()
    assert retrieved_doc["document_id"] == doc_id
    assert retrieved_doc["filename"] == "biology_notes.txt"

    # Nonexistent document returns 404
    assert api_client.get(f"/api/v1/documents/{uuid4()}").status_code == 404


def test_api_isolation_marker_step_1(api_client):
    """Write an API marker session to test isolation between test functions."""
    res = api_client.post("/api/v1/sessions", json={
        "topic": "API_ISOLATION_CHECK_MARKER",
        "source_type": "GENERAL"
    })
    assert res.status_code == 201


def test_api_isolation_marker_step_2(api_client):
    """Verify previous test's API writes were rolled back and do not leak into this test."""
    list_res = api_client.get("/api/v1/sessions")
    assert list_res.status_code == 200
    topics = [s["topic"] for s in list_res.json()]
    assert "API_ISOLATION_CHECK_MARKER" not in topics, (
        "API Test isolation failure: marker session leaked across tests!"
    )
