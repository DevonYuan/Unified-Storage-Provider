from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.session import Base


class GoogleOAuthToken(Base):
    __tablename__ = "google_oauth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    access_token = Column(String(500), nullable=False)
    refresh_token = Column(String(500), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")


class GoogleFile(Base):
    __tablename__ = "google_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(String(255), nullable=False, index=True)  # Google's file ID
    name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=True)  # in bytes, None for folders
    parent_id = Column(String(255), nullable=True, index=True)  # Parent folder ID
    modified_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")

    # Unique constraint for user + file_id to prevent duplicates
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )