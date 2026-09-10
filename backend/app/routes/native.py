from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select

from app.database import async_session
from app.models import NativeSession
from app.routes.auth import get_current_user
from app.services.native_auth import exchange_login, revoke_session, require_native_auth
from app.services.google_native_auth import start_login, exchange_google_login

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


class GoogleLoginStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class GoogleLoginStarted(BaseModel):
    login_id: uuid.UUID
    nonce: str
    client_id: str


class GoogleLoginExchange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login_id: uuid.UUID
    verifier: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$", repr=False)
    id_token: SecretStr = Field(min_length=1, max_length=16384)


@router.post("/google/start", response_model=GoogleLoginStarted,
             responses={503: {"description": "Google app login is not configured"}})
async def begin_google_login(body: GoogleLoginStart):
    return await start_login(body.challenge)


@router.post("/google/exchange", response_model=LoginCredential, responses={
    401: {"description": "Invalid, expired or already used identity proof"},
    403: {"description": "Google account is not allowed"},
    503: {"description": "Google app login unavailable"},
})
async def complete_google_login(body: GoogleLoginExchange):
    return await exchange_google_login(body.login_id, body.verifier, body.id_token.get_secret_value())


@router.post("/login", response_model=LoginStarted, responses={503: {"description": "Native login temporarily unavailable"}})
async def begin_login(body: LoginStart):
    require_native_auth()


@router.post("/exchange", response_model=LoginCredential, responses={503: {"description": "Native login temporarily unavailable"}})
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
