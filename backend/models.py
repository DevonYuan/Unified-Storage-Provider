"""Database models for OmniDrive."""

from sqlalchemy import Column, String, DateTime, Integer, Enum as SQLEnum, Text, Boolean
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


class UploadRouting(Base):
    """Tracks which provider gets the next upload in the alternation cycle.

    Single-row table. The `next_provider` column stores which provider
    (GOOGLE_DRIVE or ONEDRIVE) should receive the next root-level or
    merged-folder upload. Flips after each successful upload.
    """

    __tablename__ = "upload_routing"

    id = Column(Integer, primary_key=True, default=1)
    next_provider = Column(SQLEnum(ProviderType), nullable=False, default=ProviderType.GOOGLE_DRIVE)

    def __repr__(self):
        return f"<UploadRouting(next_provider={self.next_provider})>"


class RepairLog(Base):
    """Log of failed propagation attempts on merged-folder operations.

    Records when a rename or delete succeeds on some providers but fails
    on others, so the user can manually reconcile later.
    """

    __tablename__ = "repair_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    operation_type = Column(String(50), nullable=False)  # "rename" or "delete"
    virtual_id = Column(String(500), nullable=False)
    provider = Column(SQLEnum(ProviderType), nullable=False)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<RepairLog(id={self.id}, op={self.operation_type}, provider={self.provider}, success={self.success})>"