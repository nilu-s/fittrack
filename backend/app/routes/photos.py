from __future__ import annotations

import base64
import logging
import os
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.database import async_session
from app.models import Photo
from app.schemas import PhotoAnalysisResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photos", tags=["photos"])


@router.post("/analyze", response_model=PhotoAnalysisResponse)
async def analyze_photo(file: UploadFile = File(...)):
    """Upload a food photo → save → call Ollama Vision → return analysis."""
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

    # Save photo record
    async with async_session() as session:
        photo = Photo(
            id=photo_id,
            user_id="luis",
            file_path=file_path,
            original_filename=file.filename,
            mime_type=file.content_type,
        )
        session.add(photo)
        await session.commit()

    # Call Ollama Vision
    analysis: Optional[dict] = None
    error: Optional[str] = None
    try:
        b64_image = base64.b64encode(contents).decode("utf-8")
        prompt = (
            "Du bist ein Ernährungs-Experte. Analysiere dieses Food-Foto. "
            "Erkenne die Speisen und schätze die Nährwerte (kcal, Protein g, Kohlenhydrate g, Fett g). "
            "Antworte NUR mit gültigem JSON im folgenden Format:\n"
            '{"items": [{"name": "...", "kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}], '
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
            except (json.JSONDecodeError, IndexError):
                error = f"Could not parse vision response: {content[:200]}"
                logger.warning(error)
    except Exception as e:
        error = f"Vision API error: {e}"
        logger.exception("Vision API call failed")

    return PhotoAnalysisResponse(
        photo_id=photo_id,
        file_path=file_path,
        analysis=analysis,
        error=error,
    )