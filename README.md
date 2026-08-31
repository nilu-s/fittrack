# FitTrack PWA

Offline-first PWA für Fitness-, Ernährungs- und To-Do-Tracking.

## Stack
- **Frontend:** SvelteKit PWA + Dexie.js (IndexedDB)
- **Backend:** FastAPI + PostgreSQL 16
- **Vision:** vision-proxy
- **Infra:** Docker Compose + Caddy reverse proxy

## Development
```bash
docker compose up -d
# Backend: http://localhost:8000/api/health
# Frontend: http://localhost:3000
```

## Production
- API: `https://fittrack.49.12.225.84.sslip.io/api`
- Web: `https://fittrack.49.12.225.84.sslip.io`

## ESP32 scale bridge

The ESP32 bridge posts raw measurements to `POST /api/scale-sync/v2`. This
device-only route is excluded from browser authentication and instead requires
its registered `X-FitTrack-Device-Key`; it cannot select an account.

For the device setup, copy
[`esp32-scale-bridge/src/config.h.example`](esp32-scale-bridge/src/config.h.example)
to `config.h`, set `DEVICE_KEY` to the registered device credential, then build and
flash the firmware as described in
[`esp32-scale-bridge/README.md`](esp32-scale-bridge/README.md).  Do not commit
the generated `config.h`.

## Multi-account release

The account and shared-scale cutover is an Alembic maintenance-window release.
Use the checked-in [cutover runbook](docs/runbooks/multi-account-cutover.md): it
requires a verified backup, an allow-list, and a uniquely resolved legacy
owner before finalizing ownership. Browser offline data is cleared whenever a
different account signs in on the same browser profile.
