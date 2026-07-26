"""Pydantic schemas for the auth surface."""

from datetime import datetime
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
