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
    """Upload a food photo → save → call Ollama Vision → return analysis.

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

    # Call Ollama Vision
    analysis: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    try:
        b64_image = base64.b64encode(contents).decode("utf-8")
        prompt = (
            "You are a nutrition expert. Analyze this food photo. "
            "Identify the dish and estimate nutritional values. "
            "Respond ONLY with valid JSON in this exact format, no other text:\n"
            '{"items": [{"name": "dish name", "kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}], '
            '"total": {"kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}}'
        )

        payload = {
            "model": settings.OLLAMA_VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64_image],
                }
            ],
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_URL}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            # Extract the message content and parse JSON
            content = data.get("message", {}).get("content", "")
            # Try to extract JSON from the response
            import json
            try:
                # The model might return JSON directly or wrapped in markdown
                content = content.strip()
                if content.startswith("```"):
                    # Strip markdown code fences
                    lines = content.split("\n")
                    lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                    content = "\n".join(lines)
                analysis = json.loads(content)
                assert analysis is not None and isinstance(analysis, dict), f"Invalid JSON: {type(analysis)}"
                # Normalize: ensure items[] and total{} exist
                if "items" not in analysis and "name" in analysis:
                    # Model returned flat format → wrap it
                    item = {k: analysis[k] for k in ("name", "kcal", "protein_g", "carbs_g", "fat_g") if k in analysis}
                    analysis = {"items": [item], "total": {k: analysis.get(k, 0) for k in ("kcal", "protein_g", "carbs_g", "fat_g")}}
                if "items" in analysis and "total" not in analysis:
                    items = analysis["items"]
                    analysis["total"] = {
                        "kcal": sum(float(i.get("kcal", 0)) for i in items),
                        "protein_g": sum(float(i.get("protein_g", 0)) for i in items),
                        "carbs_g": sum(float(i.get("carbs_g", 0)) for i in items),
                        "fat_g": sum(float(i.get("fat_g", 0)) for i in items),
                    }
            except (json.JSONDecodeError, IndexError):
                error = f"Could not parse vision response: {content[:200]}"
                logger.warning(error)
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

                # --- Dish duplicate check ---
                dish_name = analysis.get("items", [{}])[0].get("name", "Erkanntes Gericht")
                dish_match = await _match_dish(session, "luis", meal.meal_slot, dish_name)
            else:
                logger.warning("Meal %s not found for photo analysis", parsed_meal_id)
    elif analysis is not None:
        # No meal_id — still do dish match for standalone photos
        dish_name = analysis.get("items", [{}])[0].get("name", "Erkanntes Gericht")
        async with async_session() as session:
            dish_match = await _match_dish(session, "luis", None, dish_name)

    return PhotoAnalysisResponse(
        photo_id=photo_id,
        file_path=file_path,
        analysis=analysis,
        error=error,
        dish_match=dish_match,
    )


async def _match_dish(session, user_id: str, slot: Optional[int], name: str) -> DishMatchResult:
    """Fuzzy-match a dish name against existing dishes. Returns best match if similarity >= 0.75."""
    from difflib import SequenceMatcher
    import sqlalchemy as sa

    def normalize(n: str) -> str:
        return " ".join(n.strip().lower().split())

    stmt = sa.select(Dish).where(Dish.user_id == user_id)
    if slot is not None:
        stmt = stmt.where(Dish.slot == slot)
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