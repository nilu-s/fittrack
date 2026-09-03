"""Private-first notes and their deliberate conversion into scheduled todos."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, exists, or_, select

from app.database import async_session
from app.models import Note, SpaceMembership, Todo
from app.routes.auth import get_current_user
from app.schemas import NoteCreate, NoteMove, NotePlan, NoteResponse, NoteUpdate
from app.services.spaces import member_space

router = APIRouter(prefix="/notes", tags=["notes"])


def _space_access(account_id: uuid.UUID):
    return exists(select(SpaceMembership.id).where(
        SpaceMembership.space_id == Note.space_id,
        SpaceMembership.account_id == account_id,
    ))


async def _accessible_note(session, note_id: uuid.UUID, account_id: uuid.UUID) -> Note:
    note = await session.scalar(select(Note).execution_options(include_all_accounts=True).where(
        Note.id == note_id,
        or_(
            and_(Note.space_id.is_(None), Note.account_id == account_id),
            and_(Note.space_id.is_not(None), _space_access(account_id)),
        ),
    ))
    if note is None:
        raise HTTPException(404, "Note not found")
    return note


async def _response(session, note: Note) -> NoteResponse:
    scheduled_todo_id = await session.scalar(select(Todo.id).where(
        Todo.origin_note_id == note.id,
        Todo.deleted == False,  # noqa: E712 - SQLAlchemy SQL predicate
    ))
    return NoteResponse(
        id=note.id, title=note.title, body=note.body, space_id=note.space_id,
        status="planned" if scheduled_todo_id else "active", sort_order=note.sort_order,
        scheduled_todo_id=scheduled_todo_id, created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.get("", response_model=list[NoteResponse])
async def list_notes(account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        notes = (await session.execute(select(Note).execution_options(include_all_accounts=True).where(
            or_(
                and_(Note.space_id.is_(None), Note.account_id == account_id),
                and_(Note.space_id.is_not(None), _space_access(account_id)),
            ),
        ).order_by(Note.space_id.nullsfirst(), Note.sort_order, Note.created_at))).scalars().all()
        return [await _response(session, note) for note in notes]


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(body: NoteCreate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        note = Note(account_id=account_id, title=body.title.strip(), body=body.body.strip() if body.body else None)
        session.add(note)
        await session.commit(); await session.refresh(note)
        return await _response(session, note)


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(note_id: uuid.UUID, body: NoteUpdate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        note = await _accessible_note(session, note_id, account_id)
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(note, field, value.strip() if field in {"title", "body"} and value else value)
        await session.commit(); await session.refresh(note)
        return await _response(session, note)


@router.post("/{note_id}/move", response_model=NoteResponse)
async def move_note(note_id: uuid.UUID, body: NoteMove, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        note = await _accessible_note(session, note_id, account_id)
        await member_space(session, body.space_id, account_id)
        if note.space_id != body.space_id and not body.confirm_share:
            raise HTTPException(422, "Confirm sharing before moving a note into another area")
        note.space_id = body.space_id
        await session.commit(); await session.refresh(note)
        return await _response(session, note)


@router.post("/{note_id}/plan", response_model=NoteResponse)
async def plan_note(note_id: uuid.UUID, body: NotePlan, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        note = await _accessible_note(session, note_id, account_id)
        if note.space_id is not None:
            await member_space(session, note.space_id, account_id)
        todo = await session.scalar(select(Todo).execution_options(include_all_accounts=True).where(
            Todo.origin_note_id == note.id,
        ))
        if todo is not None and todo.status == "done":
            raise HTTPException(422, "Completed todos cannot be rescheduled from their note")
        if todo is None:
            todo = Todo(account_id=note.account_id, title=note.title, status="open", priority=2,
                        due_date=body.due_date, start_time=body.start_time,
                        due_time=body.start_time, is_all_day=body.start_time is None,
                        source="manual", space_id=note.space_id, origin_note_id=note.id)
            session.add(todo)
        else:
            todo.title = note.title
            todo.deleted = False
            todo.status = "open"
            todo.completed_at = None
            todo.due_date = body.due_date
            todo.start_time = body.start_time
            todo.due_time = body.start_time
            todo.is_all_day = body.start_time is None
        note.status = "planned"
        await session.commit(); await session.refresh(note)
        return await _response(session, note)


@router.post("/{note_id}/unschedule", response_model=NoteResponse)
async def unschedule_note(note_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        note = await _accessible_note(session, note_id, account_id)
        todo = await session.scalar(select(Todo).execution_options(include_all_accounts=True).where(
            Todo.origin_note_id == note.id, Todo.deleted == False,  # noqa: E712
        ))
        if todo is not None:
            if todo.status == "done":
                raise HTTPException(422, "Completed todos cannot be moved back to the board")
            todo.deleted = True
        note.status = "active"
        await session.commit(); await session.refresh(note)
        return await _response(session, note)
