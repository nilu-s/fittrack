from __future__ import annotations

import uuid
from datetime import date as date_type, datetime

from app.tz import BERLIN_TZ
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, exists, or_, select

from app.database import async_session
from app.models import Account, SpaceMembership, Todo
from app.services.todo_routines import materialize_routines_for_date
from app.routes.auth import get_current_user
from app.schemas import TodoCreate, TodoResponse, TodoUpdate
from app.services.spaces import member_space, validate_assignee, validate_project

router = APIRouter(prefix="/todos", tags=["todos"])


async def _to_response(session, todo: Todo) -> TodoResponse:
    response = TodoResponse.model_validate(todo)
    response.assignee_id = todo.assignee_account_id
    if todo.assignee_account_id is not None:
        assignee = await session.scalar(select(Account).where(Account.id == todo.assignee_account_id))
        if assignee is not None:
            response.assignee_display_name = assignee.display_name or assignee.email
    return response


def _space_access(account_id: uuid.UUID):
    return exists(select(SpaceMembership.id).where(
        SpaceMembership.space_id == Todo.space_id,
        SpaceMembership.account_id == account_id,
    ))


async def _accessible_todo(session, todo_id: uuid.UUID, account_id: uuid.UUID) -> Todo:
    todo = await session.scalar(select(Todo).execution_options(include_all_accounts=True).where(
        Todo.id == todo_id,
        or_(
            and_(Todo.space_id.is_(None), Todo.account_id == account_id),
            and_(Todo.space_id.is_not(None), _space_access(account_id)),
        ),
    ))
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


def _validate_travel(todo: Todo) -> None:
    """A monitor only makes sense for a deterministic, confirmed appointment."""
    if todo.travel_monitoring_enabled and not (
        todo.place_id and todo.due_date and todo.start_time and todo.travel_mode
    ):
        raise HTTPException(
            status_code=422,
            detail="Travel monitoring requires an exact place, date, start time and travel mode",
        )


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
        stmt = select(Todo).execution_options(include_all_accounts=True).where(
            Todo.deleted == False,
            or_(
                and_(Todo.space_id.is_(None), Todo.account_id == user),
                and_(Todo.space_id.is_not(None), _space_access(user)),
            ),
        )
        if date is not None:
            stmt = stmt.where(Todo.due_date == date)
        if status is not None:
            stmt = stmt.where(Todo.status == status)
        if category is not None:
            stmt = stmt.where(Todo.category == category)
        stmt = stmt.order_by(Todo.sort_order, Todo.priority)
        result = await session.execute(stmt)
        todos = result.scalars().all()
        return [await _to_response(session, t) for t in todos]


@router.post("", response_model=TodoResponse, status_code=201)
async def create_todo(body: TodoCreate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        # Do not rely on the request-local ORM filter for ownership on writes:
        # workers and focused route tests may not install that context.
        data = body.model_dump()
        if data["space_id"] is not None:
            await member_space(session, data["space_id"], user)
            if data["source"] != "manual" or data["travel_monitoring_enabled"]:
                raise HTTPException(422, "Only manual todos without travel monitoring can be shared")
        await validate_project(session, data["project_id"], data["space_id"])
        data["assignee_account_id"] = data.pop("assignee_id")
        await validate_assignee(session, data["assignee_account_id"], data["space_id"])
        todo = Todo(account_id=user, **data)
        _validate_travel(todo)
        session.add(todo)
        await session.commit()
        await session.refresh(todo)
        return await _to_response(session, todo)


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: uuid.UUID, body: TodoUpdate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        todo = await _accessible_todo(session, todo_id, user)
        original_source = todo.source
        changes = body.model_dump(exclude_unset=True)
        if "assignee_id" in changes:
            changes["assignee_account_id"] = changes.pop("assignee_id")
        for field, value in changes.items():
            setattr(todo, field, value)
        if todo.space_id is not None:
            await member_space(session, todo.space_id, user)
            if todo.source != "manual" or original_source != "manual" or todo.travel_monitoring_enabled:
                raise HTTPException(422, "Only manual todos without travel monitoring can be shared")
        await validate_project(session, todo.project_id, todo.space_id)
        await validate_assignee(session, todo.assignee_account_id, todo.space_id)
        _validate_travel(todo)
        await session.commit()
        await session.refresh(todo)
        return await _to_response(session, todo)


@router.delete("/{todo_id}", status_code=204)
async def delete_todo(todo_id: uuid.UUID, user: str = Depends(get_current_user)):
    async with async_session() as session:
        todo = await _accessible_todo(session, todo_id, user)
        if todo.deleted:
            raise HTTPException(status_code=404, detail="Todo not found")
        todo.deleted = True
        await session.commit()


@router.post("/{todo_id}/done", response_model=TodoResponse)
async def mark_todo_done(todo_id: uuid.UUID, user: str = Depends(get_current_user)):
    async with async_session() as session:
        todo = await _accessible_todo(session, todo_id, user)
        # Toggle: if done -> open, if open -> done
        if todo.status == "done":
            todo.status = "open"
            todo.completed_at = None
        else:
            todo.status = "done"
            todo.completed_at = datetime.now(BERLIN_TZ)
        await session.commit()
        await session.refresh(todo)
        return await _to_response(session, todo)
