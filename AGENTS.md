# FitTrack agent guide

## Product intent

FitTrack is a private, household fitness tracker.  It is moving from a
single-user prototype to a multi-account application: each approved Google
account owns and can access only its own data.  A shared ESP32/Renpho scale is
an untrusted device source; it must never select or impersonate an account.

The authoritative implementation specification is
[`docs/specs/multi-account-scale-and-body-composition.md`](docs/specs/multi-account-scale-and-body-composition.md).
Read it before changing authentication, user-scoped data, the scale bridge, or
body-composition code.

## Repository map

| Area | Location | Responsibility |
| --- | --- | --- |
| API and persistence | `backend/app/` | FastAPI, SQLAlchemy models, Alembic migrations |
| API tests | `backend/tests/` | Contract and regression tests |
| Frontend | `frontend/src/` | SvelteKit UI, API client and IndexedDB sync |
| ESP32 scale bridge | `esp32-scale-bridge/` | BLE parsing and authenticated raw measurement delivery |
| Reverse proxy | `infra/caddy/Caddyfile` | Public routing; never expose secrets |
| Deployment | `docker-compose.yml` | Containers and runtime environment |

## Non-negotiable invariants

1. The server derives the authenticated account from the verified session.  A
   browser request must never choose a `user_id`, account ID, or Google token
   owner in its body, query string, or route.
2. Every account-owned query and mutation is scoped to that account.  No
   literal `"luis"`, module-level `USER_ID`, or default account may remain in
   production request handling.
3. The ESP can submit only a raw scale event.  It sends no personal profile
   data and cannot assign an event to a person.  Assignment happens server-side
   and must be auditable and reversible.
4. Preserve raw scale events.  A daily summary is a projection, never the only
   record of a measurement.
5. Do not show body-composition values unless a real impedance value was
   received.  BMI is allowed with weight and height alone.  Never call a BIA
   estimate “bone density” or make medical claims.
6. Never log OAuth tokens, session cookies, API keys, ESP Wi-Fi credentials, or
   full health payloads.  Do not read or commit `.env` or generated ESP
   `config.h`.

## Working rules

- Inspect `git status --short` first.  This repository may contain user work;
  preserve unrelated changes.
- Use Alembic for persistent-schema changes.  Do not rely on
  `Base.metadata.create_all()` for migrations or edit existing migration files.
- Make backwards-compatible API changes deliberately.  If a temporary legacy
  endpoint is needed, document its removal condition in the PR/change notes.
- Keep profile data out of firmware and out of frontend-controlled identity
  fields.  Store birth date, not a mutable age; calculate age at measurement
  time.
- Put business logic in testable backend services, not directly in route
  handlers.  Persist algorithm/version and a profile snapshot with every BIA
  result.
- Prefer small, reviewable commits/work packages.  Do not mix the account
  isolation migration with BIA protocol reverse engineering.

## Definition of done for account-scoped changes

- A request authenticated as account A cannot read, update, or delete account
  B data, including by supplying B identifiers.
- Google OAuth tokens and Google Fit/Calendar data are selected by the current
  account.
- New-account seeding creates only that account’s intended defaults and never
  copies another account’s records.
- Existing `luis` records have an explicit, tested migration target.
- Backend tests cover the isolation case and frontend checks pass.

## Commands

Run commands from the indicated directory.  Do not run deployment commands,
flash the ESP, or modify production environment variables unless specifically
requested.

```bash
# backend
cd backend && pytest -q

# frontend
cd frontend && npm run check && npm run lint:design && npm run build

# ESP firmware (compile only when toolchain is present)
cd esp32-scale-bridge && pio run
```

