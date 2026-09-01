from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.database import async_session
from app.models import TodoRoutine
from app.routes.auth import get_current_user
from app.schemas import TodoRoutineCreate, TodoRoutineResponse, TodoRoutineUpdate

router = APIRouter(prefix="/todo-routines", tags=["todo-routines"])


@router.get("", response_model=list[TodoRoutineResponse])
async def list_todo_routines(user: str = Depends(get_current_user)):
    async with async_session() as session:
        routines = (await session.execute(
            select(TodoRoutine).where(TodoRoutine.account_id == user).order_by(TodoRoutine.created_at)
        )).scalars().all()
        return [TodoRoutineResponse.model_validate(routine) for routine in routines]


@router.post("", response_model=TodoRoutineResponse, status_code=status.HTTP_201_CREATED)
async def create_todo_routine(body: TodoRoutineCreate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        routine = TodoRoutine(account_id=user, **body.model_dump())
        session.add(routine)
        await session.commit()
        await session.refresh(routine)
        return TodoRoutineResponse.model_validate(routine)


async def _owned_routine(session, routine_id: uuid.UUID, user: str) -> TodoRoutine:
    routine = await session.scalar(select(TodoRoutine).where(TodoRoutine.id == routine_id, TodoRoutine.account_id == user))
    if routine is None:
        raise HTTPException(status_code=404, detail="Todo routine not found")
    return routine


@router.put("/{routine_id}", response_model=TodoRoutineResponse)
async def update_todo_routine(routine_id: uuid.UUID, body: TodoRoutineUpdate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        routine = await _owned_routine(session, routine_id, user)
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(routine, field, value)
        await session.commit()
        await session.refresh(routine)
        return TodoRoutineResponse.model_validate(routine)


@router.delete("/{routine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo_routine(routine_id: uuid.UUID, user: str = Depends(get_current_user)):
    async with async_session() as session:
        routine = await _owned_routine(session, routine_id, user)
        await session.delete(routine)
        await session.commit()
