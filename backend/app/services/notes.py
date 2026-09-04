"""Business rules for changing the visibility of private-first notes."""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Note, Todo


async def withdraw_note_to_private(session: AsyncSession, note: Note, account_id: uuid.UUID, confirmed: bool) -> None:
    """Return a shared note to its creator and keep an open derived task private."""
    if note.space_id is None:
        return
    if note.account_id != account_id:
        raise HTTPException(403, "Only the note creator can move it back to private")
    if not confirmed:
        raise HTTPException(422, "Confirm before moving a note back to private")

    note.space_id = None
    todo = await session.scalar(select(Todo).execution_options(include_all_accounts=True).where(
        Todo.origin_note_id == note.id,
        Todo.deleted == False,  # noqa: E712 - SQLAlchemy SQL predicate
        Todo.status != "done",
    ))
    if todo is not None:
        todo.space_id = None
