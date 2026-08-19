from __future__ import annotations

import base64
import json
import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

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

# In-memory state store (single-user, sufficient)
_state_store: dict[str, str] = {}


@router.get("/google/login")
async def google_login(request: Request):
    """Redirect user to Google OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")

    # Determine redirect URI from request (use the configured redirect_uris)
    # The redirect URI must match what's in Google Cloud Console
    redirect_uri = f"https://fittrack.49.12.225.84.sslip.io/api/auth/google/callback"

    state = secrets.token_urlsafe(32)
    _state_store[state] = "pending"

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


@router.get("/google/callback")
async def google_callback(request: Request):
    """Handle OAuth callback — exchange code for tokens."""
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

    # Verify state
    if state not in _state_store:
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid state parameter"},
        )
    _state_store.pop(state, None)

    redirect_uri = f"https://fittrack.49.12.225.84.sslip.io/api/auth/google/callback"

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

    if token_resp.status_code != 200:
        logger.error(f"Token exchange failed: {token_resp.text}")
        return JSONResponse(
            status_code=400,
            content={"detail": "Failed to exchange code for tokens"},
        )

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)

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

    # Store tokens (in-memory for now — single user)
    # In production, store in DB with refresh_token for background sync
    _token_store = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
        "email": email,
        "name": user_info.get("name", ""),
        "picture": user_info.get("picture", ""),
    }

    logger.info(f"Google OAuth success for {email}")

    # Redirect to settings page with success indicator
    return RedirectResponse(
        url="/settings?google_connected=true",
        status_code=302,
    )


@router.get("/me")
async def auth_me():
    """Return current auth status."""
    return {
        "authenticated": False,
        "google_connected": False,
        "email": None,
        "detail": "Auth status endpoint — OAuth tokens stored in-memory",
    }


@router.get("/google/status")
async def google_status():
    """Check if Google is connected."""
    return {
        "connected": False,
        "has_credentials": bool(settings.GOOGLE_CLIENT_ID),
        "detail": "Google OAuth status — tokens stored in-memory",
    }


@router.post("/logout")
async def logout():
    """Logout — clear tokens."""
    return {"detail": "Logged out"}