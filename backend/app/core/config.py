from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./test.db"

    # Security
    JWT_SECRET: str = "test-secret-key-for-testing-only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Email (Brevo)
    BREVO_API_KEY: str = "test-api-key"
    BREVO_SENDER_EMAIL: Optional[str] = "noreply@omnidrive.com"
    BREVO_SENDER_NAME: Optional[str] = "OmniDrive"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Try to find .env file in backend directory or parent directories
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(env_path):
    settings = Settings(_env_file=env_path)
else:
    settings = Settings()
