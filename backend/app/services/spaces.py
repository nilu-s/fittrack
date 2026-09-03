"""Authorization helpers for explicit shared workspaces."""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Space, SpaceMembership, SpaceProject


async def member_space(session: AsyncSession, space_id: uuid.UUID, account_id: uuid.UUID) -> Space:
    space = await session.scalar(select(Space).where(Space.id == space_id))
    membership = await session.scalar(select(SpaceMembership).where(
        SpaceMembership.space_id == space_id, SpaceMembership.account_id == account_id
    ))
    if space is None or membership is None:
        raise HTTPException(404, "Space not found")
    return space


async def owner_space(session: AsyncSession, space_id: uuid.UUID, account_id: uuid.UUID) -> Space:
    space = await member_space(session, space_id, account_id)
    if space.owner_account_id != account_id:
        raise HTTPException(403, "Only the space owner can manage members")
    return space


async def validate_project(session: AsyncSession, project_id: uuid.UUID | None, space_id: uuid.UUID | None) -> None:
    if project_id is None:
        return
    if space_id is None:
        raise HTTPException(422, "A project requires a space")
    project = await session.scalar(select(SpaceProject).where(
        SpaceProject.id == project_id, SpaceProject.space_id == space_id
    ))
    if project is None:
        raise HTTPException(422, "Project does not belong to this space")


async def validate_assignee(session: AsyncSession, assignee_id: uuid.UUID | None, space_id: uuid.UUID | None) -> None:
    if assignee_id is None:
        return
    if space_id is None:
        raise HTTPException(422, "An assignee requires a space")
    member = await session.scalar(select(SpaceMembership.id).where(
        SpaceMembership.space_id == space_id, SpaceMembership.account_id == assignee_id
    ))
    if member is None:
        raise HTTPException(422, "Assignee is not a member of this space")
