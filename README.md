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

The ESP32 bridge posts measurements to `POST /api/scale-sync`.  This route is
intentionally excluded from Caddy's browser basic authentication because the
ESP32 authenticates with `X-FitTrack-CLI-Key`; the API rejects requests without
the value configured as `FITTRACK_CLI_KEY`.

For the device setup, copy
[`esp32-scale-bridge/src/config.h.example`](esp32-scale-bridge/src/config.h.example)
to `config.h`, set `API_KEY` to the server's `FITTRACK_CLI_KEY`, then build and
flash the firmware as described in
[`esp32-scale-bridge/README.md`](esp32-scale-bridge/README.md).  Do not commit
the generated `config.h`.
