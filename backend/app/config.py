from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


_DEVELOPMENT_JWT_SECRET = "chronickel_development_jwt_secret_2026"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # The visible brand is configuration.  Runtime identifiers intentionally
    # stay generic so a future rename does not require a data migration.
    APP_NAME: str = "Chronickel"
    APP_PUBLIC_ORIGIN: str = "http://localhost:3000"
    DATABASE_URL: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    APP_JWT_SECRET: str = _DEVELOPMENT_JWT_SECRET
    VISION_PROXY_URL: str = "http://host.docker.internal:8100"
    PHOTO_DIR: str = "/app/photos"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    ALLOWED_GOOGLE_EMAILS: str = ""
    APP_DEVICE_KEY: str = ""
    ENVIRONMENT: str = "development"
    GOOGLE_REDIRECT_URI: str = ""
    GOOGLE_MAPS_API_KEY: str = ""


settings = Settings()


def validate_runtime_settings() -> None:
    """Reject development credentials before a production server can start."""
    if settings.ENVIRONMENT.casefold() != "production":
        return
    secret = settings.APP_JWT_SECRET.strip()
    if secret == _DEVELOPMENT_JWT_SECRET or len(secret) < 32:
        raise RuntimeError("APP_JWT_SECRET must be a unique value of at least 32 characters in production")


def allowed_google_emails() -> set[str]:
    return {email.strip().casefold() for email in settings.ALLOWED_GOOGLE_EMAILS.split(",") if email.strip()}


def google_redirect_uri() -> str:
    """Use the configured public origin unless an explicit URI is required."""
    return settings.GOOGLE_REDIRECT_URI.strip() or f"{settings.APP_PUBLIC_ORIGIN.rstrip('/')}/api/google/callback"
