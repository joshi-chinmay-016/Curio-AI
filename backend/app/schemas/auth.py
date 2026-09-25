"""
Pydantic schemas for authentication requests and token responses.
"""
from pydantic import BaseModel, EmailStr


class UserLogin(BaseModel):
    """Schema for user login / credential submission."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT access token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
