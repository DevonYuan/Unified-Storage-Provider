"""Configuration management for OmniDrive backend."""

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env — resolve path differently for PyInstaller vs source runs
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller one-file exe — .env lives next to the exe
    _env_path = Path(sys.executable).parent / ".env"
else:
    # Running from source — .env is one level above backend/
    _env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)


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


class MicrosoftOAuthConfig(BaseModel):
    """Microsoft Azure AD OAuth configuration loaded from environment variables."""

    client_id: str = Field(..., description="Azure AD Application (client) ID")
    client_secret: str = Field(..., description="Azure AD Client Secret")
    redirect_uri: str = Field(..., description="OAuth redirect URI")
    auth_uri: str = Field(
        default="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        description="Microsoft authorization endpoint"
    )
    token_uri: str = Field(
        default="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        description="Microsoft token endpoint"
    )
    scopes: List[str] = Field(
        default_factory=lambda: [
            "offline_access",
            "Files.Read",
            "Files.ReadWrite",
            "User.Read",
        ],
        description="OAuth scopes for Microsoft Graph / OneDrive access"
    )

    @classmethod
    def from_env(cls) -> "MicrosoftOAuthConfig":
        """Create config from environment variables."""
        return cls(
            client_id=os.getenv("MICROSOFT_CLIENT_ID", ""),
            client_secret=os.getenv("MICROSOFT_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("MICROSOFT_REDIRECT_URI", ""),
            auth_uri=os.getenv("MICROSOFT_AUTH_URI", "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"),
            token_uri=os.getenv("MICROSOFT_TOKEN_URI", "https://login.microsoftonline.com/common/oauth2/v2.0/token"),
        )

    def validate(self) -> List[str]:
        """Validate required configuration fields."""
        errors = []
        if not self.client_id:
            errors.append("MICROSOFT_CLIENT_ID is required")
        if not self.client_secret:
            errors.append("MICROSOFT_CLIENT_SECRET is required")
        if not self.redirect_uri:
            errors.append("MICROSOFT_REDIRECT_URI is required")
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
    microsoft_oauth: MicrosoftOAuthConfig = Field(default_factory=MicrosoftOAuthConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)


@lru_cache
def get_config() -> AppConfig:
    """Get cached application configuration."""
    google_oauth = GoogleOAuthConfig.from_env()
    google_errors = google_oauth.validate()

    microsoft_oauth = MicrosoftOAuthConfig.from_env()
    ms_errors = microsoft_oauth.validate()

    all_errors = google_errors + ms_errors
    if all_errors:
        raise ValueError(f"Configuration errors: {', '.join(all_errors)}")

    return AppConfig(
        google_oauth=google_oauth,
        microsoft_oauth=microsoft_oauth,
        database=DatabaseConfig.from_env(),
    )