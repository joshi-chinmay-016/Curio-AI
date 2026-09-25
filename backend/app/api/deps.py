"""
FastAPI authentication and authorization dependencies (Phase 2, Task 4).

Provides:
- oauth2_scheme: OAuth2 Bearer token extraction for Swagger / OpenAPI.
- get_current_user: Decodes access token, extracts UUID sub claim, and loads active User.
- get_current_active_user: Enforces that the authenticated user account is active.
"""
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session as SQLAlchemySession
import jwt

from backend.app.core.config import settings
from backend.app.core.security import decode_access_token
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

user_repo = UserRepository()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: SQLAlchemySession = Depends(get_db),
) -> User:
    """
    Extract and validate JWT Bearer token from request Authorization header,
    resolve the user UUID subject, and retrieve the persistent User record.

    Raises:
        HTTPException (401): On missing, expired, invalid tokens, non-UUID subjects,
                             or nonexistent user records. Always includes WWW-Authenticate header.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id = UUID(str(sub))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise credentials_exception

    user = user_repo.get_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensure the resolved authenticated user has an active account.

    Raises:
        HTTPException (400): If the user's account is marked inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user
