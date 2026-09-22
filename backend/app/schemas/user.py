"""
Pydantic schemas for User creation and response.

Security: UserResponse intentionally excludes hashed_password.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration requests."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")


class UserResponse(BaseModel):
    """Safe user representation — never exposes hashed_password."""
    id: UUID
    email: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
