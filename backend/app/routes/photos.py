from __future__ import annotations

import base64
import logging
import os
import uuid
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.config import settings
from app.database import async_session
from app.models import Dish, Meal, Photo
from app.routes.auth import get_current_user
from app.schemas import DishMatchResult, DishResponse, PhotoAnalysisResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photos", tags=["photos"])


@router.post("/analyze", response_model=PhotoAnalysisResponse)
async def analyze_photo(
    file: UploadFile = File(...),
    meal_id: Optional[str] = Form(None),
    user: str = Depends(get_current_user),
):
    """Upload a food photo → save → call the vision service → return analysis.

    If meal_id is provided, the analysis result is also persisted to the meal:
    - meal.photo_analysis = analysis
    - meal.assigned_via_photo = True
    - meal.photo_url = file_path
    - Photo.meal_id = meal_id
    """
    # Read file content
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    # Ensure photo directory exists
    os.makedirs(settings.PHOTO_DIR, exist_ok=True)

    # Save the photo
    photo_id = uuid.uuid4()
    ext = ""
    if file.filename and "." in file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1]
    filename = f"{photo_id}{ext}"
    file_path = os.path.join(settings.PHOTO_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    # Parse meal_id to UUID if provided
    parsed_meal_id = None
    if meal_id:
        try:
            parsed_meal_id = uuid.UUID(meal_id)
        except (ValueError, AttributeError):
            logger.warning("Invalid meal_id provided: %s", meal_id)

    # Save photo record
    async with async_session() as session:
        photo = Photo(
            id=photo_id,
            user_id="luis",
            meal_id=parsed_meal_id,
            file_path=file_path,
            original_filename=file.filename,
            mime_type=file.content_type,
        )
        session.add(photo)
        await session.commit()

    # Call vision proxy (GPT-5.5 via Codex) — one-step, handles food detection + JSON
    analysis: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    try:
        b64_image = base64.b64encode(contents).decode("utf-8")
        proxy_url = settings.VISION_PROXY_URL

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{proxy_url}/analyze",
                json={"image_base64": b64_image},
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("not_food"):
                error = "Kein Essen erkannt — Foto zeigt kein Gericht"
            elif data.get("analysis"):
                analysis = data["analysis"]
            else:
                error = data.get("error", "Unbekannter Fehler")
    except Exception as e:
        error = f"Vision API error: {e}"
        logger.exception("Vision API call failed")

    # If analysis succeeded and meal_id was provided, persist to meal
    dish_match: Optional[DishMatchResult] = None
    if analysis is not None and parsed_meal_id is not None:
        async with async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Meal).where(Meal.id == parsed_meal_id, Meal.deleted == False)
            )
            meal = result.scalars().first()
            if meal is not None:
                meal.photo_analysis = analysis
                meal.assigned_via_photo = True
                meal.photo_url = file_path
                await session.commit()
                logger.info("Photo analysis persisted to meal %s", parsed_meal_id)

                # --- Dish duplicate check (slot-independent) ---
                dish_name = analysis.get("items", [{}])[0].get("name", "Erkanntes Gericht")
                dish_match = await _match_dish(session, "luis", dish_name)
                # Auto-create dish if no match found
                if not dish_match.matched:
                    item = analysis.get("items", [{}])[0]
                    total = analysis.get("total", {})
                    new_dish = Dish(
                        user_id="luis",
                        slot=None,
                        name=dish_name,
                        kcal=total.get("kcal"),
                        protein_g=total.get("protein_g"),
                        carbs_g=total.get("carbs_g"),
                        fat_g=total.get("fat_g"),
                        fiber_g=total.get("fiber_g"),
                        sugar_g=total.get("sugar_g"),
                        free_sugar_g=total.get("free_sugar_g"),
                        source="photo",
                        is_default=False,
                        usage_count=1,
                        portion_label=item.get("portion_label"),
                        portion_grams=item.get("portion_grams"),
                        is_scalable=item.get("is_scalable", False),
                    )
                    session.add(new_dish)
                    await session.commit()
                    await session.refresh(new_dish)
                    dish_match = DishMatchResult(matched=True, dish=DishResponse.model_validate(new_dish), similarity=1.0)
                    logger.info("Auto-created dish from photo: %s", dish_name)
            else:
                logger.warning("Meal %s not found for photo analysis", parsed_meal_id)
    elif analysis is not None:
        # No meal_id — still do dish match + auto-create for standalone photos
        dish_name = analysis.get("items", [{}])[0].get("name", "Erkanntes Gericht")
        async with async_session() as session:
            dish_match = await _match_dish(session, "luis", dish_name)
            if not dish_match.matched:
                item = analysis.get("items", [{}])[0]
                total = analysis.get("total", {})
                new_dish = Dish(
                    user_id="luis",
                    slot=None,
                    name=dish_name,
                    kcal=total.get("kcal"),
                    protein_g=total.get("protein_g"),
                    carbs_g=total.get("carbs_g"),
                    fat_g=total.get("fat_g"),
                    fiber_g=total.get("fiber_g"),
                    sugar_g=total.get("sugar_g"),
                    free_sugar_g=total.get("free_sugar_g"),
                    source="photo",
                    is_default=False,
                    usage_count=1,
                    portion_label=item.get("portion_label"),
                    portion_grams=item.get("portion_grams"),
                    is_scalable=item.get("is_scalable", False),
                )
                session.add(new_dish)
                await session.commit()
                await session.refresh(new_dish)
                dish_match = DishMatchResult(matched=True, dish=DishResponse.model_validate(new_dish), similarity=1.0)
                logger.info("Auto-created dish from standalone photo: %s", dish_name)

    return PhotoAnalysisResponse(
        photo_id=photo_id,
        file_path=file_path,
        analysis=analysis,
        error=error,
        dish_match=dish_match,
    )


async def _match_dish(session, user_id: str, name: str) -> DishMatchResult:
    """Fuzzy-match a dish name against ALL existing dishes (slot-independent).
    Returns best match if similarity >= 0.75."""
    from difflib import SequenceMatcher
    import sqlalchemy as sa

    def normalize(n: str) -> str:
        return " ".join(n.strip().lower().split())

    stmt = sa.select(Dish).where(Dish.user_id == user_id)
    result = await session.execute(stmt)
    dishes = list(result.scalars().all())

    best_dish = None
    best_score = 0.0
    norm_name = normalize(name)

    for dish in dishes:
        score = SequenceMatcher(None, norm_name, normalize(dish.name)).ratio()
        if score > best_score:
            best_score = score
            best_dish = dish

    if best_dish and best_score >= 0.75:
        return DishMatchResult(matched=True, dish=DishResponse.model_validate(best_dish), similarity=best_score)
    return DishMatchResult(matched=False, similarity=best_score)