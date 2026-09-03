"""Private, consent-based contacts with no resource-sharing semantics."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.database import async_session
from app.models import Account, Contact, ContactInvitation
from app.routes.auth import get_current_user
from app.schemas import (
    ContactInviteCreate, ContactInvitationResponse, ContactOutgoingInvitationResponse,
    ContactResponse, ContactSearchResult,
)

router = APIRouter(prefix="/contacts", tags=["contacts"])
invitation_router = APIRouter(prefix="/contact-invitations", tags=["contacts"])


@router.get("", response_model=list[ContactResponse])
async def list_contacts(account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        rows = (await session.execute(select(Contact, Account).join(Account, Account.id == Contact.contact_account_id).where(Contact.owner_account_id == account_id).order_by(Account.display_name, Account.email))).all()
        return [ContactResponse(id=contact.id, display_name=account.display_name or "Kontakt", alias=account.alias or "") for contact, account in rows]


@router.get("/search", response_model=list[ContactSearchResult])
async def search_contacts(query: str = Query(min_length=2, max_length=33), account_id: uuid.UUID = Depends(get_current_user)):
    """Find public account handles without ever returning an email or account ID."""
    prefix = query.strip().removeprefix("@").casefold()
    if len(prefix) < 2 or not prefix.replace(".", "").replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=422, detail="Invalid alias search")
    async with async_session() as session:
        rows = (await session.execute(
            select(Account).where(Account.alias.startswith(prefix), Account.id != account_id).order_by(Account.alias).limit(10)
        )).scalars().all()
        return [ContactSearchResult(alias=item.alias, display_name=item.display_name or "Cronicl-Mitglied") for item in rows]


@router.post("/invitations", status_code=status.HTTP_201_CREATED)
async def invite_contact(body: ContactInviteCreate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        invited = await session.scalar(select(Account).where(Account.alias == body.alias))
        if invited is None or invited.id == account_id:
            return {"status": "created"}
        exists = await session.scalar(select(Contact.id).where(Contact.owner_account_id == account_id, Contact.contact_account_id == invited.id))
        pending = await session.scalar(select(ContactInvitation.id).where(ContactInvitation.invited_account_id == invited.id, ContactInvitation.invited_by_account_id == account_id, ContactInvitation.status == "pending"))
        if exists is None and pending is None:
            session.add(ContactInvitation(invited_account_id=invited.id, invited_by_account_id=account_id))
            await session.commit()
        return {"status": "created"}


@router.delete("/entries/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_contact(contact_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        contact = await session.scalar(select(Contact).where(Contact.id == contact_id, Contact.owner_account_id == account_id))
        if contact is None: raise HTTPException(404, "Contact not found")
        await session.delete(contact)
        reciprocal = await session.scalar(select(Contact).where(Contact.owner_account_id == contact.contact_account_id, Contact.contact_account_id == account_id))
        if reciprocal is not None: await session.delete(reciprocal)
        await session.commit()


@invitation_router.get("", response_model=list[ContactInvitationResponse])
async def list_invitations(account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        rows = (await session.execute(select(ContactInvitation, Account).join(Account, Account.id == ContactInvitation.invited_by_account_id).where(ContactInvitation.invited_account_id == account_id, ContactInvitation.status == "pending"))).all()
        return [ContactInvitationResponse(id=item.id, invited_by_display_name=account.display_name or "Cronicl-Mitglied", invited_by_alias=account.alias or "") for item, account in rows]


@router.get("/outgoing-invitations", response_model=list[ContactOutgoingInvitationResponse])
async def list_outgoing_invitations(account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        rows = (await session.execute(select(ContactInvitation, Account).join(Account, Account.id == ContactInvitation.invited_account_id).where(ContactInvitation.invited_by_account_id == account_id, ContactInvitation.status == "pending"))).all()
        return [ContactOutgoingInvitationResponse(id=item.id, invited_display_name=account.display_name or "Cronicl-Mitglied", invited_alias=account.alias or "") for item, account in rows]


@invitation_router.post("/{invitation_id}/accept", status_code=status.HTTP_204_NO_CONTENT)
async def accept_invitation(invitation_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        item = await session.scalar(select(ContactInvitation).where(ContactInvitation.id == invitation_id, ContactInvitation.invited_account_id == account_id, ContactInvitation.status == "pending"))
        if item is None: raise HTTPException(404, "Invitation not found")
        item.status = "accepted"; item.responded_at = datetime.now(timezone.utc)
        for owner, contact in ((account_id, item.invited_by_account_id), (item.invited_by_account_id, account_id)):
            if await session.scalar(select(Contact.id).where(Contact.owner_account_id == owner, Contact.contact_account_id == contact)) is None: session.add(Contact(owner_account_id=owner, contact_account_id=contact))
        await session.commit()


@invitation_router.post("/{invitation_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_invitation(invitation_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        item = await session.scalar(select(ContactInvitation).where(ContactInvitation.id == invitation_id, ContactInvitation.invited_account_id == account_id, ContactInvitation.status == "pending"))
        if item is None: raise HTTPException(404, "Invitation not found")
        item.status = "declined"; item.responded_at = datetime.now(timezone.utc); await session.commit()
