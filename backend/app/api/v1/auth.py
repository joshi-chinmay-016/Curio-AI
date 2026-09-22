"""
Authentication API endpoints (Phase 2, Task 4):
- POST /api/v1/auth/register: User registration.
- POST /api/v1/auth/login: User credential authentication and JWT issuance.
- GET  /api/v1/auth/me: Retrieve profile of currently authenticated user.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.api.deps import get_current_active_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import Token, UserLogin
from backend.app.schemas.user import UserCreate, UserResponse
from backend.app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    user_in: UserCreate,
    db: SQLAlchemySession = Depends(get_db),
) -> UserResponse:
    """
    Register a new user account with email and password.
    Enforces minimum 8-character password and valid RFC email format.
    Excludes hashed_password from response.
    """
    try:
        return auth_service.register_user(db, user_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Authenticate credentials and obtain JWT access token",
)
def login(
    user_in: UserLogin,
    db: SQLAlchemySession = Depends(get_db),
) -> Token:
    """
    Authenticate user credentials (email + password) and issue a JWT access token.
    Returns 401 Unauthorized with WWW-Authenticate header on invalid credentials.
    """
    try:
        user = auth_service.authenticate_user(
            db, email=user_in.email, password=user_in.password
        )
    except ValueError as e:
        if "inactive" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_service.create_user_access_token(user)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current authenticated user profile",
)
def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    Retrieve profile information for the currently authenticated user.
    Requires Bearer JWT token in Authorization header.
    """
    return UserResponse.model_validate(current_user)
