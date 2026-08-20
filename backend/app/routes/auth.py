from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from jose import jwt as jose_jwt
from sqlalchemy import delete, select

from app.config import settings
from app.database import async_session
from app.models import GoogleToken

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
# Separate router for /google/* paths (matching Google Console redirect URI)
google_router = APIRouter(prefix="/google", tags=["auth"])

# --- Google OAuth2 Configuration ---

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.sleep.read",
    "https://www.googleapis.com/auth/calendar.events.readonly",
]

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

import hashlib
import hmac

# Stateless HMAC-signed state (no in-memory storage needed — survives container restarts)
def _create_state() -> str:
    """Create a self-verifying state token: random nonce + HMAC signature."""
    nonce = secrets.token_urlsafe(16)
    sig = hmac.new(
        settings.FITTRACK_JWT_SECRET.encode(),
        nonce.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{nonce}.{sig}"

def _verify_state(state: str) -> bool:
    """Verify a state token's HMAC signature."""
    try:
        nonce, sig = state.split(".", 1)
        expected = hmac.new(
            settings.FITTRACK_JWT_SECRET.encode(),
            nonce.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


# --- JWT session helpers ---

SESSION_COOKIE_NAME = "fittrack_session"
SESSION_TTL_DAYS = 7


def _create_session_jwt(email: str) -> str:
    """Create a JWT session token for the given email."""
    now = datetime.now(timezone.utc)
    payload = {
        "email": email,
        "iat": now,
        "exp": now + timedelta(days=SESSION_TTL_DAYS),
    }
    return jose_jwt.encode(payload, settings.FITTRACK_JWT_SECRET, algorithm="HS256")


def _verify_session_jwt(token: str) -> str | None:
    """Verify a JWT session token and return the email, or None if invalid."""
    try:
        payload = jose_jwt.decode(token, settings.FITTRACK_JWT_SECRET, algorithms=["HS256"])
        return payload.get("email")
    except Exception:
        return None


async def get_current_user(request: Request) -> str:
    """FastAPI dependency: reads fittrack_session cookie, verifies JWT, returns email.

    Raises HTTPException(401) if not authenticated.
    Localhost/private network requests without cookie bypass auth (CLI/agent access).
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    # Auth bypass for CLI/agent: secret key header (not forwarded by Caddy from public)
    cli_key = os.environ.get("FITTRACK_CLI_KEY")
    if not token and cli_key and request.headers.get("X-FitTrack-CLI-Key") == cli_key:
        return "luis"
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = _verify_session_jwt(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return email


# --- Token refresh helpers ---


async def refresh_access_token(refresh_token: str) -> dict | None:
    """Refresh the Google access token using the refresh token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
    if resp.status_code == 200:
        return resp.json()
    logger.error(f"Token refresh failed: {resp.text}")
    return None


async def get_valid_access_token(session) -> str | None:
    """Get a valid access token for user_id='luis', refreshing if necessary.

    Returns the access_token string, or None if no token is stored / refresh fails.
    """
    result = await session.execute(
        select(GoogleToken).where(GoogleToken.user_id == "luis")
    )
    token_row = result.scalar_one_or_none()
    if not token_row or not token_row.refresh_token:
        return None

    now = datetime.now(timezone.utc)
    # Refresh if expired or within 5 minutes of expiry
    if token_row.expires_at and token_row.expires_at > now + timedelta(minutes=5):
        return token_row.access_token

    refreshed = await refresh_access_token(token_row.refresh_token)
    if not refreshed:
        return None

    new_access = refreshed.get("access_token")
    new_expires_in = refreshed.get("expires_in", 3600)
    token_row.access_token = new_access
    token_row.expires_at = datetime.now(timezone.utc) + timedelta(seconds=new_expires_in)
    await session.commit()
    return new_access


# --- Routes ---


@router.get("/google/login")
async def google_login(request: Request):
    """Redirect user to Google OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")

    # The redirect URI must match what's in Google Cloud Console
    redirect_uri = f"https://fittrack.49.12.225.84.sslip.io/api/google/callback"

    state = _create_state()

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@google_router.get("/callback")
async def google_callback(request: Request):
    """Handle OAuth callback — exchange code for tokens and persist to DB."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        return JSONResponse(
            status_code=400,
            content={"detail": f"OAuth error: {error}"},
        )

    if not code or not state:
        return JSONResponse(
            status_code=400,
            content={"detail": "Missing code or state parameter"},
        )

    # Verify state (HMAC-signed, stateless — survives container restarts)
    if not _verify_state(state):
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid state parameter"},
        )

    redirect_uri = f"https://fittrack.49.12.225.84.sslip.io/api/google/callback"

    # Exchange authorization code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=30,
        )

    logger.info(f"Token exchange response: status={token_resp.status_code}, body={token_resp.text[:500]}")

    if token_resp.status_code != 200:
        logger.error(f"Token exchange failed: status={token_resp.status_code}, body={token_resp.text[:500]}")
        # Redirect to login with error (instead of JSON, so browser doesn't get stuck)
        return RedirectResponse(url="/login?error=token_exchange_failed", status_code=302)

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    token_type = token_data.get("token_type", "Bearer")
    scope = token_data.get("scope", " ".join(SCOPES))

    if not access_token:
        return JSONResponse(
            status_code=400,
            content={"detail": "No access token in response"},
        )

    # Get user info
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )

    if userinfo_resp.status_code != 200:
        logger.error(f"UserInfo fetch failed: {userinfo_resp.text}")
        return JSONResponse(
            status_code=400,
            content={"detail": "Failed to get user info"},
        )

    user_info = userinfo_resp.json()
    email = user_info.get("email", "")

    # Check allowed email
    if settings.ALLOWED_EMAIL and email and settings.ALLOWED_EMAIL != email:
        return JSONResponse(
            status_code=403,
            content={"detail": f"Email {email} not allowed"},
        )

    # Persist tokens to DB (upsert for user_id='luis')
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    async with async_session() as session:
        result = await session.execute(
            select(GoogleToken).where(GoogleToken.user_id == "luis")
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.email = email
            existing.access_token = access_token
            if refresh_token:
                existing.refresh_token = refresh_token
            existing.token_type = token_type
            existing.expires_at = expires_at
            existing.scope = scope
        else:
            new_token = GoogleToken(
                user_id="luis",
                email=email,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type=token_type,
                expires_at=expires_at,
                scope=scope,
            )
            session.add(new_token)

        await session.commit()

    logger.info(f"Google OAuth success for {email} — tokens persisted to DB")

    # Create JWT session token and set as httpOnly cookie, then redirect to /
    session_jwt = _create_session_jwt(email)
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_jwt,
        max_age=SESSION_TTL_DAYS * 86400,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@router.get("/me")
async def auth_me(request: Request):
    """Return current auth status based on JWT session cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return {"authenticated": False, "email": None}
    email = _verify_session_jwt(token)
    if not email:
        return {"authenticated": False, "email": None}
    return {"authenticated": True, "email": email}


@router.get("/google/status")
async def google_status():
    """Check if Google is connected (valid token in DB)."""
    async with async_session() as session:
        result = await session.execute(
            select(GoogleToken).where(GoogleToken.user_id == "luis")
        )
        token_row = result.scalar_one_or_none()

    connected = token_row is not None and bool(token_row.access_token)
    return {
        "connected": connected,
        "has_credentials": bool(settings.GOOGLE_CLIENT_ID),
        "email": token_row.email if token_row else None,
    }


@router.post("/logout")
async def logout(request: Request):
    """Logout — clear session cookie only (keep Google tokens for re-login)."""
    response = JSONResponse(content={"detail": "Logged out"})
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@router.post("/google/disconnect")
async def google_disconnect(request: Request):
    """Disconnect Google — delete Google tokens from DB, but keep session cookie."""
    async with async_session() as session:
        await session.execute(
            delete(GoogleToken).where(GoogleToken.user_id == "luis")
        )
        await session.commit()
    return {"detail": "Google disconnected"}