from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/login")
async def google_login():
    return JSONResponse(status_code=501, content={"detail": "Not implemented — auth disabled in Phase 1"})


@router.get("/google/callback")
async def google_callback():
    return JSONResponse(status_code=501, content={"detail": "Not implemented — auth disabled in Phase 1"})


@router.get("/me")
async def auth_me():
    return JSONResponse(status_code=501, content={"detail": "Not implemented — auth disabled in Phase 1"})


@router.post("/logout")
async def logout():
    return JSONResponse(status_code=501, content={"detail": "Not implemented — auth disabled in Phase 1"})