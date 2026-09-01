"""Business rules for materializing account-private recurring todos."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Todo, TodoRoutine


async def materialize_routines_for_date(session: AsyncSession, account_id, target_date: date) -> None:
    """Create missing todo instances for matching enabled routines.

    Instance provenance is stored in ``external_id`` to make repeated reads
    idempotent without letting a browser choose an account or routine owner.
    """
    routines = (await session.execute(
        select(TodoRoutine).where(
            TodoRoutine.account_id == account_id,
            TodoRoutine.is_active.is_(True),
        )
    )).scalars().all()
    for routine in routines:
        if target_date.weekday() not in routine.weekdays:
            continue
        instance_key = f"routine:{routine.id}:{target_date.isoformat()}"
        exists = await session.scalar(select(Todo.id).where(
            Todo.account_id == account_id,
            Todo.source == "routine",
            Todo.external_id == instance_key,
        ))
        if exists is None:
            session.add(Todo(
                account_id=account_id,
                title=routine.title,
                due_date=target_date,
                due_time=routine.due_time,
                priority=routine.priority,
                source="routine",
                external_id=instance_key,
            ))
