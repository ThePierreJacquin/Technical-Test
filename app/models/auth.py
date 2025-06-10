"""Pydantic models for login-related API requests and responses."""

from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    """Login request model"""

    email: EmailStr
    password: str
    save_credentials: bool = False


class LoginResponse(BaseModel):
    """Login response model"""

    success: bool
    message: str
    session_id: str
    email: Optional[str] = None
