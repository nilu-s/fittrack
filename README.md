# FitTrack PWA

Offline-first PWA für Fitness-, Ernährungs- und To-Do-Tracking.

## Stack
- **Frontend:** SvelteKit PWA + Dexie.js (IndexedDB)
- **Backend:** FastAPI + PostgreSQL 16
- **Vision:** Ollama (kimi-k3)
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