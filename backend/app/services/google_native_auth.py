"""Credential Manager identity proof -> one-time, account-private native session."""
from __future__ import annotations

import hmac
import secrets
import uuid
from datetime import timedelta

from fastapi import HTTPException
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from starlette.concurrency import run_in_threadpool

from app.config import allowed_google_emails, settings
from app.database import async_session
from app.models import Account, AccountWeightRange, NativeLogin, NativeSession
from app.services.native_auth import credential_hash, proof_challenge, utcnow


def client_id() -> str:
    configured = settings.GOOGLE_NATIVE_CLIENT_ID.strip()
    if not configured:
        raise HTTPException(503, "Google app login is not configured")
    return configured


class BoundedGoogleRequest(google_requests.Request):
    def __call__(self, *args, **kwargs):
        kwargs["timeout"] = 10
        return super().__call__(*args, **kwargs)


def verify_identity(token: str, audience: str) -> dict:
    try:
        identity = id_token.verify_oauth2_token(token, BoundedGoogleRequest(), audience)
    except ValueError:
        raise HTTPException(401, "Invalid Google identity") from None
    except GoogleAuthError:
        raise HTTPException(503, "Google identity verification unavailable") from None
    # Explicit checks also guard unexpected provider/library responses.
    if (identity.get("iss") not in ("accounts.google.com", "https://accounts.google.com")
            or identity.get("aud") != audience
            or not isinstance(identity.get("exp"), (int, float))
            or identity["exp"] <= utcnow().timestamp()
            or not isinstance(identity.get("sub"), str) or not identity["sub"]
            or identity.get("email_verified") is not True
            or not isinstance(identity.get("email"), str)):
        raise HTTPException(401, "Invalid Google identity")
    if identity["email"].casefold() not in allowed_google_emails():
        raise HTTPException(403, "Google account is not allowed")
    return identity


async def start_login(challenge: str) -> dict:
    audience = client_id()
    nonce = secrets.token_urlsafe(32)
    async with async_session() as session:
        login = NativeLogin(challenge=challenge, nonce_hash=credential_hash(nonce),
                            protocol_version=2, platform="android", expires_at=utcnow() + timedelta(minutes=5))
        session.add(login)
        await session.commit()
        return {"login_id": login.id, "nonce": nonce, "client_id": audience}


def validate_request(login, verifier: str) -> None:
    if (not login or login.protocol_version != 2 or login.platform != "android"
            or login.consumed or login.expires_at <= utcnow() or not login.nonce_hash
            or not hmac.compare_digest(login.challenge, proof_challenge(verifier))):
        raise HTTPException(401, "Invalid or expired login request")


async def exchange_google_login(login_id: uuid.UUID, verifier: str, token: str) -> dict:
    audience = client_id()
    # Reject bogus/expired proofs before certificate fetch; don't hold a DB lock over network IO.
    async with async_session() as session:
        login = await session.get(NativeLogin, login_id)
        validate_request(login, verifier)
    identity = await run_in_threadpool(verify_identity, token, audience)
    async with async_session() as session:
        login = await session.scalar(select(NativeLogin).where(NativeLogin.id == login_id).with_for_update())
        validate_request(login, verifier)
        nonce = identity.get("nonce")
        if not isinstance(nonce, str) or not hmac.compare_digest(login.nonce_hash, credential_hash(nonce)):
            raise HTTPException(401, "Invalid Google login nonce")
        # Concurrent first logins for the same subject converge on a single account.
        await session.execute(insert(Account).values(id=uuid.uuid4(), google_subject=identity["sub"],
            email=identity["email"].casefold(), display_name=identity.get("name"))
            .on_conflict_do_nothing(index_elements=[Account.google_subject]))
        account = await session.scalar(select(Account).where(Account.google_subject == identity["sub"]).with_for_update())
        account.email = identity["email"].casefold()
        if isinstance(identity.get("name"), str):
            account.display_name = identity["name"]
        own_range = await session.scalar(select(AccountWeightRange).where(AccountWeightRange.account_id == account.id))
        if own_range is None:
            session.add(AccountWeightRange(account_id=account.id, baseline_kg=65.0,
                                           lower_offset_kg=-20.0, upper_offset_kg=20.0, is_active=False))
        credential = "crn2_" + secrets.token_urlsafe(48)
        device = NativeSession(account_id=account.id, credential_hash=credential_hash(credential),
            protocol_version=2, platform="android", expires_at=utcnow() + timedelta(days=30))
        session.add(device)
        login.consumed, login.account_id = True, account.id
        await session.commit()
        return {"credential": credential, "expires_at": device.expires_at, "device_id": device.id}
