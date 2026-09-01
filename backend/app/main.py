from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import validate_runtime_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Schema changes run exclusively through Alembic; accounts seed explicitly."""
    validate_runtime_settings()
    yield


app = FastAPI(title="FitTrack API", version="1.0.0", lifespan=lifespan)

# CORS — restrict to known origins
_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://fittrack.49.12.225.84.sslip.io",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# --- Register routers ---
from app.routes.auth import router as auth_router, google_router as auth_google_router
from app.routes.day_entries import router as day_entries_router
from app.routes.stats import router as stats_router
from app.routes.google_calendar import router as google_calendar_router
from app.routes.google_fit import router as google_fit_router
from app.routes.scale_v2 import browser_router as scale_browser_router, device_router as scale_v2_router, profile_router
from app.routes.sync import router as sync_router
from app.routes.todos import router as todos_router
from app.routes.training import router as training_router
from app.routes.goals import router as goals_router
from app.routes.configurable_meals import router as configurable_meals_router


# Device ingestion and OAuth are deliberately outside the browser-session
# boundary. Every other API route obtains its owner exclusively from the
# signed session before any route handler or ORM query can run.
from app.routes.auth import (
    SESSION_COOKIE_NAME,
    _verify_session_jwt,
)
from app.services.ownership import reset_current_account, set_current_account
import uuid

_PUBLIC_API_PATHS = {
    "/api/health",
    "/api/auth/me",
    "/api/auth/google/login",
    "/api/auth/logout",
    "/api/google/callback",
}


@app.middleware("http")
async def require_browser_account(request: Request, call_next):
    """Establish request-local account scope for every browser API request."""
    path = request.url.path
    if not path.startswith("/api/") or path in _PUBLIC_API_PATHS or path == "/api/scale-sync/v2":
        return await call_next(request)
    token = request.cookies.get(SESSION_COOKIE_NAME)
    claims = _verify_session_jwt(token) if token else None
    if not claims:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    try:
        account_id = uuid.UUID(claims["account_id"])
    except (KeyError, TypeError, ValueError):
        return JSONResponse(status_code=401, content={"detail": "Invalid session account"})
    scope = set_current_account(account_id)
    try:
        return await call_next(request)
    finally:
        reset_current_account(scope)

app.include_router(auth_router, prefix="/api")
app.include_router(auth_google_router, prefix="/api")
app.include_router(day_entries_router, prefix="/api")
app.include_router(todos_router, prefix="/api")
app.include_router(training_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(goals_router, prefix="/api")
app.include_router(configurable_meals_router, prefix="/api")
app.include_router(google_fit_router, prefix="/api")
app.include_router(scale_v2_router, prefix="/api")
app.include_router(scale_browser_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(google_calendar_router, prefix="/api")
