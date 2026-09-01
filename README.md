# Chronickel

Offline-first PWA für Fitness-, Ernährungs- und To-Do-Tracking.

## Stack
- **Frontend:** SvelteKit PWA + Dexie.js (IndexedDB)
- **Backend:** FastAPI + PostgreSQL 16
- **Vision:** vision-proxy
- **Infra:** Docker Compose + Caddy reverse proxy

## Development
```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
# Backend: http://localhost:8000/api/health
# Frontend: http://localhost:3000
```

Run `cd backend && alembic upgrade head` against a fresh local database. The
developer Compose file does not mount production credentials or expose Caddy.

## Production
- API: `${APP_PUBLIC_ORIGIN}/api`
- Web: `${APP_PUBLIC_ORIGIN}`

## ESP32 scale bridge

The ESP32 bridge posts raw measurements to `POST /api/scale-sync/v2`. This
device-only route is excluded from browser authentication and instead requires
its registered `X-App-Device-Key`; it cannot select an account.

For the device setup, copy
[`esp32-scale-bridge/src/config.h.example`](esp32-scale-bridge/src/config.h.example)
to `config.h`, set `DEVICE_KEY` to the registered device credential, then build and
flash the firmware as described in
[`esp32-scale-bridge/README.md`](esp32-scale-bridge/README.md).  Do not commit
the generated `config.h`.

## Datenbankstart

Chronickel wird mit einer leeren Datenbank und der einzelnen Baseline-Migration
gestartet. Kontodaten entstehen erst nach der Google-Anmeldung; Browserdaten
werden bei einem Konto-Wechsel im selben Browserprofil gelöscht.
