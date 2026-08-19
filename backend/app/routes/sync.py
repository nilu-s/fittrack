from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from app.database import async_session
from app.models import DayEntry, Meal, Todo, SyncLog
from app.schemas import SyncConflictItem, SyncRequest, SyncResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

USER_ID = "luis"

# Mapping entity_type → model
ENTITY_MODELS = {
    "day_entry": DayEntry,
    "meal": Meal,
    "todo": Todo,
}


@router.post("", response_model=SyncResponse)
async def sync_changes(body: SyncRequest):
    async with async_session() as session:
        conflicts: list[SyncConflictItem] = []
        applied: list[dict[str, Any]] = []

        for change in body.changes:
            model = ENTITY_MODELS.get(change.entity_type)
            if model is None:
                logger.warning("Unknown entity_type: %s", change.entity_type)
                continue

            # Look up existing record by entity_id
            result = await session.execute(select(model).where(model.id == change.entity_id))
            existing = result.scalars().first()

            if change.action == "delete":
                if existing is not None:
                    await session.delete(existing)
                applied.append({"entity_type": change.entity_type, "entity_id": str(change.entity_id), "action": "delete"})
                continue

            payload = change.payload or {}

            if existing is None:
                # Create new record
                obj = model(**payload, id=change.entity_id)
                session.add(obj)
                applied.append({"entity_type": change.entity_type, "entity_id": str(change.entity_id), "action": "create"})
            else:
                # Update — last-write-wins by client_timestamp vs updated_at
                server_updated = getattr(existing, "updated_at", None)
                if server_updated is not None and change.client_timestamp < server_updated:
                    # Conflict: server is newer
                    conflicts.append(SyncConflictItem(
                        entity_type=change.entity_type,
                        entity_id=change.entity_id,
                        client_payload=payload,
                        server_payload={c.name: getattr(existing, c.name) for c in existing.__table__.columns},
                        client_timestamp=change.client_timestamp,
                        server_timestamp=server_updated,
                    ))
                    # Still apply client change (last-write-wins policy for Phase 1)
                for field, value in payload.items():
                    if hasattr(existing, field) and field != "id":
                        setattr(existing, field, value)
                applied.append({"entity_type": change.entity_type, "entity_id": str(change.entity_id), "action": "update"})

            # Log to sync_log
            session.add(SyncLog(
                user_id=USER_ID,
                entity_type=change.entity_type,
                entity_id=change.entity_id,
                action=change.action,
                payload=payload,
                client_timestamp=change.client_timestamp,
                synced=True,
            ))

        await session.commit()

        # Gather server changes since last_sync
        server_changes: list[dict[str, Any]] = []
        if body.last_sync is not None:
            for entity_type, model in ENTITY_MODELS.items():
                if hasattr(model, "updated_at"):
                    result = await session.execute(
                        select(model).where(
                            model.user_id == USER_ID,
                            model.updated_at > body.last_sync,
                        )
                    )
                    for obj in result.scalars().all():
                        server_changes.append({
                            "entity_type": entity_type,
                            "entity_id": str(obj.id),
                            "payload": {c.name: getattr(obj, c.name) for c in obj.__table__.columns},
                        })

        sync_token = datetime.utcnow()
        return SyncResponse(
            server_changes=server_changes,
            conflicts=conflicts,
            sync_token=sync_token,
        )