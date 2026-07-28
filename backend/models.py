"""Database models for OmniDrive."""

from sqlalchemy import Column, String, DateTime, Integer, Enum as SQLEnum, Text
from sqlalchemy.dialects.sqlite import JSON
from datetime import datetime
import enum

from database_driver import Base


class ProviderType(str, enum.Enum):
    """Supported cloud storage providers."""
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"


class ConnectedAccount(Base):
    """Connected cloud storage account metadata."""

    __tablename__ = "connected_accounts"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(SQLEnum(ProviderType), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)  # User-facing account name
    keyring_key = Column(String(255), nullable=False, unique=True)  # Keyring reference key
    access_token = Column(Text, nullable=True)  # Current access token for API calls
    refresh_token = Column(Text, nullable=True)  # Refresh token for getting new access tokens
    token_expiry = Column(DateTime, nullable=True)  # Token expiration time
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ConnectedAccount(id={self.id}, provider={self.provider}, display_name='{self.display_name}')>"