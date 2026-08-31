"""Device-only scale ingestion and account-scoped measurement history."""
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from statistics import median

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import AccountWeightRange, BodyProfile, DayEntry, RegisteredDevice, ScaleMeasurement
from app.routes.auth import get_current_user
from app.schemas import BodyProfileResponse, BodyProfileUpdate, ScaleSyncV2Request
from app.services.scale_assignment import AssignmentRange, advance_baseline, choose_assignment

device_router = APIRouter(prefix="/scale-sync/v2", tags=["scale-sync"])
browser_router = APIRouter(prefix="/scale-measurements", tags=["scale-measurements"])


def _device_key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def _require_device(body: ScaleSyncV2Request, device_key: str | None) -> None:
    if not device_key:
        raise HTTPException(status_code=401, detail="Device authentication required")
    async with async_session() as session:
        device = (await session.execute(select(RegisteredDevice).where(RegisteredDevice.device_id == body.device_id))).scalar_one_or_none()
    if not device or not device.is_active or not hmac.compare_digest(device.credential_hash, _device_key_hash(device_key)):
        raise HTTPException(status_code=401, detail="Unknown device")


@device_router.post("")
async def ingest_scale_measurement(body: ScaleSyncV2Request, x_fittrack_device_key: str | None = Header(default=None)):
    await _require_device(body, x_fittrack_device_key)
    async with async_session() as session:
        existing = (await session.execute(
            select(ScaleMeasurement).execution_options(include_all_accounts=True).where(
                ScaleMeasurement.device_id == body.device_id,
                ScaleMeasurement.device_event_id == body.device_event_id,
            )
        )).scalar_one_or_none()
        if existing:
            return {"event_id": str(existing.id), "status": existing.status}

        rows = (await session.execute(select(AccountWeightRange).where(AccountWeightRange.is_active.is_(True)))).scalars().all()
        ranges = [
            AssignmentRange(
                account_id=str(row.account_id),
                minimum_kg=float(row.baseline_kg + row.lower_offset_kg),
                maximum_kg=float(row.baseline_kg + row.upper_offset_kg),
            )
            for row in rows
        ]
        try:
            assignment = choose_assignment(body.weight_kg, ranges)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail="Invalid server range configuration") from exc
        if assignment is None:
            return {"status": "discarded"}

        assigned_account_id = uuid.UUID(assignment.account_id)
        profile = (await session.execute(select(BodyProfile).where(BodyProfile.account_id == assigned_account_id))).scalar_one_or_none()
        bmi = None
        profile_snapshot = None
        if profile and profile.height_cm:
            height_m = Decimal(profile.height_cm) / Decimal("100")
            bmi = (Decimal(str(body.weight_kg)) / (height_m * height_m)).quantize(Decimal("0.1"))
            profile_snapshot = {"height_cm": float(profile.height_cm)}

        measurement = ScaleMeasurement(
            account_id=assigned_account_id,
            device_id=body.device_id,
            device_event_id=body.device_event_id,
            measured_at=body.measured_at,
            weight_kg=Decimal(str(body.weight_kg)),
            impedance_ohm=body.impedance_ohm,
            raw_payload=body.model_dump(mode="json"),
            status="assigned",
            assignment_method="weight_range",
            assignment_confidence=Decimal("1.0"),
            assignment_reason="unique active weight range",
            bmi=bmi,
            profile_snapshot=profile_snapshot,
        )
        session.add(measurement)
        await session.flush()
        history = (await session.execute(
            select(ScaleMeasurement.weight_kg)
            .execution_options(include_all_accounts=True)
            .where(ScaleMeasurement.account_id == assigned_account_id, ScaleMeasurement.status == "assigned")
            .order_by(ScaleMeasurement.measured_at.desc())
            .limit(28)
        )).scalars().all()
        own_range = next(row for row in rows if row.account_id == assigned_account_id)
        candidate_baseline = Decimal(str(advance_baseline(
            baseline_kg=float(own_range.baseline_kg),
            target_kg=float(median(history)),
            previous_updated_at=own_range.baseline_updated_at,
            now=datetime.now(timezone.utc),
        ))).quantize(Decimal("0.01"))
        if candidate_baseline != own_range.baseline_kg:
            candidate_ranges = [
                AssignmentRange(
                    account_id=str(row.account_id),
                    minimum_kg=float((candidate_baseline if row.id == own_range.id else row.baseline_kg) + row.lower_offset_kg),
                    maximum_kg=float((candidate_baseline if row.id == own_range.id else row.baseline_kg) + row.upper_offset_kg),
                )
                for row in rows
            ]
            # Calling the validator through assignment guarantees non-overlap
            # before changing the persistent baseline.
            choose_assignment(body.weight_kg, candidate_ranges)
            own_range.baseline_kg = candidate_baseline
            own_range.baseline_updated_at = datetime.now(timezone.utc)
        day = body.measured_at.astimezone(timezone.utc).date()
        entry = (await session.execute(select(DayEntry).where(DayEntry.account_id == measurement.account_id, DayEntry.date == day))).scalar_one_or_none()
        if entry is None:
            entry = DayEntry(account_id=measurement.account_id, user_id="legacy", date=day)
            session.add(entry)
        # A scale event is a projection. Do not replace a newer manual weight.
        if entry.weight_source != "manual":
            entry.weight_kg = measurement.weight_kg
            entry.weight_source = "scale_esp"
            entry.bmi = bmi
        await session.commit()
        return {"event_id": str(measurement.id), "status": "assigned"}


@browser_router.get("")
async def list_measurements(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    account_id=Depends(get_current_user),
):
    async with async_session() as session:
        statement = select(ScaleMeasurement).where(ScaleMeasurement.status == "assigned")
        if from_:
            statement = statement.where(ScaleMeasurement.measured_at >= from_)
        if to:
            statement = statement.where(ScaleMeasurement.measured_at <= to)
        rows = (await session.execute(statement.order_by(ScaleMeasurement.measured_at.desc()))).scalars().all()
    return [
        {"id": str(item.id), "measured_at": item.measured_at, "weight_kg": item.weight_kg, "bmi": item.bmi, "status": item.status}
        for item in rows
    ]


@browser_router.post("/{measurement_id}/reject")
async def reject_measurement(measurement_id: uuid.UUID, account_id=Depends(get_current_user)):
    async with async_session() as session:
        item = await session.get(ScaleMeasurement, measurement_id)
        if not item or item.status != "assigned":
            raise HTTPException(status_code=404, detail="Measurement not found")
        item.status = "rejected"
        item.rejected_at = datetime.now(timezone.utc)
        item.assignment_reason = "removed by assigned account"
        await session.commit()
    return {"id": str(measurement_id), "status": "rejected"}


profile_router = APIRouter(prefix="/account/body-profile", tags=["account"])


@profile_router.get("", response_model=BodyProfileResponse | None)
async def get_body_profile(account_id=Depends(get_current_user)):
    async with async_session() as session:
        profile = (await session.execute(select(BodyProfile))).scalar_one_or_none()
    return profile


@profile_router.put("", response_model=BodyProfileResponse)
async def update_body_profile(body: BodyProfileUpdate, account_id=Depends(get_current_user)):
    async with async_session() as session:
        profile = (await session.execute(select(BodyProfile))).scalar_one_or_none()
        if profile is None:
            profile = BodyProfile(account_id=account_id, **body.model_dump())
            session.add(profile)
        else:
            for field, value in body.model_dump(exclude_unset=True).items():
                setattr(profile, field, value)
        await session.commit()
        await session.refresh(profile)
    return profile
