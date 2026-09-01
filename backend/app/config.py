from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


_DEVELOPMENT_JWT_SECRET = "fittrack_jwt_secret_2026"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://fittrack:fittrack@localhost:5432/fittrack"
    FITTRACK_JWT_SECRET: str = _DEVELOPMENT_JWT_SECRET
    VISION_PROXY_URL: str = "http://host.docker.internal:8100"
    PHOTO_DIR: str = "/app/photos"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    ALLOWED_GOOGLE_EMAILS: str = ""
    LEGACY_OWNER_EMAIL: str = ""
    FITTRACK_DEVICE_KEY: str = ""
    ENVIRONMENT: str = "development"
    GOOGLE_REDIRECT_URI: str = "https://fittrack.49.12.225.84.sslip.io/api/google/callback"


settings = Settings()


def validate_runtime_settings() -> None:
    """Reject development credentials before a production server can start."""
    if settings.ENVIRONMENT.casefold() != "production":
        return
    secret = settings.FITTRACK_JWT_SECRET.strip()
    if secret == _DEVELOPMENT_JWT_SECRET or len(secret) < 32:
        raise RuntimeError("FITTRACK_JWT_SECRET must be a unique value of at least 32 characters in production")


def allowed_google_emails() -> set[str]:
    return {email.strip().casefold() for email in settings.ALLOWED_GOOGLE_EMAILS.split(",") if email.strip()}
