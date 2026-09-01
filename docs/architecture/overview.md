# System overview

```text
Google OIDC -> signed browser session -> current account -> scoped ORM/API
Renpho BLE -> ESP32 device key -> Scale v2 -> range assignment -> daily projection
```

| Module | Boundary | Normative source | Verification |
| --- | --- | --- | --- |
| `backend/app/routes/auth.py` | OIDC/session/account creation | multi-account spec §5.1 | backend tests |
| `backend/app/services/ownership.py` | account query/write scope | multi-account spec §4 | authorization tests |
| `backend/app/routes/scale_v2.py` | device ingest and private feed | multi-account spec §5.3–5.4 | scale-v2 contract tests |
| `backend/app/routes/{day_entries,todos,goals,stats}.py` | account-private tracker APIs | multi-account spec §4 | backend contract tests |
| `backend/app/routes/configurable_meals.py` | account-private categories, food, recipes, plans, entries and photo analysis | configurable-meals spec | meal contract and isolation tests |
| `backend/app/routes/{training,vision,google_fit,google_calendar,sync}.py` | account-private training, import, offline-sync and vision APIs | multi-account spec §4–5.1 | backend contract tests |
| `backend/app/models.py` and `backend/alembic/versions/019–033` | ownership schema, meal cutover and one-way legacy migration | multi-account and configurable-meals specs | Alembic head; migration rehearsal |
| `backend/app/seed.py` | explicit starter-data initialization for one account | multi-account spec §5.2 | backend contract tests |
| `frontend/src/lib/{api,auth,db,sync}.ts` | session-aware API, private offline cache and conflict-preserving sync | multi-account spec §4 | Svelte check/build |
| `frontend/src/routes/` and `frontend/src/lib/components/` | account-private tracker presentation | frontend design system | design lint/build |
| `esp32-scale-bridge/src/main.cpp` | raw device transport only | Scale v2 contract | PlatformIO build |
| `esp32-scale-bridge/src/diagnostic.cpp` | manual, credential-free protocol observation | multi-account spec §6 phase D | PlatformIO diagnostic build |
| `infra/caddy/Caddyfile` | public routing with separate device path | multi-account spec §5.4 | scale-sync proxy test |
