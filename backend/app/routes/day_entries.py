from __future__ import annotations

import uuid
from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.database import async_session
from app.models import DayEntry
from app.routes.auth import get_current_user
from app.schemas import (
    DayEntryBulkRequest,
    DayEntryBulkResponse,
    DayEntryCreate,
    DayEntryResponse,
    DayEntryUpdate,
)

router = APIRouter(prefix="/day-entries", tags=["day-entries"])


def _to_response(entry: DayEntry) -> DayEntryResponse:
    return DayEntryResponse.model_validate(entry)


async def _get_or_create(session, user_id: str, day: date_type) -> DayEntry:
    result = await session.execute(
        select(DayEntry).where(DayEntry.user_id == user_id, DayEntry.date == day)
    )
    entry = result.scalars().first()
    if entry is None:
        entry = DayEntry(user_id=user_id, date=day)
        session.add(entry)
        await session.flush()
    return entry


@router.get("", response_model=Optional[DayEntryResponse])
async def get_day_entry(date: date_type = Query(...), user: str = Depends(get_current_user)):
    """Get a day entry by date — does NOT create one if missing (no side-effect on GET)."""
    async with async_session() as session:
        result = await session.execute(
            select(DayEntry).where(DayEntry.user_id == "luis", DayEntry.date == date)
        )
        entry = result.scalars().first()
        if entry is None:
            return None
        return _to_response(entry)


@router.put("", response_model=DayEntryResponse)
async def upsert_day_entry(body: DayEntryCreate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(
            select(DayEntry).where(DayEntry.user_id == "luis", DayEntry.date == body.date)
        )
        entry = result.scalars().first()
        if entry is None:
            entry = DayEntry(**body.model_dump())
            session.add(entry)
        else:
            for field, value in body.model_dump(exclude_unset=True).items():
                setattr(entry, field, value)
        await session.commit()
        await session.refresh(entry)
        return _to_response(entry)


@router.post("/bulk", response_model=DayEntryBulkResponse)
async def get_bulk_day_entries(body: DayEntryBulkRequest, user: str = Depends(get_current_user)):
    async with async_session() as session:
        entries: list[DayEntryResponse] = []
        for d in body.dates:
            entry = await _get_or_create(session, "luis", d)
            entries.append(_to_response(entry))
        await session.commit()
        return DayEntryBulkResponse(entries=entries)
