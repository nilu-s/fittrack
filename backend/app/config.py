from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://fittrack:fittrack@localhost:5432/fittrack"
    FITTRACK_JWT_SECRET: str = "fittrack_jwt_secret_2026"
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    OLLAMA_VISION_MODEL: str = "kimi-k3:cloud"
    PHOTO_DIR: str = "/app/photos"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    ALLOWED_EMAIL: str = "luis@example.com"
    GOOGLE_REDIRECT_URI: str = "https://fittrack.49.12.225.84.sslip.io/api/google/callback"


settings = Settings()