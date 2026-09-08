"""Visible APNs/FCM alerts. Provider tokens/payloads must never be logged."""
import asyncio
from pathlib import Path

import httpx
from jose import jwt

from app.config import settings
from app.services.native_auth import utcnow


class PushUnavailable(Exception):
    pass


class InvalidPushToken(Exception):
    pass


def fcm_access_token():
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    credentials = service_account.Credentials.from_service_account_file(
        settings.FCM_CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/firebase.messaging"])
    credentials.refresh(Request())
    return credentials.token


async def send_alert(device, event, todo, client=None):
    if not settings.TRAVEL_PUSH_ENABLED or not device.push_token:
        raise PushUnavailable()
    messages = {"lead": "Deine Anreise steht bevor. Prüfe die Abfahrt und starte bei Bedarf die Begleitung.",
                "leave": "Es ist Zeit, deine geplante Abfahrt zu prüfen.",
                "change": "Die empfohlene Abfahrtszeit hat sich geändert. Öffne die aktuelle Anreise."}
    data = {"todo_id": str(todo.id), "date": str(todo.due_date), "event_id": str(event.id), "expires_at": event.expires_at.isoformat()}
    now = utcnow()
    ttl = max(0, int((event.expires_at - now).total_seconds()))
    if ttl == 0:
        raise PushUnavailable()
    if device.platform == "ios":
        if not all((settings.APNS_KEY_FILE, settings.APNS_KEY_ID, settings.APNS_TEAM_ID)):
            raise PushUnavailable()
        token = jwt.encode({"iss": settings.APNS_TEAM_ID, "iat": int(now.timestamp())},
            Path(settings.APNS_KEY_FILE).read_text(), algorithm="ES256", headers={"kid": settings.APNS_KEY_ID})
        host = "api.sandbox.push.apple.com" if settings.APNS_SANDBOX else "api.push.apple.com"
        url = f"https://{host}/3/device/{device.push_token}"
        headers = {"authorization": f"bearer {token}", "apns-topic": settings.APNS_TOPIC,
            "apns-push-type": "alert", "apns-priority": "10", "apns-expiration": str(int(event.expires_at.timestamp())),
            "apns-collapse-id": str(event.watch_id), "apns-id": str(event.id)}
        payload = {"aps": {"alert": {"title": "Cronicl · Anreise", "body": messages[event.kind]}, "sound": "default"}, **data}
    else:
        if not settings.FCM_PROJECT_ID or not settings.FCM_CREDENTIALS_FILE:
            raise PushUnavailable()
        token = await asyncio.to_thread(fcm_access_token)
        url = f"https://fcm.googleapis.com/v1/projects/{settings.FCM_PROJECT_ID}/messages:send"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"message": {"token": device.push_token, "data": data,
            "notification": {"title": "Cronicl · Anreise", "body": messages[event.kind]},
            "android": {"priority": "high", "ttl": f"{ttl}s", "collapse_key": str(event.watch_id),
                "notification": {"tag": str(event.watch_id), "channel_id": "travel"}}}}
    owned = client is None
    http = client or httpx.AsyncClient(http2=True, timeout=15)
    try:
        response = await http.post(url, headers=headers, json=payload)
        if device.platform == "ios" and response.status_code in (400, 410):
            if response.json().get("reason") in ("BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"):
                raise InvalidPushToken()
        if device.platform == "android" and response.status_code == 404:
            raise InvalidPushToken()
        if response.status_code not in (200, 201):
            raise PushUnavailable()
    finally:
        if owned:
            await http.aclose()
