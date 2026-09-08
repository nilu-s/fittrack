"""Proof-bound browser login handoff and revocable native account credentials."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from sqlalchemy import select

from app.database import async_session
from app.models import Account, NativeLogin, NativeSession, TravelWatch


def utcnow():
    return datetime.now(timezone.utc)


def proof_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")


def credential_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def resolve_native(request: Request):
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer crn_") or len(header) > 256:
        return None
    async with async_session() as session:
        device = await session.scalar(select(NativeSession).where(
            NativeSession.credential_hash == credential_hash(header[7:]),
            NativeSession.revoked.is_(False), NativeSession.expires_at > utcnow(),
        ))
        if device is None:
            return None
        account = await session.get(Account, device.account_id)
        if account is None:
            return None
        request.state.native_session_id = device.id
        return {"account_id": str(account.id), "sub": account.google_subject}


async def exchange_login(login_id: uuid.UUID, verifier: str):
    async with async_session() as session:
        login = await session.scalar(select(NativeLogin).where(NativeLogin.id == login_id).with_for_update())
        if not login or login.consumed or login.expires_at <= utcnow():
            raise HTTPException(401, "Login expired or already used")
        if not hmac.compare_digest(login.challenge, proof_challenge(verifier)):
            raise HTTPException(401, "Invalid login proof")
        if login.account_id is None:
            raise HTTPException(409, "Complete Google login in the browser")
        token = "crn_" + secrets.token_urlsafe(48)
        device = NativeSession(account_id=login.account_id, credential_hash=credential_hash(token),
            platform=login.platform, expires_at=utcnow() + timedelta(days=30))
        login.consumed = True
        session.add(device)
        await session.commit()
        return {"credential": token, "expires_at": device.expires_at, "device_id": device.id}


async def revoke_session(device_id, account_id):
    async with async_session() as session:
        device = await session.scalar(select(NativeSession).where(
            NativeSession.id == device_id, NativeSession.account_id == account_id).with_for_update())
        if device:
            device.revoked, device.push_token = True, None
            watches = (await session.scalars(select(TravelWatch).where(
                TravelWatch.device_id == device.id, TravelWatch.account_id == account_id).with_for_update())).all()
            for watch in watches:
                watch.active, watch.origin, watch.live_fix, watch.live_until = False, None, None, None
                watch.generation += 1
            await session.commit()
