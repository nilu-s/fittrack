from __future__ import annotations

import logging
from datetime import datetime

from app.tz import BERLIN_TZ
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import inspect, select

from app.database import async_session
from app.models import DayEntry, Exercise, Meal, MealTemplate, Todo, TrainingSet, SyncLog
from app.routes.auth import get_current_user
from app.schemas import SyncConflictItem, SyncRequest, SyncResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

# Mapping entity_type → model
ENTITY_MODELS = {
    "day_entry": DayEntry,
    "meal": Meal,
    "todo": Todo,
    "training_set": TrainingSet,
    "exercise": Exercise,
    "meal_template": MealTemplate,
}


async def _validate_owned_references(session, model, payload: dict[str, Any], account_id: str) -> None:
    """Validate IDs that are logically foreign keys but lack DB constraints."""
    if model is Meal and payload.get("dish_id") is not None:
        from app.models import Dish

        dish = await session.scalar(
            select(Dish).where(Dish.id == payload["dish_id"], Dish.account_id == account_id)
        )
        if dish is None:
            raise HTTPException(status_code=404, detail="Dish not found")


def _safe_payload(model, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Keep only writable table columns; ownership/identity are server-owned."""
    column_names = {column.key for column in inspect(model).columns}
    server_managed = {"id", "account_id", "user_id", "deleted", "updated_at"}
    if model is Meal:
        server_managed.update({"photo_url", "photo_analysis", "assigned_via_photo"})
    return {
        key: value
        for key, value in (payload or {}).items()
        if key in column_names and key not in server_managed
    }


@router.post("", response_model=SyncResponse)
async def sync_changes(body: SyncRequest, user: str = Depends(get_current_user)):
    async with async_session() as session:
        conflicts: list[SyncConflictItem] = []
        applied: list[dict[str, Any]] = []

        for change in body.changes:
            model = ENTITY_MODELS.get(change.entity_type)
            if model is None:
                logger.warning("Unknown entity_type: %s", change.entity_type)
                continue

            if change.action not in {"create", "update", "delete"}:
                raise HTTPException(status_code=422, detail="Invalid sync action")

            # Never select a resource outside the authenticated account,
            # including when the request context is absent in tests/workers.
            result = await session.execute(
                select(model).where(model.id == change.entity_id, model.account_id == user)
            )
            existing = result.scalars().first()

            if change.action == "delete":
                if existing is not None:
                    if not hasattr(existing, "deleted"):
                        raise HTTPException(status_code=422, detail="Entity does not support deletion")
                    existing.deleted = True
                    if hasattr(existing, "updated_at"):
                        existing.updated_at = datetime.now(BERLIN_TZ)
                    applied.append({"entity_type": change.entity_type, "entity_id": str(change.entity_id), "action": "delete"})
                continue

            # Offline records are untrusted input. In particular, an IndexedDB
            # replay must never be able to carry either legacy or new owner
            # fields across the account boundary.
            payload = _safe_payload(model, change.payload)
            await _validate_owned_references(session, model, payload, user)

            if existing is None:
                # Treat update as an assertion that the record is already
                # owned by this account.  Falling through to create here would
                # turn an attempted cross-account update into a confusing
                # primary-key conflict (or, on a future non-global key, data
                # creation under the wrong operation).
                if change.action == "update":
                    raise HTTPException(status_code=404, detail="Sync entity not found")
                # Create new record
                obj = model(**payload, id=change.entity_id, account_id=user)
                session.add(obj)
                applied.append({"entity_type": change.entity_type, "entity_id": str(change.entity_id), "action": "create"})
            else:
                if change.action == "create":
                    raise HTTPException(status_code=409, detail="Sync entity already exists")
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
                    if hasattr(existing, field) and field not in {"id", "account_id", "user_id"}:
                        setattr(existing, field, value)
                applied.append({"entity_type": change.entity_type, "entity_id": str(change.entity_id), "action": "update"})

            # Log to sync_log
            session.add(SyncLog(
                account_id=user,
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
                            model.account_id == user,
                            model.updated_at > body.last_sync,
                        )
                    )
                    for obj in result.scalars().all():
                        server_changes.append({
                            "entity_type": entity_type,
                            "entity_id": str(obj.id),
                            "payload": {
                                c.name: getattr(obj, c.name)
                                for c in obj.__table__.columns
                                if c.name not in {"account_id", "user_id"}
                            },
                        })

        sync_token = datetime.now(BERLIN_TZ)
        return SyncResponse(
            server_changes=server_changes,
            conflicts=conflicts,
            sync_token=sync_token,
        )
