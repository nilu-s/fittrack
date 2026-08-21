#!/usr/bin/env python3
"""
Vision Proxy: bridges FitTrack backend → Codex/GPT-5.5 vision API.
Reads OAuth token from Hermes auth.json, refreshes if needed, calls Codex responses API.
Listens on 127.0.0.1:8100 — only accessible from localhost (Docker containers via host gateway).
"""
import base64
import json
import logging
import os
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTH_FILE = Path(os.environ.get("HERMES_AUTH_FILE", "/root/.hermes/auth.json"))
CODEX_API = "https://chatgpt.com/backend-api/codex/responses"
MODEL = "gpt-5.5"

app = FastAPI()

# Token cache
_cached_token: str = ""
_cached_exp: float = 0


def get_codex_token() -> str:
    """Read the current valid OAuth token from auth.json."""
    global _cached_token, _cached_exp
    # Check cache first (5 min buffer)
    if _cached_token and _cached_exp > time.time() + 300:
        return _cached_token

    with open(AUTH_FILE) as f:
        d = json.load(f)
    creds = d.get("credential_pool", {}).get("openai-codex", [])
    now = time.time()
    for c in creds:
        token = c.get("access_token", "")
        if not token:
            continue
        # Try to decode JWT expiration
        try:
            parts = token.split(".")
            if len(parts) >= 2:
                payload = json.loads(base64.b64decode(parts[1] + "=="))
                exp = payload.get("exp", 0)
                if exp > now + 300:
                    _cached_token = token
                    _cached_exp = exp
                    logger.info("Using token expiring in %d min", (exp - now) / 60)
                    return token
        except Exception:
            # Not a JWT, try it anyway
            _cached_token = token
            _cached_exp = now + 3600
            return token
    # If no valid token, use the first one anyway
    if creds:
        _cached_token = creds[0].get("access_token", "")
        _cached_exp = now + 3600
        logger.warning("No valid token found, using first available")
        return _cached_token
    raise HTTPException(status_code=500, detail="No Codex credentials available")


class AnalyzeRequest(BaseModel):
    image_base64: str


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL}


@app.post("/analyze")
async def analyze_photo_json(req: AnalyzeRequest):
    """Analyze a food photo using GPT-5.5 via Codex API. Accepts base64 JSON."""
    b64 = req.image_base64
    if not b64:
        raise HTTPException(status_code=400, detail="Empty image")
    return await _do_analysis(b64)


@app.post("/analyze-upload")
async def analyze_photo(file: UploadFile = File(...)):
    """Analyze a food photo from multipart upload."""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")
    b64 = base64.b64encode(contents).decode()
    return await _do_analysis(b64)


async def _do_analysis(b64: str) -> JSONResponse:
    token = get_codex_token()

    prompt = (
        'You are a nutrition expert. Analyze this food photo. '
        'If this is NOT a food photo (e.g. clothes, furniture, scenery), respond: {"not_food": true}. '
        'If it IS food, respond ONLY with valid JSON:\n'
        '{"not_food": false, "items": [{"name": "German dish name", "kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, '
        '"portion_label": "100g", "portion_grams": 100, "is_scalable": true}], '
        '"total": {"kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}}\n\n'
        'Portion rules:\n'
        '- For packaged/weighted foods (chips, yogurt, pasta, etc.): set portion_label to the package size '
        '(e.g. "100g", "200g"), portion_grams to the numeric value, is_scalable=true. '
        'Nutritional values are PER the full package/serving shown.\n'
        '- For single-serving foods (Döner, pizza slice, apple, bowl): set portion_label to "1 Portion", '
        'portion_grams to null, is_scalable=false. Nutritional values are for one serving.\n'
        '- Always research realistic nutritional values for the identified dish.'
    )

    try:
        full_text = ""
        with httpx.stream(
            "POST",
            CODEX_API,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "store": False,
                "stream": True,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
                        ],
                    }
                ],
            },
            timeout=120,
        ) as r:
            if r.status_code == 429:
                raise HTTPException(status_code=429, detail="Codex rate limited")
            if r.status_code != 200:
                body = r.read().decode()[:300]
                logger.error("Codex API error %d: %s", r.status_code, body)
                raise HTTPException(status_code=502, detail=f"Codex error: {r.status_code}")
            for line in r.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        ev = json.loads(data)
                        if ev.get("type") == "response.output_text.delta":
                            full_text += ev.get("delta", "")
                    except Exception:
                        pass

        # Parse the JSON response
        full_text = full_text.strip()
        if full_text.startswith("```"):
            lines = full_text.split("\n")
            lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            full_text = "\n".join(lines)

        result = json.loads(full_text)

        # Check if not food
        if result.get("not_food"):
            return JSONResponse({"not_food": True, "analysis": None, "error": "Not a food photo"})

        # Normalize format
        if "items" not in result and "name" in result:
            item = {k: result[k] for k in ("name", "kcal", "protein_g", "carbs_g", "fat_g") if k in result}
            result = {"items": [item], "total": {k: result.get(k, 0) for k in ("kcal", "protein_g", "carbs_g", "fat_g")}}
        if "items" in result and "total" not in result:
            items = result["items"]
            result["total"] = {
                "kcal": sum(float(i.get("kcal", 0)) for i in items),
                "protein_g": sum(float(i.get("protein_g", 0)) for i in items),
                "carbs_g": sum(float(i.get("carbs_g", 0)) for i in items),
                "fat_g": sum(float(i.get("fat_g", 0)) for i in items),
            }

        return JSONResponse({"not_food": False, "analysis": result, "error": None})

    except httpx.ConnectError as e:
        logger.exception("Connection error")
        raise HTTPException(status_code=502, detail=str(e))
    except json.JSONDecodeError:
        logger.error("Could not parse response: %s", full_text[:200])
        raise HTTPException(status_code=500, detail=f"Parse error: {full_text[:200]}")
    except Exception as e:
        logger.exception("Vision proxy error")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100, log_level="info")