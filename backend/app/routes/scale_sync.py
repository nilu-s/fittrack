"""Scale sync endpoint — receives weight + body composition from ESP32 BLE scale.

The ESP32 reads a Renpho (or similar) BLE scale, sends raw weight + impedance
to this endpoint. If body composition isn't pre-calculated by the ESP, the
server calculates it from impedance + user profile using standard formulas.
"""
from __future__ import annotations

import math
from datetime import date as date_type
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.database import async_session
from app.models import DayEntry
from app.routes.auth import get_current_user
from app.schemas import ScaleSyncRequest, DayEntryResponse

router = APIRouter(prefix="/scale-sync", tags=["scale-sync"])


def _calc_body_composition(
    weight_kg: float,
    impedance: int,
    height_cm: float,
    age: int,
    gender: str,
) -> dict:
    """Calculate body composition from impedance using standard BIA formulas.

    Based on the widely-used formulas from open-source scale projects
    (openScale, Espressif BLE scale examples, Renpho reverse-engineering).
    """
    h = height_cm / 100.0  # height in meters
    bmi = weight_kg / (h * h) if h > 0 else 0.0

    # Impedance-based calculations (simplified BIA model)
    # Resistance R = impedance, Reactance Xc ≈ 0 for these scales
    z = float(impedance) if impedance > 0 else 500.0  # fallback

    # Total Body Water (TBW) — Watson formulas + impedance correction
    if gender.lower() == "male":
        tbw = 2.447 - 0.09156 * age + 0.1074 * height_cm + 0.3362 * weight_kg
    else:
        tbw = -2.097 + 0.1069 * height_cm + 0.2466 * weight_kg

    water_pct = (tbw / weight_kg * 100.0) if weight_kg > 0 else 0.0

    # Fat-Free Mass (FFM) — impedance-based estimate
    # FFM = -0.99 + 0.36 * weight + 0.37 * height_cm - 0.14 * age + 0.0004 * z^2 + (gender_adj)
    if gender.lower() == "male":
        ffm = -0.99 + 0.36 * weight_kg + 0.37 * height_cm - 0.14 * age + 4.8 * (height_cm / 100) - 0.0001 * z * z
    else:
        ffm = -0.99 + 0.36 * weight_kg + 0.37 * height_cm - 0.14 * age + 0.0001 * z * z

    ffm = max(ffm, 0.0)
    fat_mass = weight_kg - ffm
    body_fat_pct = (fat_mass / weight_kg * 100.0) if weight_kg > 0 else 0.0
    body_fat_pct = max(0.0, min(100.0, body_fat_pct))

    # Muscle mass — ~FFM minus bone mass
    bone_mass = _calc_bone_mass(weight_kg, height_cm, gender)
    muscle_mass = max(0.0, ffm - bone_mass)

    # BMR — Mifflin-St Jeor
    if gender.lower() == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    bmr = int(round(bmr))

    # Visceral fat — simple estimate based on BMI + waist proxy
    if gender.lower() == "male":
        vf = 0.5 * bmi - 5.5 if bmi > 11 else 0
    else:
        vf = 0.4 * bmi - 4.0 if bmi > 11 else 0
    visceral_fat = max(0, int(round(vf)))

    # Metabolic age — rough estimate (actual age if healthy)
    metabolic_age = max(age, int(round(age + (body_fat_pct - 15) * 0.5))) if body_fat_pct > 15 else age

    return {
        "body_fat_pct": round(body_fat_pct, 1),
        "muscle_mass_kg": round(muscle_mass, 1),
        "water_pct": round(water_pct, 1),
        "bone_mass_kg": round(bone_mass, 1),
        "bmi": round(bmi, 1),
        "basal_metabolism": bmr,
        "visceral_fat": visceral_fat,
        "metabolic_age": metabolic_age,
    }


def _calc_bone_mass(weight_kg: float, height_cm: float, gender: str) -> float:
    """Estimate bone mass from weight and height."""
    if gender.lower() == "male":
        base = 0.0 + 0.025 * weight_kg + 0.001 * height_cm
    else:
        base = 0.5 + 0.02 * weight_kg + 0.0005 * height_cm
    return max(1.5, min(5.5, round(base, 1)))


@router.post("", response_model=DayEntryResponse)
async def scale_sync(
    body: ScaleSyncRequest,
    user: str = Depends(get_current_user),
):
    """Receive weight + body composition from ESP32 BLE scale.

    Auth: JWT session cookie OR X-FitTrack-CLI-Key header (same as CLI auth).
    The ESP32 sends X-FitTrack-CLI-Key header for authentication.
    If body composition fields aren't provided but impedance + profile are,
    the server calculates them.
    """

    # Determine date
    entry_date = date_type.today()
    if body.date:
        try:
            entry_date = date_type.fromisoformat(body.date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date format, use YYYY-MM-DD")

    weight = Decimal(str(body.weight_kg))

    # Body composition: use pre-calculated or compute from impedance
    comp: dict = {}
    if body.body_fat_pct is not None:
        # ESP sent pre-calculated values
        comp = {
            "body_fat_pct": Decimal(str(body.body_fat_pct)),
            "muscle_mass_kg": Decimal(str(body.muscle_mass_kg)) if body.muscle_mass_kg else None,
            "water_pct": Decimal(str(body.water_pct)) if body.water_pct else None,
            "bone_mass_kg": Decimal(str(body.bone_mass_kg)) if body.bone_mass_kg else None,
            "bmi": Decimal(str(body.bmi)) if body.bmi else None,
            "basal_metabolism": body.basal_metabolism,
            "visceral_fat": body.visceral_fat,
            "metabolic_age": body.metabolic_age,
        }
    elif body.impedance is not None and body.height_cm and body.age and body.gender:
        # Server-side calculation from impedance
        calc = _calc_body_composition(
            body.weight_kg, body.impedance, body.height_cm, body.age, body.gender
        )
        comp = {k: Decimal(str(v)) if isinstance(v, float) else v for k, v in calc.items()}

    async with async_session() as session:
        result = await session.execute(
            select(DayEntry).where(DayEntry.user_id == "luis", DayEntry.date == entry_date)
        )
        entry = result.scalars().first()

        if entry is None:
            entry = DayEntry(user_id="luis", date=entry_date)
            session.add(entry)

        # Always update weight from scale
        entry.weight_kg = weight
        entry.weight_source = "scale_esp"

        # Update body composition fields
        if comp:
            for field, value in comp.items():
                if value is not None:
                    setattr(entry, field, value)
        if body.impedance is not None:
            entry.impedance = body.impedance

        await session.commit()
        await session.refresh(entry)
        return DayEntryResponse.model_validate(entry)