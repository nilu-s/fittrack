from __future__ import annotations

import uuid
from datetime import date as date_type, datetime

from app.tz import BERLIN_TZ
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.database import async_session
from app.models import Todo
from app.services.todo_routines import materialize_routines_for_date
from app.routes.auth import get_current_user
from app.schemas import TodoCreate, TodoResponse, TodoUpdate

router = APIRouter(prefix="/todos", tags=["todos"])


def _to_response(todo: Todo) -> TodoResponse:
    return TodoResponse.model_validate(todo)


@router.get("", response_model=list[TodoResponse])
async def list_todos(
    date: Optional[date_type] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    user: str = Depends(get_current_user),
):
    async with async_session() as session:
        if date is not None:
            await materialize_routines_for_date(session, user, date)
            await session.commit()
        stmt = select(Todo).where(Todo.account_id == user, Todo.deleted == False)
        if date is not None:
            stmt = stmt.where(Todo.due_date == date)
        if status is not None:
            stmt = stmt.where(Todo.status == status)
        if category is not None:
            stmt = stmt.where(Todo.category == category)
        stmt = stmt.order_by(Todo.sort_order, Todo.priority)
        result = await session.execute(stmt)
        todos = result.scalars().all()
        return [_to_response(t) for t in todos]


@router.post("", response_model=TodoResponse, status_code=201)
async def create_todo(body: TodoCreate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        # Do not rely on the request-local ORM filter for ownership on writes:
        # workers and focused route tests may not install that context.
        todo = Todo(account_id=user, **body.model_dump())
        session.add(todo)
        await session.commit()
        await session.refresh(todo)
        return _to_response(todo)


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: uuid.UUID, body: TodoUpdate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(
            select(Todo).where(Todo.id == todo_id, Todo.account_id == user)
        )
        todo = result.scalars().first()
        if todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(todo, field, value)
        await session.commit()
        await session.refresh(todo)
        return _to_response(todo)


@router.delete("/{todo_id}", status_code=204)
async def delete_todo(todo_id: uuid.UUID, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(
            select(Todo).where(
                Todo.id == todo_id, Todo.account_id == user, Todo.deleted == False
            )
        )
        todo = result.scalars().first()
        if todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        todo.deleted = True
        await session.commit()


@router.post("/{todo_id}/done", response_model=TodoResponse)
async def mark_todo_done(todo_id: uuid.UUID, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(
            select(Todo).where(Todo.id == todo_id, Todo.account_id == user)
        )
        todo = result.scalars().first()
        if todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        # Toggle: if done -> open, if open -> done
        if todo.status == "done":
            todo.status = "open"
            todo.completed_at = None
        else:
            todo.status = "done"
            todo.completed_at = datetime.now(BERLIN_TZ)
        await session.commit()
        await session.refresh(todo)
        return _to_response(todo)
