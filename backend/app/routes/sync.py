from __future__ import annotations

import logging
from datetime import datetime

from app.tz import BERLIN_TZ
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import inspect, select

from app.database import async_session
from app.models import DayEntry, Exercise, Todo, TrainingSet, SyncLog
from app.routes.auth import get_current_user
from app.schemas import SyncConflictItem, SyncOperationResult, SyncRequest, SyncResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

# Mapping entity_type → model
ENTITY_MODELS = {
    "day_entry": DayEntry,
    "todo": Todo,
    "training_set": TrainingSet,
    "exercise": Exercise,
}


async def _validate_owned_references(session, model, payload: dict[str, Any], account_id: str) -> None:
    """Reserved for syncable models with logical foreign-key references."""


def _safe_payload(model, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Keep only writable table columns; ownership/identity are server-owned."""
    column_names = {column.key for column in inspect(model).columns}
    server_managed = {"id", "account_id", "user_id", "deleted", "updated_at"}
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
        results: list[SyncOperationResult] = []

        for change_index, change in enumerate(body.changes):
            model = ENTITY_MODELS.get(change.entity_type)
            if model is None:
                results.append(SyncOperationResult(
                    change_index=change_index, entity_type=change.entity_type,
                    entity_id=change.entity_id, status="validation_error",
                    detail="Unknown sync entity type",
                ))
                continue

            if change.action not in {"create", "update", "delete"}:
                results.append(SyncOperationResult(
                    change_index=change_index, entity_type=change.entity_type,
                    entity_id=change.entity_id, status="validation_error",
                    detail="Invalid sync action",
                ))
                continue

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
                    results.append(SyncOperationResult(
                        change_index=change_index, entity_type=change.entity_type,
                        entity_id=change.entity_id, status="applied",
                    ))
                else:
                    # A repeated delete is safe and may leave the queue.
                    results.append(SyncOperationResult(
                        change_index=change_index, entity_type=change.entity_type,
                        entity_id=change.entity_id, status="duplicate",
                    ))
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
                    results.append(SyncOperationResult(
                        change_index=change_index, entity_type=change.entity_type,
                        entity_id=change.entity_id, status="validation_error",
                        detail="Sync entity not found",
                    ))
                    continue
                # Create new record
                obj = model(**payload, id=change.entity_id, account_id=user)
                session.add(obj)
                applied.append({"entity_type": change.entity_type, "entity_id": str(change.entity_id), "action": "create"})
            else:
                if change.action == "create":
                    results.append(SyncOperationResult(
                        change_index=change_index, entity_type=change.entity_type,
                        entity_id=change.entity_id, status="duplicate",
                    ))
                    continue
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
                    results.append(SyncOperationResult(
                        change_index=change_index, entity_type=change.entity_type,
                        entity_id=change.entity_id, status="conflict",
                        detail="Server version is newer",
                    ))
                    continue
                for field, value in payload.items():
                    if hasattr(existing, field) and field not in {"id", "account_id", "user_id"}:
                        setattr(existing, field, value)
                applied.append({"entity_type": change.entity_type, "entity_id": str(change.entity_id), "action": "update"})

            results.append(SyncOperationResult(
                change_index=change_index, entity_type=change.entity_type,
                entity_id=change.entity_id, status="applied",
            ))

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
            results=results,
            sync_token=sync_token,
        )
