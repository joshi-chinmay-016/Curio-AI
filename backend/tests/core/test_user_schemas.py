"""
Unit tests for User & Auth Pydantic Schemas (Phase 2, Task 3):
- UserCreate validation (valid data, invalid email, password < 8 characters).
- UserResponse serialization and safety (no hashed_password exposed).
- UserLogin and Token validation.
"""
from datetime import datetime, timezone
import uuid
import pytest
from pydantic import ValidationError

from backend.app.schemas.user import UserCreate, UserResponse
from backend.app.schemas.auth import UserLogin, Token


def test_user_create_valid():
    """Verify valid email and password pass UserCreate validation."""
    data = {"email": "learner@curio.ai", "password": "securepassword123"}
    user_in = UserCreate(**data)

    assert user_in.email == "learner@curio.ai"
    assert user_in.password == "securepassword123"


def test_user_create_invalid_email():
    """Verify invalid email syntax raises Pydantic ValidationError."""
    invalid_emails = [
        "not-an-email",
        "missing@domain",
        "@nodomain.com",
        "spaces in@email.com",
        "",
    ]
    for email in invalid_emails:
        with pytest.raises(ValidationError):
            UserCreate(email=email, password="validpassword123")


def test_user_create_password_too_short():
    """Verify password shorter than 8 characters raises ValidationError."""
    short_passwords = ["", "1", "1234567", "short"]
    for pw in short_passwords:
        with pytest.raises(ValidationError):
            UserCreate(email="learner@curio.ai", password=pw)


def test_user_create_password_minimum_8_chars_allowed():
    """Verify password of exactly 8 characters passes validation."""
    user_in = UserCreate(email="learner@curio.ai", password="12345678")
    assert len(user_in.password) == 8


def test_user_response_fields_and_no_password_exposed():
    """Verify UserResponse serializes expected fields and excludes any password attributes."""
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # Construct UserResponse from a dict that includes hashed_password or extra password fields
    response = UserResponse(
        id=user_id,
        email="learner@curio.ai",
        is_active=True,
        created_at=now,
    )

    dumped = response.model_dump()
    assert dumped["id"] == user_id
    assert dumped["email"] == "learner@curio.ai"
    assert dumped["is_active"] is True
    assert dumped["created_at"] == now

    # Ensure password or hash cannot be present in response schema model_fields
    assert "password" not in response.model_fields
    assert "hashed_password" not in response.model_fields
    assert "password" not in dumped
    assert "hashed_password" not in dumped


def test_user_response_from_orm_object():
    """Verify UserResponse can be created from an object/ORM attributes without leaking hashed_password."""
    class DummyUserORM:
        id = uuid.uuid4()
        email = "learner_orm@curio.ai"
        hashed_password = "$2b$12$eX4mpleH4shValu3NotToExpos3..."
        is_active = True
        created_at = datetime.now(timezone.utc)

    user_orm = DummyUserORM()
    response = UserResponse.model_validate(user_orm)

    assert response.id == user_orm.id
    assert response.email == user_orm.email
    assert response.is_active is True
    assert not hasattr(response, "hashed_password")
    
    dumped = response.model_dump()
    assert "hashed_password" not in dumped
    assert "password" not in dumped


def test_user_login_valid():
    """Verify UserLogin schema accepts valid credentials."""
    login = UserLogin(email="user@curio.ai", password="somepassword")
    assert login.email == "user@curio.ai"
    assert login.password == "somepassword"


def test_user_login_invalid_email():
    """Verify UserLogin rejects invalid email formatting."""
    with pytest.raises(ValidationError):
        UserLogin(email="invalid_email_format", password="somepassword")


def test_token_schema():
    """Verify Token schema fields and defaults."""
    token = Token(access_token="eyJhbGciOi...", token_type="bearer", expires_in=86400)
    assert token.access_token == "eyJhbGciOi..."
    assert token.token_type == "bearer"
    assert token.expires_in == 86400

    # Default token_type is "bearer"
    token_default = Token(access_token="abc", expires_in=3600)
    assert token_default.token_type == "bearer"
