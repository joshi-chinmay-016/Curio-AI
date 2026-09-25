"""
Real PostgreSQL Integration Tests for UserRepository and AuthService (Phase 2, Task 3).

Target: 'curio_test_db' via test_db_session fixture (savepoints with rollback).
"""
import uuid
import pytest

from backend.app.core.security import verify_password, decode_access_token
from backend.app.models.user import User
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.user import UserCreate
from backend.app.services.auth_service import AuthService


pytestmark = pytest.mark.db_integration


def test_user_repository_create_and_lookup_by_email(test_db_session):
    """Verify creating a user via UserRepository persists in DB and can be retrieved by normalized email."""
    repo = UserRepository()
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"Learner_{unique_suffix}@Curio.AI"
    plain_password = "Password123!"

    created_user = repo.create(test_db_session, email=email, password=plain_password)

    assert created_user.id is not None
    assert created_user.email == f"learner_{unique_suffix}@curio.ai"
    assert created_user.is_active is True
    assert created_user.created_at is not None
    # Password must be hashed with bcrypt, never stored as plaintext
    assert created_user.hashed_password != plain_password
    assert created_user.hashed_password.startswith("$2b$") or created_user.hashed_password.startswith("$2a$")
    assert verify_password(plain_password, created_user.hashed_password) is True

    # Lookup by lowercase email
    by_lower = repo.get_by_email(test_db_session, f"learner_{unique_suffix}@curio.ai")
    assert by_lower is not None
    assert by_lower.id == created_user.id

    # Lookup by mixed-case email
    by_mixed = repo.get_by_email(test_db_session, f"LEARNER_{unique_suffix}@CURIO.AI")
    assert by_mixed is not None
    assert by_mixed.id == created_user.id


def test_user_repository_get_by_id(test_db_session):
    """Verify UserRepository.get_by_id retrieves correct user."""
    repo = UserRepository()
    email = f"id_test_{uuid.uuid4().hex[:8]}@curio.ai"
    user = repo.create(test_db_session, email=email, password="ValidPassword123!")

    retrieved = repo.get_by_id(test_db_session, user.id)
    assert retrieved is not None
    assert retrieved.id == user.id
    assert retrieved.email == email

    # Non-existent ID returns None
    assert repo.get_by_id(test_db_session, uuid.uuid4()) is None


def test_user_repository_exists_by_email(test_db_session):
    """Verify UserRepository.exists_by_email reports true for existing and false for non-existing."""
    repo = UserRepository()
    email = f"exists_{uuid.uuid4().hex[:8]}@curio.ai"

    assert repo.exists_by_email(test_db_session, email) is False

    repo.create(test_db_session, email=email, password="ValidPassword123!")

    assert repo.exists_by_email(test_db_session, email) is True
    assert repo.exists_by_email(test_db_session, email.upper()) is True


def test_user_repository_duplicate_email_rejected(test_db_session):
    """Verify attempting to create a user with an existing email raises ValueError."""
    repo = UserRepository()
    email = f"dup_{uuid.uuid4().hex[:8]}@curio.ai"
    repo.create(test_db_session, email=email, password="FirstPassword123!")

    with pytest.raises(ValueError, match="already exists"):
        repo.create(test_db_session, email=email.upper(), password="SecondPassword123!")


def test_auth_service_end_to_end_registration_and_login(test_db_session):
    """Verify full AuthService workflow: register, authenticate, and issue JWT using PostgreSQL."""
    auth_service = AuthService()
    email = f"full_flow_{uuid.uuid4().hex[:8]}@curio.ai"
    password = "SuperSecurePassword123!"

    # 1. Registration
    user_in = UserCreate(email=email, password=password)
    response = auth_service.register_user(test_db_session, user_in)

    assert response.email == email
    assert response.is_active is True
    assert not hasattr(response, "hashed_password")

    # 2. Duplicate registration rejected
    with pytest.raises(ValueError, match="already exists"):
        auth_service.register_user(test_db_session, user_in)

    # 3. Successful authentication
    authenticated = auth_service.authenticate_user(test_db_session, email=email, password=password)
    assert authenticated.id == response.id

    # 4. Authentication with wrong password
    with pytest.raises(ValueError, match="Invalid email or password"):
        auth_service.authenticate_user(test_db_session, email=email, password="IncorrectPassword!")

    # 5. Authentication with unknown email
    with pytest.raises(ValueError, match="Invalid email or password"):
        auth_service.authenticate_user(test_db_session, email="nobody@curio.ai", password=password)

    # 6. Issue access token
    token = auth_service.create_user_access_token(authenticated)
    assert token.token_type == "bearer"
    assert token.expires_in > 0

    payload = decode_access_token(token.access_token)
    assert payload["sub"] == str(response.id)


def test_auth_service_inactive_user_rejected(test_db_session):
    """Verify inactive user in database cannot authenticate."""
    repo = UserRepository()
    auth_service = AuthService(user_repo=repo)
    email = f"inactive_{uuid.uuid4().hex[:8]}@curio.ai"
    password = "ValidPassword123!"

    user = repo.create(test_db_session, email=email, password=password)
    user.is_active = False
    test_db_session.commit()

    with pytest.raises(ValueError, match="Account is inactive"):
        auth_service.authenticate_user(test_db_session, email=email, password=password)
