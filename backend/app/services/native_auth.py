"""Revocable v2 native credentials; the retired browser handoff always rejects."""
from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from sqlalchemy import select

from app.database import async_session
from app.models import Account, NativeSession, TravelWatch


def require_native_auth() -> None:
    raise HTTPException(503, "Native login temporarily unavailable", headers={"Cache-Control": "no-store"})


def utcnow():
    return datetime.now(timezone.utc)


def proof_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")


def credential_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def resolve_native(request: Request):
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer crn2_") or len(header) > 256:
        return None
    async with async_session() as session:
        device = await session.scalar(select(NativeSession).where(
            NativeSession.credential_hash == credential_hash(header[7:]),
            NativeSession.revoked.is_(False), NativeSession.expires_at > utcnow(),
            NativeSession.protocol_version == 2, NativeSession.platform == "android",
        ))
        if device is None:
            return None
        account = await session.get(Account, device.account_id)
        if account is None:
            return None
        request.state.native_session_id = device.id
        return {"account_id": str(account.id), "sub": account.google_subject}


async def exchange_login(login_id: uuid.UUID, verifier: str):
    require_native_auth()


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
