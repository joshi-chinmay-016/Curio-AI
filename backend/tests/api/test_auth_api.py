"""
FastAPI Authentication API endpoint tests (Phase 2, Task 4):
- POST /api/v1/auth/register (success, duplicate, invalid email, short password, no leaked hash).
- POST /api/v1/auth/login (success, access token structure, wrong password, unknown email, inactive user).
- GET  /api/v1/auth/me (valid token, missing token, malformed token, expired token, nonexistent user, inactive user).
"""
from datetime import timedelta
import uuid
from fastapi.testclient import TestClient
import pytest

from backend.app.core.security import create_access_token
from backend.app.main import app
from backend.app.repositories.user_repository import UserRepository

pytestmark = pytest.mark.db_integration


@pytest.fixture
def api_client(override_get_db):
    with TestClient(app) as client:
        yield client


# ==============================================================================
# Registration Endpoint Tests
# ==============================================================================

def test_register_valid_user(api_client):
    """Verify POST /api/v1/auth/register creates user, returns 201, and excludes password hash."""
    email = f"learner_{uuid.uuid4().hex[:8]}@curio.ai"
    payload = {"email": email, "password": "SecurePassword123!"}

    res = api_client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["email"] == email.lower()
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    # Guarantee password or hash is never returned
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email(api_client):
    """Verify duplicate email registration returns 400 Bad Request."""
    email = f"duplicate_{uuid.uuid4().hex[:8]}@curio.ai"
    payload = {"email": email, "password": "FirstPassword123!"}

    res1 = api_client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = api_client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


def test_register_invalid_email_format(api_client):
    """Verify invalid email syntax returns 422 Unprocessable Entity."""
    payload = {"email": "not-an-email", "password": "ValidPassword123!"}
    res = api_client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422


def test_register_password_too_short(api_client):
    """Verify password shorter than 8 characters returns 422 Unprocessable Entity."""
    payload = {
        "email": f"shortpw_{uuid.uuid4().hex[:8]}@curio.ai",
        "password": "short",
    }
    res = api_client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422


# ==============================================================================
# Login Endpoint Tests
# ==============================================================================

def test_login_valid_credentials(api_client):
    """Verify POST /api/v1/auth/login returns 200 with JWT access token and bearer type."""
    email = f"login_{uuid.uuid4().hex[:8]}@curio.ai"
    password = "CorrectPassword123!"

    # Register first
    api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )

    # Login
    login_res = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()

    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] > 0
    assert isinstance(token_data["access_token"], str)


def test_login_wrong_password(api_client):
    """Verify wrong password returns 401 Unauthorized with WWW-Authenticate header."""
    email = f"wrongpw_{uuid.uuid4().hex[:8]}@curio.ai"
    password = "CorrectPassword123!"

    api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )

    login_res = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword999!"},
    )
    assert login_res.status_code == 401
    assert "www-authenticate" in login_res.headers
    assert "Bearer" in login_res.headers["www-authenticate"]
    assert login_res.json()["detail"] == "Invalid email or password"


def test_login_unknown_email(api_client):
    """Verify unknown email returns identical 401 Unauthorized without leaking email absence."""
    login_res = api_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent_user@curio.ai", "password": "AnyPassword123!"},
    )
    assert login_res.status_code == 401
    assert "www-authenticate" in login_res.headers
    assert login_res.json()["detail"] == "Invalid email or password"


def test_login_inactive_user(api_client, test_db_session):
    """Verify deactivated user account cannot log in and returns 400 Bad Request."""
    email = f"inactive_login_{uuid.uuid4().hex[:8]}@curio.ai"
    password = "ValidPassword123!"

    repo = UserRepository()
    user = repo.create(test_db_session, email=email, password=password)
    user.is_active = False
    test_db_session.commit()

    login_res = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 400
    assert "inactive" in login_res.json()["detail"].lower()


# ==============================================================================
# /auth/me Protected Endpoint Tests
# ==============================================================================

def test_auth_me_valid_token(api_client):
    """Verify GET /api/v1/auth/me returns authenticated user's profile with valid token."""
    email = f"me_valid_{uuid.uuid4().hex[:8]}@curio.ai"
    password = "ValidPassword123!"

    reg_res = api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    user_id = reg_res.json()["id"]

    login_res = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["access_token"]

    me_res = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()

    assert me_data["id"] == user_id
    assert me_data["email"] == email.lower()
    assert me_data["is_active"] is True
    assert "hashed_password" not in me_data
    assert "password" not in me_data


def test_auth_me_missing_token(api_client):
    """Verify GET /api/v1/auth/me returns 401 when Authorization header is omitted."""
    res = api_client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert "www-authenticate" in res.headers


def test_auth_me_malformed_token(api_client):
    """Verify GET /api/v1/auth/me returns 401 when token is garbage or malformed."""
    res = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert res.status_code == 401
    assert "www-authenticate" in res.headers
    assert res.json()["detail"] == "Could not validate credentials"


def test_auth_me_expired_token(api_client, test_db_session):
    """Verify GET /api/v1/auth/me returns 401 when token has expired."""
    repo = UserRepository()
    email = f"expired_me_{uuid.uuid4().hex[:8]}@curio.ai"
    user = repo.create(test_db_session, email=email, password="Password123!")

    # Generate token that expired 10 minutes ago
    expired_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=-10),
    )

    res = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Could not validate credentials"


def test_auth_me_nonexistent_user_in_token(api_client):
    """Verify GET /api/v1/auth/me returns 401 when token sub contains non-existent UUID."""
    random_uuid = str(uuid.uuid4())
    token = create_access_token(subject=random_uuid)

    res = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Could not validate credentials"


def test_auth_me_inactive_user(api_client, test_db_session):
    """Verify GET /api/v1/auth/me returns 400 when user is marked inactive."""
    repo = UserRepository()
    email = f"me_inactive_{uuid.uuid4().hex[:8]}@curio.ai"
    user = repo.create(test_db_session, email=email, password="Password123!")
    user.is_active = False
    test_db_session.commit()

    token = create_access_token(subject=str(user.id))

    res = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "inactive" in res.json()["detail"].lower()
