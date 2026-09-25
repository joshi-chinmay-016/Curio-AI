"""
Real PostgreSQL Integration Tests for Auth API Endpoints (Phase 2, Task 4).

Verifies the complete HTTP authentication lifecycle against 'curio_test_db' via TestClient:
1. POST /api/v1/auth/register
2. POST /api/v1/auth/login
3. GET  /api/v1/auth/me (using Bearer JWT)
4. Verifies database consistency and strict absence of password/hash in all responses.
"""
import uuid
from fastapi.testclient import TestClient
import pytest

from backend.app.main import app

pytestmark = pytest.mark.db_integration


@pytest.fixture
def api_client(override_get_db):
    with TestClient(app) as client:
        yield client


def test_full_auth_lifecycle_integration(api_client):
    """
    End-to-end integration test:
    - Register user via POST /api/v1/auth/register
    - Login user via POST /api/v1/auth/login
    - Extract returned JWT
    - Call GET /api/v1/auth/me using the JWT
    - Verify identity matches and password/hash is never exposed
    """
    unique_id = uuid.uuid4().hex[:8]
    raw_email = f"Integrate_{unique_id}@Curio.AI"
    password = "SuperStrongPassword2026!"

    # 1. Register User
    reg_res = api_client.post(
        "/api/v1/auth/register",
        json={"email": raw_email, "password": password},
    )
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()

    assert "id" in reg_data
    user_id = reg_data["id"]
    assert reg_data["email"] == raw_email.lower()
    assert reg_data["is_active"] is True
    assert "password" not in reg_data
    assert "hashed_password" not in reg_data

    # 2. Login User
    login_res = api_client.post(
        "/api/v1/auth/login",
        json={"email": raw_email, "password": password},
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token_data = login_res.json()

    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] > 0
    token = token_data["access_token"]
    assert "password" not in token_data
    assert "hashed_password" not in token_data

    # 3. Access Protected /auth/me with Bearer JWT
    me_res = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200, f"/auth/me failed: {me_res.text}"
    me_data = me_res.json()

    assert me_data["id"] == user_id
    assert me_data["email"] == raw_email.lower()
    assert me_data["is_active"] is True
    assert "password" not in me_data
    assert "hashed_password" not in me_data

    # 4. Verify Case-Insensitive Login against same account
    login_mixed = api_client.post(
        "/api/v1/auth/login",
        json={"email": raw_email.upper(), "password": password},
    )
    assert login_mixed.status_code == 200
    token_mixed = login_mixed.json()["access_token"]

    me_res2 = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_mixed}"},
    )
    assert me_res2.status_code == 200
    assert me_res2.json()["id"] == user_id
