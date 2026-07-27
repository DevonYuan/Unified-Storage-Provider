"""Configuration management for OmniDrive backend."""

import os
from functools import lru_cache
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class GoogleOAuthConfig(BaseModel):
    """Google OAuth configuration loaded from environment variables."""

    client_id: str = Field(..., description="Google OAuth Client ID")
    client_secret: str = Field(..., description="Google OAuth Client Secret")
    redirect_uri: str = Field(..., description="OAuth redirect URI")
    auth_uri: str = Field(
        default="https://accounts.google.com/o/oauth2/auth",
        description="Google authorization endpoint"
    )
    token_uri: str = Field(
        default="https://oauth2.googleapis.com/token",
        description="Google token endpoint"
    )
    scopes: List[str] = Field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        description="OAuth scopes for Google Drive access"
    )

    @classmethod
    def from_env(cls) -> "GoogleOAuthConfig":
        """Create config from environment variables."""
        return cls(
            client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", ""),
            auth_uri=os.getenv("GOOGLE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
            token_uri=os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
        )

    def validate(self) -> List[str]:
        """Validate required configuration fields."""
        errors = []
        if not self.client_id:
            errors.append("GOOGLE_CLIENT_ID is required")
        if not self.client_secret:
            errors.append("GOOGLE_CLIENT_SECRET is required")
        if not self.redirect_uri:
            errors.append("GOOGLE_REDIRECT_URI is required")
        return errors


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: str = Field(default="", description="Database URL")

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(url=os.getenv("DATABASE_URL", ""))


class AppConfig(BaseModel):
    """Application configuration."""

    name: str = "OmniDrive"
    version: str = "0.1.0"
    google_oauth: GoogleOAuthConfig = Field(default_factory=GoogleOAuthConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)


@lru_cache
def get_config() -> AppConfig:
    """Get cached application configuration."""
    google_oauth = GoogleOAuthConfig.from_env()
    errors = google_oauth.validate()
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")

    return AppConfig(
        google_oauth=google_oauth,
        database=DatabaseConfig.from_env(),
    )