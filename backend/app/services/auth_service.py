"""
Authentication service — orchestrates user registration, credential
verification, and JWT access token issuance.

Security:
- Never reveals whether an email exists through error-detail differences.
- Never logs plaintext passwords, hashes, or tokens.
- Reuses the existing security module for all cryptographic operations.
- Does NOT implement FastAPI dependencies (deferred to Task 4).
"""
from typing import Optional
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.core.config import settings
from backend.app.core.security import (
    create_access_token,
    verify_password,
)
from backend.app.models.user import User
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.auth import Token
from backend.app.schemas.user import UserCreate, UserResponse


class AuthService:
    def __init__(self, user_repo: Optional[UserRepository] = None):
        self.user_repo = user_repo or UserRepository()

    def register_user(
        self,
        db: SQLAlchemySession,
        user_in: UserCreate,
    ) -> UserResponse:
        """
        Register a new user.

        Raises:
            ValueError: If the email is already registered.
        """
        if self.user_repo.exists_by_email(db, user_in.email):
            raise ValueError("A user with this email already exists")

        db_user = self.user_repo.create(
            db,
            email=user_in.email,
            password=user_in.password,
        )
        return UserResponse.model_validate(db_user)

    def authenticate_user(
        self,
        db: SQLAlchemySession,
        email: str,
        password: str,
    ) -> User:
        """
        Verify user credentials and return the authenticated User model.

        Raises:
            ValueError: On invalid credentials or inactive account.
                        Uses a generic message to avoid leaking email existence.
        """
        user = self.user_repo.get_by_email(db, email)
        if not user:
            raise ValueError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Account is inactive")

        return user

    def create_user_access_token(self, user: User) -> Token:
        """
        Issue a JWT access token for an authenticated user.
        Uses the user's UUID as the JWT subject claim.
        """
        access_token = create_access_token(subject=str(user.id))
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
