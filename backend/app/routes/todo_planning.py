"""Account-private helpers for AI-assisted todo planning and travel estimates."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import Todo
from app.routes.auth import get_current_user
from app.schemas import (
    PlaceSuggestion,
    AssistantRequest,
    AssistantResponse,
    TodoDraftRequest,
    TodoDraftResponse,
    TravelEstimateRequest,
    TravelEstimateResponse,
)
from app.tz import BERLIN_TZ

router = APIRouter(prefix="/todo-planning", tags=["todo-planning"])

_WEEKDAYS = {
    "montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3,
    "freitag": 4, "samstag": 5, "sonntag": 6,
}


def _relative_due_date(text: str, reference: date) -> date:
    """Resolve German weekday wording against the selected calendar day.

    "Nächsten Freitag" is deliberately the Friday *after* the selected day;
    plain "Freitag" means the next matching day, including today. This keeps
    the offline fallback predictable when the LLM is unavailable.
    """
    normalized = text.casefold()
    for name, weekday in _WEEKDAYS.items():
        if not re.search(rf"\b{name}\b", normalized):
            continue
        days = (weekday - reference.weekday()) % 7
        if re.search(rf"\b(?:nächsten|naechsten|kommenden)\s+{name}\b", normalized):
            days = days or 7
            if days < 7:
                days += 7
        return reference + timedelta(days=days)
    if "übermorgen" in normalized or "uebermorgen" in normalized:
        return reference + timedelta(days=2)
    if "morgen" in normalized:
        return reference + timedelta(days=1)
    return reference


def _fallback_draft(body: TodoDraftRequest) -> TodoDraftResponse:
    """Safe local fallback when no LLM integration is configured.

    It deliberately produces a reviewable partial draft, never an inferred
    destination identifier or an automatically created record.
    """
    text = body.text.strip()
    time_match = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", text)
    start_time = None
    if time_match:
        from datetime import time
        start_time = time(int(time_match.group(1)), int(time_match.group(2)))
    mode = next((value for token, value in (("auto", "drive"), ("fahrrad", "bicycle"), ("rad", "bicycle"), ("zu fuß", "walk"), ("laufen", "walk"), ("öpnv", "transit"), ("bahn", "transit")) if token in text.casefold()), None)
    place_match = re.search(r"\b(?:bei|in|zum|zur)\s+(.+?)(?:,|\.|$)", text, re.IGNORECASE)
    place_query = place_match.group(1).strip() if place_match else None
    due_date = _relative_due_date(text, body.date)
    title = re.sub(r"\b(?:nächsten|naechsten|kommenden)\s+", "", text, flags=re.IGNORECASE)
    title = re.sub(r"\b(?:montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\b\d{1,2}[:.]\d{2}\b", "", title).strip(" ,.-") or text
    needs_review = []
    if start_time is None:
        needs_review.append("Startzeit fehlt")
    if place_query is None:
        needs_review.append("Ort auswählen")
    return TodoDraftResponse(title=title[:200], due_date=due_date, start_time=start_time, place_query=place_query, travel_mode=mode, needs_review=needs_review)


async def _codex_draft(body: TodoDraftRequest) -> TodoDraftResponse | None:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{settings.VISION_PROXY_URL}/todo-draft", json={"text": body.text, "date": body.date.isoformat()})
        if response.status_code != 200:
            return None
        parsed = response.json()
        parsed["due_date"] = parsed.get("due_date") or body.date.isoformat()
        return TodoDraftResponse.model_validate(parsed)
    except (httpx.HTTPError, ValueError, TypeError):
        return None


@router.post("/draft", response_model=TodoDraftResponse)
async def draft_todo(body: TodoDraftRequest, user=Depends(get_current_user)):
    # `user` intentionally only establishes the browser account boundary. The
    # LLM receives neither identity, coordinates, prior todos nor tokens.
    return await _codex_draft(body) or _fallback_draft(body)


@router.post("/assistant", response_model=AssistantResponse)
async def assistant_reply(body: AssistantRequest, user=Depends(get_current_user)):
    """General, opt-in assistant: it can advise, never mutate account data."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{settings.VISION_PROXY_URL}/assistant", json={"text": body.text, "date": body.date.isoformat()})
        if response.status_code == 200:
            return AssistantResponse.model_validate(response.json())
    except (httpx.HTTPError, ValueError, TypeError):
        pass
    raise HTTPException(502, "KI-Assistent ist derzeit nicht verfügbar")


@router.get("/places", response_model=list[PlaceSuggestion])
async def search_places(query: str = Query(min_length=2, max_length=200), user=Depends(get_current_user)):
    if not settings.GOOGLE_MAPS_API_KEY:
        raise HTTPException(503, "Google Maps is not configured")
    headers = {"X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY, "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post("https://places.googleapis.com/v1/places:searchText", headers=headers, json={"textQuery": query, "languageCode": "de"})
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Ortssuche ist derzeit nicht erreichbar") from exc
    if response.status_code != 200:
        raise HTTPException(502, "Ortssuche ist derzeit nicht verfügbar")
    return [PlaceSuggestion(place_id=item["id"], name=item.get("displayName", {}).get("text") or item.get("formattedAddress") or "Ort", address=item.get("formattedAddress")) for item in response.json().get("places", []) if item.get("id")]


@router.post("/{todo_id}/estimate", response_model=TravelEstimateResponse)
async def estimate_travel(todo_id: str, body: TravelEstimateRequest, user=Depends(get_current_user)):
    async with async_session() as session:
        todo = await session.scalar(select(Todo).where(Todo.id == todo_id, Todo.account_id == user, Todo.deleted.is_(False)))
        if todo is None:
            raise HTTPException(404, "Todo not found")
        if not (todo.place_id and todo.due_date and todo.start_time and todo.travel_mode):
            raise HTTPException(422, "Todo needs an exact place, date, start time and travel mode")
        if not settings.GOOGLE_MAPS_API_KEY:
            raise HTTPException(503, "Google Maps is not configured")
        now = datetime.now(BERLIN_TZ)
        arrival = datetime.combine(todo.due_date, todo.start_time, tzinfo=BERLIN_TZ) - timedelta(minutes=todo.travel_buffer_minutes)
        travel_mode = {"drive": "DRIVE", "bicycle": "BICYCLE", "walk": "WALK", "transit": "TRANSIT"}[todo.travel_mode]
        request = {"origin": {"location": {"latLng": {"latitude": body.origin_latitude, "longitude": body.origin_longitude}}}, "destination": {"placeId": todo.place_id}, "travelMode": travel_mode}
        if todo.travel_mode == "drive":
            request.update({"routingPreference": "TRAFFIC_AWARE", "departureTime": now.isoformat()})
        headers = {"X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY, "X-Goog-FieldMask": "routes.duration"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post("https://routes.googleapis.com/directions/v2:computeRoutes", headers=headers, json=request)
        except httpx.HTTPError as exc:
            raise HTTPException(502, "Routenberechnung ist derzeit nicht erreichbar") from exc
        if response.status_code != 200 or not response.json().get("routes"):
            raise HTTPException(502, "Routenberechnung ist derzeit nicht verfügbar")
        duration = int(str(response.json()["routes"][0]["duration"]).removesuffix("s"))
        depart_at = arrival - timedelta(seconds=duration)
        todo.travel_duration_seconds = duration
        todo.travel_depart_at = depart_at
        todo.travel_last_checked_at = now
        await session.commit()
        return TravelEstimateResponse(duration_seconds=duration, depart_at=depart_at, arrival_at=arrival, checked_at=now, traffic_aware=todo.travel_mode == "drive")
