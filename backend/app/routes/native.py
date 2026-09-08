from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import NativeLogin, NativeSession
from app.routes.auth import get_current_user
from app.services.native_auth import exchange_login, revoke_session, utcnow

router = APIRouter(prefix="/native", tags=["native"])


class LoginStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    platform: Literal["ios", "android"]


class LoginStarted(BaseModel):
    login_id: uuid.UUID
    login_url: str


class LoginExchange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login_id: uuid.UUID
    verifier: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$")


class LoginCredential(BaseModel):
    credential: str
    expires_at: datetime
    device_id: uuid.UUID


class PushRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str | None = Field(default=None, max_length=4096)


@router.post("/login", response_model=LoginStarted)
async def begin_login(body: LoginStart):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google login is not configured")
    async with async_session() as session:
        login = NativeLogin(challenge=body.challenge, platform=body.platform, expires_at=utcnow() + timedelta(minutes=5))
        session.add(login)
        await session.commit()
        return {"login_id": login.id, "login_url": settings.APP_PUBLIC_ORIGIN.rstrip("/") + "/api/auth/google/login?" + urlencode({"native_request": str(login.id)})}


@router.post("/exchange", response_model=LoginCredential)
async def exchange(body: LoginExchange):
    return await exchange_login(body.login_id, body.verifier)


@router.put("/push", status_code=204)
async def register_push(body: PushRegistration, request: Request, user=Depends(get_current_user)):
    device_id = getattr(request.state, "native_session_id", None)
    async with async_session() as session:
        device = await session.scalar(select(NativeSession).where(NativeSession.id == device_id, NativeSession.account_id == user))
        if not device:
            raise HTTPException(403, "A native session is required")
        # A registration token can migrate after an account switch. Remove the
        # old association globally without disclosing any other account.
        if body.token:
            from sqlalchemy import update
            await session.execute(update(NativeSession).execution_options(include_all_accounts=True).where(
                NativeSession.push_token == body.token, NativeSession.id != device.id).values(push_token=None))
        device.push_token = body.token
        await session.commit()


@router.post("/logout", status_code=204)
async def logout(request: Request, user=Depends(get_current_user)):
    await revoke_session(getattr(request.state, "native_session_id", None), user)
