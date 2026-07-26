"""Application settings loaded from environment variables.

Real config surface for Phase 1:
- DATABASE_URL: Async PostgreSQL connection string (Supabase).
- JWT_SECRET / JWT_ALGORITHM / ACCESS_TOKEN_EXPIRE_MINUTES: token config.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()  # type: ignore[call-arg]
