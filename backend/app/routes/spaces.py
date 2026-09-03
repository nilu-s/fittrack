"""Explicit membership-managed spaces for shared household work."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.database import async_session
from app.models import Account, Space, SpaceInvitation, SpaceMembership, SpaceProject
from app.routes.auth import get_current_user
from app.schemas import (
    SpaceCreate, SpaceInvitationResponse, SpaceInviteCreate, SpaceMemberResponse,
    SpaceProjectCreate, SpaceProjectResponse, SpaceProjectUpdate, SpaceResponse, SpaceUpdate,
)
from app.services.spaces import member_space, owner_space

router = APIRouter(prefix="/spaces", tags=["spaces"])
invitation_router = APIRouter(prefix="/space-invitations", tags=["spaces"])


async def _members(session, space_id: uuid.UUID) -> list[SpaceMemberResponse]:
    rows = (await session.execute(select(SpaceMembership, Account).join(
        Account, Account.id == SpaceMembership.account_id
    ).where(SpaceMembership.space_id == space_id).order_by(SpaceMembership.created_at))).all()
    return [SpaceMemberResponse(member_id=membership.account_id, display_name=account.display_name or account.email, role=membership.role)
            for membership, account in rows]


async def _space_response(session, space: Space, account_id: uuid.UUID) -> SpaceResponse:
    membership = await session.scalar(select(SpaceMembership).where(
        SpaceMembership.space_id == space.id, SpaceMembership.account_id == account_id
    ))
    return SpaceResponse(id=space.id, name=space.name, owner_id=space.owner_account_id,
                         role=membership.role, members=await _members(session, space.id))


@router.get("", response_model=list[SpaceResponse])
async def list_spaces(account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        spaces = (await session.execute(select(Space).join(SpaceMembership).where(
            SpaceMembership.account_id == account_id
        ).order_by(Space.created_at))).scalars().all()
        return [await _space_response(session, space, account_id) for space in spaces]


@router.post("", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED)
async def create_space(body: SpaceCreate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        space = Space(name=body.name.strip(), owner_account_id=account_id)
        session.add(space)
        await session.flush()
        session.add(SpaceMembership(space_id=space.id, account_id=account_id, role="owner"))
        await session.commit()
        return await _space_response(session, space, account_id)


@router.put("/{space_id}", response_model=SpaceResponse)
async def update_space(space_id: uuid.UUID, body: SpaceUpdate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        space = await owner_space(session, space_id, account_id)
        space.name = body.name.strip()
        await session.commit()
        return await _space_response(session, space, account_id)


@router.post("/{space_id}/invitations", status_code=status.HTTP_201_CREATED)
async def invite_member(space_id: uuid.UUID, body: SpaceInviteCreate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        await owner_space(session, space_id, account_id)
        invited = await session.scalar(select(Account).where(Account.email == body.email.strip()))
        # Do not disclose whether an email belongs to an approved account.
        if invited is None:
            return {"status": "created"}
        existing = await session.scalar(select(SpaceMembership.id).where(
            SpaceMembership.space_id == space_id, SpaceMembership.account_id == invited.id
        ))
        pending = await session.scalar(select(SpaceInvitation.id).where(
            SpaceInvitation.space_id == space_id, SpaceInvitation.invited_account_id == invited.id,
            SpaceInvitation.status == "pending"
        ))
        if existing is None and pending is None:
            session.add(SpaceInvitation(space_id=space_id, invited_account_id=invited.id, invited_by_account_id=account_id))
            await session.commit()
        return {"status": "created"}


@router.delete("/{space_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(space_id: uuid.UUID, member_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        space = await owner_space(session, space_id, account_id)
        if member_id == space.owner_account_id:
            raise HTTPException(422, "The space owner cannot be removed")
        membership = await session.scalar(select(SpaceMembership).where(
            SpaceMembership.space_id == space_id, SpaceMembership.account_id == member_id
        ))
        if membership is None:
            raise HTTPException(404, "Member not found")
        await session.delete(membership)
        await session.commit()


@router.get("/{space_id}/projects", response_model=list[SpaceProjectResponse])
async def list_projects(space_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        await member_space(session, space_id, account_id)
        return [SpaceProjectResponse.model_validate(project) for project in (await session.execute(
            select(SpaceProject).where(SpaceProject.space_id == space_id).order_by(SpaceProject.is_archived, SpaceProject.name)
        )).scalars().all()]


@router.post("/{space_id}/projects", response_model=SpaceProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(space_id: uuid.UUID, body: SpaceProjectCreate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        await member_space(session, space_id, account_id)
        project = SpaceProject(space_id=space_id, name=body.name.strip(), description=body.description, created_by_account_id=account_id)
        session.add(project); await session.commit(); await session.refresh(project)
        return SpaceProjectResponse.model_validate(project)


@router.put("/{space_id}/projects/{project_id}", response_model=SpaceProjectResponse)
async def update_project(space_id: uuid.UUID, project_id: uuid.UUID, body: SpaceProjectUpdate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        await member_space(session, space_id, account_id)
        project = await session.scalar(select(SpaceProject).where(SpaceProject.id == project_id, SpaceProject.space_id == space_id))
        if project is None:
            raise HTTPException(404, "Project not found")
        for key, value in body.model_dump(exclude_unset=True).items():
            setattr(project, key, value.strip() if key == "name" else value)
        await session.commit(); await session.refresh(project)
        return SpaceProjectResponse.model_validate(project)


@router.delete("/{space_id}/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(space_id: uuid.UUID, project_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        await member_space(session, space_id, account_id)
        project = await session.scalar(select(SpaceProject).where(SpaceProject.id == project_id, SpaceProject.space_id == space_id))
        if project is None:
            raise HTTPException(404, "Project not found")
        await session.delete(project); await session.commit()


@invitation_router.get("", response_model=list[SpaceInvitationResponse])
async def list_invitations(account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        rows = (await session.execute(select(SpaceInvitation, Space, Account).join(
            Space, Space.id == SpaceInvitation.space_id
        ).join(Account, Account.id == SpaceInvitation.invited_by_account_id).where(
            SpaceInvitation.invited_account_id == account_id, SpaceInvitation.status == "pending"
        ))).all()
        return [SpaceInvitationResponse(id=invite.id, space_id=space.id, space_name=space.name,
                 invited_by_display_name=inviter.display_name or inviter.email, status=invite.status)
                for invite, space, inviter in rows]


@invitation_router.post("/{invitation_id}/accept", response_model=SpaceResponse)
async def accept_invitation(invitation_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        invitation = await session.scalar(select(SpaceInvitation).where(
            SpaceInvitation.id == invitation_id, SpaceInvitation.invited_account_id == account_id,
            SpaceInvitation.status == "pending"
        ))
        if invitation is None:
            raise HTTPException(404, "Invitation not found")
        invitation.status = "accepted"; invitation.responded_at = datetime.now(timezone.utc)
        if await session.scalar(select(SpaceMembership.id).where(SpaceMembership.space_id == invitation.space_id, SpaceMembership.account_id == account_id)) is None:
            session.add(SpaceMembership(space_id=invitation.space_id, account_id=account_id, role="member"))
        await session.commit()
        space = await member_space(session, invitation.space_id, account_id)
        return await _space_response(session, space, account_id)


@invitation_router.post("/{invitation_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_invitation(invitation_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        invitation = await session.scalar(select(SpaceInvitation).where(
            SpaceInvitation.id == invitation_id, SpaceInvitation.invited_account_id == account_id,
            SpaceInvitation.status == "pending"
        ))
        if invitation is None:
            raise HTTPException(404, "Invitation not found")
        invitation.status = "declined"; invitation.responded_at = datetime.now(timezone.utc)
        await session.commit()
