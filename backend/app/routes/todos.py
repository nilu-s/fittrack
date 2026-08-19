from __future__ import annotations

import uuid
from datetime import date as date_type, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.database import async_session
from app.models import Todo
from app.schemas import TodoCreate, TodoResponse, TodoUpdate

router = APIRouter(prefix="/todos", tags=["todos"])


def _to_response(todo: Todo) -> TodoResponse:
    return TodoResponse.model_validate(todo)


@router.get("", response_model=list[TodoResponse])
async def list_todos(
    date: Optional[date_type] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    async with async_session() as session:
        stmt = select(Todo).where(Todo.user_id == "luis")
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
async def create_todo(body: TodoCreate):
    async with async_session() as session:
        todo = Todo(**body.model_dump())
        session.add(todo)
        await session.commit()
        await session.refresh(todo)
        return _to_response(todo)


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: uuid.UUID, body: TodoUpdate):
    async with async_session() as session:
        result = await session.execute(select(Todo).where(Todo.id == todo_id))
        todo = result.scalars().first()
        if todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(todo, field, value)
        await session.commit()
        await session.refresh(todo)
        return _to_response(todo)


@router.delete("/{todo_id}", status_code=204)
async def delete_todo(todo_id: uuid.UUID):
    async with async_session() as session:
        result = await session.execute(select(Todo).where(Todo.id == todo_id))
        todo = result.scalars().first()
        if todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        await session.delete(todo)
        await session.commit()


@router.post("/{todo_id}/done", response_model=TodoResponse)
async def mark_todo_done(todo_id: uuid.UUID):
    async with async_session() as session:
        result = await session.execute(select(Todo).where(Todo.id == todo_id))
        todo = result.scalars().first()
        if todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        todo.status = "done"
        todo.completed_at = datetime.utcnow()
        await session.commit()
        await session.refresh(todo)
        return _to_response(todo)