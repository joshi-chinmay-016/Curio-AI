"""
Unit tests for AuthService (Phase 2, Task 3):
- User registration (success, duplicate rejection).
- User authentication (success, wrong password, unknown email, inactive account).
- Token creation (claims, user UUID subject, expiration).
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest

import backend.app.db.base  # noqa: F401 - Register all SQLAlchemy models in mapper registry
from backend.app.core.security import get_password_hash, decode_access_token
from backend.app.models.user import User
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.user import UserCreate
from backend.app.services.auth_service import AuthService


@pytest.fixture
def mock_repo():
    return MagicMock(spec=UserRepository)


@pytest.fixture
def auth_service(mock_repo):
    return AuthService(user_repo=mock_repo)


@pytest.fixture
def mock_db():
    return MagicMock()


def test_register_user_success(auth_service, mock_repo, mock_db):
    """Verify successful user registration returns UserResponse without exposing password hash."""
    user_in = UserCreate(email="newuser@curio.ai", password="validpassword123")
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Repository returns False for existence check
    mock_repo.exists_by_email.return_value = False

    created_user = User(
        id=user_id,
        email="newuser@curio.ai",
        hashed_password="$2b$12$somehashedpasswordstringhere...",
        is_active=True,
        created_at=now,
    )
    mock_repo.create.return_value = created_user

    response = auth_service.register_user(mock_db, user_in)

    mock_repo.exists_by_email.assert_called_once_with(mock_db, "newuser@curio.ai")
    mock_repo.create.assert_called_once_with(
        mock_db,
        email="newuser@curio.ai",
        password="validpassword123",
    )
    assert response.id == user_id
    assert response.email == "newuser@curio.ai"
    assert response.is_active is True
    assert not hasattr(response, "hashed_password")


def test_register_user_duplicate_email_rejected(auth_service, mock_repo, mock_db):
    """Verify duplicate email registration raises ValueError without calling create."""
    user_in = UserCreate(email="existing@curio.ai", password="validpassword123")
    mock_repo.exists_by_email.return_value = True

    with pytest.raises(ValueError, match="already exists"):
        auth_service.register_user(mock_db, user_in)

    mock_repo.create.assert_not_called()


def test_authenticate_user_success(auth_service, mock_repo, mock_db):
    """Verify successful authentication with matching password returns the User object."""
    plain_password = "CorrectPassword123!"
    hashed = get_password_hash(plain_password)
    user = User(
        id=uuid.uuid4(),
        email="learner@curio.ai",
        hashed_password=hashed,
        is_active=True,
    )
    mock_repo.get_by_email.return_value = user

    authenticated_user = auth_service.authenticate_user(
        mock_db,
        email="learner@curio.ai",
        password=plain_password,
    )

    assert authenticated_user.id == user.id
    assert authenticated_user.email == user.email


def test_authenticate_user_wrong_password_rejected(auth_service, mock_repo, mock_db):
    """Verify incorrect password raises generic ValueError without leaking email presence."""
    correct_password = "CorrectPassword123!"
    hashed = get_password_hash(correct_password)
    user = User(
        id=uuid.uuid4(),
        email="learner@curio.ai",
        hashed_password=hashed,
        is_active=True,
    )
    mock_repo.get_by_email.return_value = user

    with pytest.raises(ValueError, match="Invalid email or password"):
        auth_service.authenticate_user(
            mock_db,
            email="learner@curio.ai",
            password="WrongPassword999!",
        )


def test_authenticate_user_unknown_email_rejected(auth_service, mock_repo, mock_db):
    """Verify unknown email raises identical generic ValueError."""
    mock_repo.get_by_email.return_value = None

    with pytest.raises(ValueError, match="Invalid email or password"):
        auth_service.authenticate_user(
            mock_db,
            email="unknown@curio.ai",
            password="any_password",
        )


def test_authenticate_user_inactive_account_rejected(auth_service, mock_repo, mock_db):
    """Verify inactive user account is rejected even with correct credentials."""
    password = "CorrectPassword123!"
    hashed = get_password_hash(password)
    inactive_user = User(
        id=uuid.uuid4(),
        email="inactive@curio.ai",
        hashed_password=hashed,
        is_active=False,
    )
    mock_repo.get_by_email.return_value = inactive_user

    with pytest.raises(ValueError, match="Account is inactive"):
        auth_service.authenticate_user(
            mock_db,
            email="inactive@curio.ai",
            password=password,
        )


def test_create_user_access_token_subject_and_type(auth_service):
    """Verify JWT access token uses user UUID as subject claim and returns Token schema."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="token_user@curio.ai",
        hashed_password="hash",
        is_active=True,
    )

    token_response = auth_service.create_user_access_token(user)

    assert token_response.token_type == "bearer"
    assert token_response.expires_in > 0
    assert isinstance(token_response.access_token, str)

    # Decode token and verify subject claim matches user UUID string
    payload = decode_access_token(token_response.access_token)
    assert payload["sub"] == str(user_id)
