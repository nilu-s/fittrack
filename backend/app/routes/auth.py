from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import jwt as jose_jwt
from sqlalchemy import delete, select

from app.config import allowed_google_emails, settings
from app.database import async_session
from app.models import Account, AccountWeightRange, GoogleToken
from app.services.ownership import reset_current_account, set_current_account

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


def _create_session_jwt(account: Account) -> str:
    """Create a session bound to an internal account and immutable Google subject."""
    now = datetime.now(timezone.utc)
    payload = {
        "account_id": str(account.id),
        "sub": account.google_subject,
        "iat": now,
        "exp": now + timedelta(days=SESSION_TTL_DAYS),
    }
    return jose_jwt.encode(payload, settings.FITTRACK_JWT_SECRET, algorithm="HS256")


def _verify_session_jwt(token: str) -> dict | None:
    try:
        payload = jose_jwt.decode(token, settings.FITTRACK_JWT_SECRET, algorithms=["HS256"])
        return payload if payload.get("account_id") and payload.get("sub") else None
    except Exception:
        return None


async def get_current_user(request: Request):
    """Yield the account derived from a verified browser session; never a device."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    claims = _verify_session_jwt(token)
    if not claims:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    import uuid
    try:
        account_id = uuid.UUID(claims["account_id"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid session account")
    async with async_session() as session:
        account = await session.get(Account, account_id)
    if account is None or account.google_subject != claims["sub"]:
        raise HTTPException(status_code=401, detail="Invalid session account")
    scope = set_current_account(account_id)
    try:
        yield account_id
    finally:
        reset_current_account(scope)


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
    logger.error("Token refresh failed: status=%s", resp.status_code)
    return None


async def get_valid_access_token(session, account_id) -> str | None:
    """Get a valid access token for a session-derived account.

    Returns the access_token string, or None if no token is stored / refresh fails.
    """
    result = await session.execute(
        select(GoogleToken).where(GoogleToken.account_id == account_id)
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
    redirect_uri = settings.GOOGLE_REDIRECT_URI

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

    redirect_uri = settings.GOOGLE_REDIRECT_URI

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
        logger.error("Token exchange failed: status=%s", token_resp.status_code)
        # Redirect to login with error (instead of JSON, so browser doesn't get stuck)
        return RedirectResponse(url="/login?error=token_exchange_failed", status_code=302)

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    token_type = token_data.get("token_type", "Bearer")
    oauth_scope = token_data.get("scope", " ".join(SCOPES))

    if not access_token:
        return JSONResponse(
            status_code=400,
            content={"detail": "No access token in response"},
        )

    raw_id_token = token_data.get("id_token")
    if not raw_id_token:
        return JSONResponse(status_code=400, content={"detail": "Missing Google ID token"})
    try:
        identity = google_id_token.verify_oauth2_token(
            raw_id_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        logger.warning("Google ID token validation failed")
        return JSONResponse(status_code=401, content={"detail": "Invalid Google identity"})
    google_subject = identity.get("sub")
    email = str(identity.get("email", "")).casefold()
    if not google_subject or not email:
        return JSONResponse(status_code=400, content={"detail": "Incomplete Google identity"})
    allow_list = allowed_google_emails()
    if not allow_list and settings.ENVIRONMENT.casefold() == "production":
        raise HTTPException(status_code=500, detail="Google allow-list not configured")
    if email not in allow_list:
        return JSONResponse(
            status_code=403,
            content={"detail": "Google account is not allowed"},
        )

    # Upsert immutable Google identity, then persist tokens only for that account.
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    async with async_session() as session:
        account = (await session.execute(select(Account).where(Account.google_subject == google_subject))).scalar_one_or_none()
        if account is None:
            account = Account(google_subject=google_subject, email=email, display_name=identity.get("name"))
            session.add(account)
            await session.flush()
        else:
            account.email = email
            account.display_name = identity.get("name") or account.display_name
        range_row = (await session.execute(select(AccountWeightRange).where(AccountWeightRange.account_id == account.id))).scalar_one_or_none()
        if range_row is None:
            is_legacy_owner = email == settings.LEGACY_OWNER_EMAIL.casefold()
            range_row = AccountWeightRange(
                account_id=account.id,
                baseline_kg=117.5 if is_legacy_owner else 65.0,
                lower_offset_kg=-27.5 if is_legacy_owner else -20.0,
                upper_offset_kg=27.5 if is_legacy_owner else 20.0,
            )
            session.add(range_row)
        result = await session.execute(select(GoogleToken).where(GoogleToken.account_id == account.id))
        existing = result.scalar_one_or_none()

        if existing:
            existing.email = email
            existing.access_token = access_token
            if refresh_token:
                existing.refresh_token = refresh_token
            existing.token_type = token_type
            existing.expires_at = expires_at
            existing.scope = oauth_scope
        else:
            new_token = GoogleToken(
                account_id=account.id,
                email=email,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type=token_type,
                expires_at=expires_at,
                scope=oauth_scope,
            )
            session.add(new_token)

        await session.commit()

    # Create JWT session token and set as httpOnly cookie, then redirect to /
    session_jwt = _create_session_jwt(account)
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
    claims = _verify_session_jwt(token)
    if not claims:
        return {"authenticated": False, "email": None}
    import uuid
    async with async_session() as session:
        account = await session.get(Account, uuid.UUID(claims["account_id"]))
    if not account or account.google_subject != claims["sub"]:
        return {"authenticated": False, "email": None}
    return {"authenticated": True, "id": str(account.id), "email": account.email, "display_name": account.display_name}


@router.get("/google/status")
async def google_status(user=Depends(get_current_user)):
    """Check if Google is connected (valid token in DB)."""
    async with async_session() as session:
        result = await session.execute(
            select(GoogleToken).where(GoogleToken.account_id == user)
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


@router.post("/initialize")
async def initialize_account(user=Depends(get_current_user)):
    """Idempotently create this account's own optional starter data.

    Initialization is an explicit account action, never an application-startup
    side effect and never a copy of another account's records.
    """
    from app.seed import seed_default_data

    async with async_session() as session:
        await seed_default_data(session, user)
    return {"initialized": True}


@router.post("/google/disconnect")
async def google_disconnect(request: Request, user=Depends(get_current_user)):
    """Disconnect Google — delete Google tokens from DB, but keep session cookie."""
    async with async_session() as session:
        await session.execute(
            delete(GoogleToken).where(GoogleToken.account_id == user)
        )
        await session.commit()
    return {"detail": "Google disconnected"}
