"""Privacy-preserving Pictogramicl delivery client and local SVG cache."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import unicodedata
from urllib.parse import quote, urljoin, urlparse

import httpx
from sqlalchemy import select

from app.config import settings
from app.models import PictogramDeliveryCache

_PRIVATE_VALUE = re.compile(r"(?:https?://|www\.)|[\w.+-]+@[\w.-]+|(?:\+?\d[\d\s()./-]{6,}\d)", re.I)
_MAX_SVG_BYTES = 180_000
_FALLBACK_RETRY = timedelta(minutes=15)


@dataclass(frozen=True)
class DeliveredPictogram:
    svg: str
    state: str
    etag: str | None


def _normalise_public_term(value: str) -> str | None:
    term = " ".join(value.split())
    if not term or len(term) > 120 or _PRIVATE_VALUE.search(term):
        return None
    return term


def _cache_key(term: str) -> str:
    message = f"pictogramicl-v1:shopping:{term.casefold()}".encode()
    return hmac.new(settings.APP_JWT_SECRET.encode(), message, hashlib.sha256).hexdigest()


def _fallback_key() -> str:
    return _cache_key("__private_or_unavailable__")


def _placeholder_initial(term: str | None) -> str:
    if not term:
        return "_"
    folded = unicodedata.normalize("NFKD", term)
    for char in folded:
        if char.isascii() and char.isalnum():
            return char.upper()
    return "_"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _same_service_url(url: str) -> str:
    """Only follow Pictogramicl URLs; a response cannot redirect asset fetches."""
    base = urlparse(settings.PICTOGRAMICL_URL.rstrip("/") + "/")
    resolved = urlparse(urljoin(settings.PICTOGRAMICL_URL.rstrip("/") + "/", url))
    if (resolved.scheme, resolved.netloc) != (base.scheme, base.netloc):
        raise ValueError("Pictogramicl returned an external asset URL")
    return resolved.geturl()


async def _asset(client: httpx.AsyncClient, url: str) -> tuple[str, str | None]:
    response = await client.get(_same_service_url(url), headers={"X-Api-Key": settings.PICTOGRAMICL_API_KEY})
    response.raise_for_status()
    content = response.content
    if len(content) > _MAX_SVG_BYTES or not content.lstrip().startswith(b"<svg"):
        raise ValueError("Pictogramicl returned an invalid SVG")
    return content.decode("utf-8"), response.headers.get("etag")


async def _save(session, key: str, *, svg: str, state: str, etag: str | None,
                concept_key: str | None = None, revision: int | None = None,
                placeholder_initial: str | None = None, placeholder_revision: int | None = None,
                retry_after: datetime | None = None) -> PictogramDeliveryCache:
    row = await session.scalar(select(PictogramDeliveryCache).where(PictogramDeliveryCache.cache_key == key))
    if row is None:
        row = PictogramDeliveryCache(cache_key=key, svg_markup=svg, state=state)
        session.add(row)
    row.svg_markup, row.state, row.etag = svg, state, etag
    row.concept_key, row.revision = concept_key, revision
    row.placeholder_initial, row.placeholder_revision = placeholder_initial, placeholder_revision
    row.retry_after = retry_after
    await session.flush()
    return row


async def _placeholder(session, initial: str) -> DeliveredPictogram:
    """Fetch one immutable Pictogramicl initial, never a locally drawn glyph."""
    key = _cache_key(f"__placeholder__:{initial}")
    cached = await session.scalar(select(PictogramDeliveryCache).where(PictogramDeliveryCache.cache_key == key))
    if cached is not None:
        return DeliveredPictogram(cached.svg_markup, cached.state, cached.etag)
    url = f"/v1/styles/{quote(settings.PICTOGRAMICL_STYLE, safe='')}/placeholders/2/{initial}.svg"
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0), follow_redirects=False) as client:
        svg, etag = await _asset(client, url)
    row = await _save(session, key, svg=svg, state="placeholder", etag=etag,
                      placeholder_initial=initial, placeholder_revision=2)
    return DeliveredPictogram(row.svg_markup, row.state, row.etag)


async def _generic_placeholder(session) -> DeliveredPictogram:
    return await _placeholder(session, "_")


async def prepare_shopping_pictogram(session, title: str) -> tuple[DeliveredPictogram, bool]:
    """Return a placeholder immediately and report whether a background lookup is due."""
    term = _normalise_public_term(title)
    if term is None:
        return await _generic_placeholder(session), False
    key = _cache_key(term)
    cached = await session.scalar(select(PictogramDeliveryCache).where(PictogramDeliveryCache.cache_key == key))
    if cached is not None and cached.state == "available":
        return DeliveredPictogram(cached.svg_markup, cached.state, cached.etag), False
    if cached is not None and cached.retry_after and cached.retry_after > _now():
        return DeliveredPictogram(cached.svg_markup, cached.state, cached.etag), False
    placeholder = await _placeholder(session, _placeholder_initial(term))
    row = await _save(session, key, svg=placeholder.svg, state="pending", etag=placeholder.etag,
                      placeholder_initial=_placeholder_initial(term), placeholder_revision=2,
                      retry_after=_now() + timedelta(minutes=2))
    return DeliveredPictogram(row.svg_markup, row.state, row.etag), True


async def resolve_shopping_pictogram(session, title: str, *, force: bool = False) -> DeliveredPictogram:
    """Resolve one shopping title without persisting or exposing it as catalogue data."""
    term = _normalise_public_term(title)
    if term is None:
        return await _generic_placeholder(session)
    key = _cache_key(term)
    cached = await session.scalar(select(PictogramDeliveryCache).where(PictogramDeliveryCache.cache_key == key))
    if cached is not None and not force and (cached.state == "available" or (cached.retry_after and cached.retry_after > _now())):
        return DeliveredPictogram(cached.svg_markup, cached.state, cached.etag)
    if not settings.PICTOGRAMICL_API_KEY.strip():
        return await _generic_placeholder(session)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=115.0, write=10.0, pool=5.0), follow_redirects=False) as client:
            response = await client.get(
                f"{settings.PICTOGRAMICL_URL.rstrip('/')}/v1/pictograms/{quote(term, safe='')}",
                params={"style": settings.PICTOGRAMICL_STYLE},
                headers={"X-Api-Key": settings.PICTOGRAMICL_API_KEY},
            )
            response.raise_for_status()
            payload = response.json()
            success = payload.get("success") is True
            asset_url = payload.get("asset_url") if success else payload.get("placeholder_url")
            if not isinstance(asset_url, str):
                raise ValueError("Pictogramicl response has no asset URL")
            svg, etag = await _asset(client, asset_url)
            retry_seconds = payload.get("retry_after") or response.headers.get("retry-after") or _FALLBACK_RETRY.total_seconds()
            try:
                retry_at = None if success else _now() + timedelta(seconds=max(1, min(int(retry_seconds), 86_400)))
            except (TypeError, ValueError):
                retry_at = _now() + _FALLBACK_RETRY
            row = await _save(session, key, svg=svg, state="available" if success else str(payload.get("state", "unavailable")),
                              etag=etag, concept_key=payload.get("concept_key") if success else None,
                              revision=payload.get("revision") if success else None,
                              placeholder_initial=payload.get("placeholder_initial"),
                              placeholder_revision=payload.get("placeholder_revision"), retry_after=retry_at)
            return DeliveredPictogram(row.svg_markup, row.state, row.etag)
    except (httpx.HTTPError, ValueError, UnicodeDecodeError):
        # A previously cached service fallback remains usable; no local SVG is generated.
        if cached is not None:
            return DeliveredPictogram(cached.svg_markup, cached.state, cached.etag)
        return await _generic_placeholder(session)


async def refresh_shopping_pictogram(title: str) -> None:
    """Run the potentially slow service lookup after the initial response."""
    from app.database import async_session
    async with async_session() as session:
        await resolve_shopping_pictogram(session, title, force=True)
        await session.commit()
