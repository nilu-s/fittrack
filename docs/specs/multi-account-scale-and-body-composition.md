# Cronicl: Multi-account, shared scale and body-composition specification

**Status:** approved
**Owner:** Cronicl household
**Last updated:** 2026-08-31

## 1. Intent and outcome

Cronicl becomes a private, two-person application.  Each person signs in with
their own approved Google account and sees only their own fitness, nutrition,
training, integration and scale data.  The shared Renpho scale continues to
send measurements through one ESP32 bridge.  The backend assigns a measurement
to an account using configured, non-overlapping weight ranges; neither the ESP
nor either frontend chooses the account.

The immediate outcome is secure account separation and reliable automatic
weight delivery.  Body composition is a separate, gated capability: it is
available only if the scale protocol supplies genuine BIA impedance data.

## 2. Scope

### In scope

- Google OAuth accounts, restricted to an allow-list maintained in server
  configuration.
- Strict data ownership for all existing account-owned models and integrations.
- A fresh Cronicl baseline schema; no predecessor data is carried forward.
- Shared-scale ingestion with automatic, privacy-preserving weight-range
  assignment and an owner-only removal workflow for wrongly assigned events.
- Per-account body-profile settings and BMI.
- A future-safe data model for BIA results, including reproducibility metadata.

### Out of scope

- Household sharing outside the explicit task/list/project spaces governed by
  `shared-spaces.md`, social features, cross-account dashboards or delegated
  access to private data.
- User-selected account/profile on the ESP32 or in the scale request.
- Guessing body fat, water, muscle, visceral fat, protein or bone mass from
  weight alone.
- Clinical measurements, diagnosis, treatment, risk assessment, osteoporosis
  screening or the term “bone density”.
- Reverse engineering or reproducing Renpho’s proprietary algorithm.  The
  BIA implementation will use a documented, versioned model selected later.

## 3. Facts and constraints

The current ESP32 AABB bridge parses a final BLE frame containing weight.  It
does **not** parse or submit impedance.  Although the current scale endpoint
contains provisional body-composition code, it cannot legitimately calculate
BIA values from the present bridge payload.

Renpho describes its consumer-scale outputs as body-composition data derived
from impedance together with height, age, sex/gender and weight; its own manuals
state that the result is reference-only, not medical advice.

- [Renpho body-composition manual](https://renpho.com/pages/user-manual-body-composition-scale)
- [FDA classification of bioimpedance devices](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpcd/classification.cfm?id=1844)
- [NIAMS: DXA and bone mineral density](https://www.niams.nih.gov/health-topics/osteoporosis/diagnosis-treatment-and-steps-to-take)

## 4. Product rules

### Accounts and access

1. A Cronicl account is created on the first successful Google login from an
   allowed Google identity.  The persistent external identity is the OIDC
   `sub`, not email; email is display/contact data and may change.
2. The session carries the internal `account_id`, OIDC `sub` and expiry.  The
   backend verifies it on every browser request.
3. Any request for account-owned data uses `account_id` obtained from the
   dependency.  The API neither accepts nor returns a client-controlled owner
   field for mutation requests.
4. An account can only view, edit, export or delete its own data.  This applies
   to day entries, meals, templates, dishes, todos, training units, rotations,
   exercises, progress, goals, photos, sync log, Google tokens, Google Fit,
   Calendar imports and scale events.
5. Cronicl starts from an empty database. There is no compatibility account,
   legacy user identifier or data backfill path.

### Shared scale

1. The ESP authenticates with a device credential and sends raw data only.
2. The server validates and attempts assignment before persistence. An event
   matching no active range (including a visitor's measurement) is discarded:
   its raw payload and weight are not persisted, projected or shown to either
   account. Accepted events are either `assigned` or later `rejected` by their
   assigned account; accepted raw events remain immutable and auditable.
3. The initial household configuration is:

   | Account | Auto-assignment range |
   | --- | --- |
   | Friend | 45.0–85.0 kg |
   | Owner | 90.0–145.0 kg |

   Ranges must not overlap. The 85.0–90.0 kg gap and all values outside active
   ranges are discarded before persistence.
4. Auto-assignment is a server decision with `assignment_method = 'weight_range'`
   and a confidence value of `1.0` only when exactly one active range matches.
5. A user may remove only an event currently assigned to their own account.
   Removal changes its status to `rejected` and records an audit reason; it
   never deletes or transfers the raw event. There is no claim, reassignment,
   household-admin or cross-account recovery flow in this cutover.
6. A duplicate device event must be idempotent and must not create another
   daily measurement or overwrite a later correction.
7. Each account's range follows its accepted-weight baseline slowly: once per
   UTC day, calculate the target as the rolling median of the last 28 accepted,
   non-rejected measurements and move the stored baseline toward it by at most
   2.0 kg in any rolling seven-day period. Translate that account's configured
   lower and upper offsets by the same amount; never permit active ranges to
   overlap. This accommodates sustained weight change without treating ordinary
   daily fluctuation as a new identity.

### Body profile and health language

Each account owns its body profile:

- `birth_date` (required for BIA; age calculated at measurement time)
- `height_cm` (required for BMI and BIA)
- `calculation_sex` (required only by the selected BIA formula; explain it is a
  formula input, not an identity label)
- `athlete_mode` (disabled initially; add only when supported by the selected
  algorithm)

Weight and BMI are measurements/calculations.  BIA-derived items are always
labelled **“Schätzung”** in German UI and shown as trends.  Use “geschätzte
Knochenmasse”, never “Knochendichte”.  Round weight/mass to 0.1 kg and
percentages to 0.1%; do not imply false precision.  Display a concise notice:

> Körperzusammensetzung ist eine BIA-Schätzung zur Verlaufskontrolle und keine
> medizinische Messung oder Diagnose.

## 5. Target architecture

```text
Google OAuth -> verified session -> current account -> account-scoped API/data

Renpho BLE -> ESP32 bridge -> raw scale event -> assignment service
                                                -> immutable event record
                                                -> daily measurement projection
                                                -> optional BIA calculation service
```

### 5.1 Authentication

- Add `accounts` as the canonical owner table.  Do not use raw email addresses
  as foreign keys.
- Google callback validates the OIDC identity and allow-list, upserts the
  account by `google_subject`, then upserts that account’s Google token.
- Replace singular `ALLOWED_EMAIL` with `ALLOWED_GOOGLE_EMAILS`, a comma-
  separated allow-list.  Empty allow-lists are not permitted in production.
- CLI/device credentials must authenticate a device principal only; they must
  not resolve to any account.
- `GET /api/auth/me` returns a minimal account DTO: ID, display name and email.

### 5.2 Clean-slate baseline

Cronicl has one baseline migration that creates the current schema against
an empty database. Every account-owned table uses a non-null UUID `account_id`
from its first version; no browser-visible compatibility owner or `user_id`
column exists. Seed data runs only when a new account is explicitly initialized,
never globally at application startup.

### 5.3 Scale storage

Create immutable scale events before updating daily summaries.

`scale_measurements`

| Field | Meaning |
| --- | --- |
| `id` UUID | Internal event ID |
| `device_id` | Registered ESP bridge ID |
| `device_event_id` | Idempotency key from bridge; unique with device ID |
| `measured_at` | UTC time at measurement source; nullable only for legacy events |
| `received_at` | Server UTC timestamp |
| `weight_kg` | Raw stable scale weight |
| `impedance_ohm` | Nullable raw impedance; absent means weight-only |
| `raw_payload` JSONB | Original accepted payload, excluding credentials |
| `status` | assigned / rejected (unmatched events are not persisted) |
| `assigned_account_id` | Nullable account FK |
| `assignment_method` | weight_range / none |
| `assignment_confidence` | 0..1; auditable decision signal |
| `assignment_reason` | Human-readable audit context |

`body_composition_results`

| Field | Meaning |
| --- | --- |
| `measurement_id` | FK to `scale_measurements` |
| `algorithm_id`, `algorithm_version` | Exact documented calculation used |
| `profile_snapshot` JSONB | Height, age-at-measurement and formula inputs |
| `input_snapshot` JSONB | Weight, impedance/frequency and device metadata |
| metrics | Explicit nullable fields or versioned JSONB for estimates |
| `warnings` JSONB | Missing data / out-of-range / reference-only warning |
| `created_at` | Calculation time |

Use a unique constraint on `(measurement_id, algorithm_id, algorithm_version)`.
Old results remain valid historical outputs when a new algorithm is introduced.

`day_entries` remains a user-facing daily projection during the transition.  A
deterministic rule chooses the latest valid assigned event for that local day.
Manual weight entries remain distinct with `weight_source = 'manual'` and are
never overwritten silently by an older device event.

### 5.4 Scale API v2

The device endpoint is machine-to-machine and separate from browser account
APIs.

`POST /api/scale-sync/v2`

```json
{
  "device_id": "esp32-renpho-aabb-bridge",
  "device_event_id": "uuid-or-monotonic-event-id",
  "measured_at": "2026-08-31T07:15:02Z",
  "weight_kg": 115.2,
  "impedance_ohm": null,
  "protocol": "renpho-aabb",
  "protocol_version": 1
}
```

- Authentication: a dedicated device credential in a header; rate-limit by
  device.  Reject unknown device IDs and payloads outside 0.5–300 kg.
- Response: event ID and status for an accepted event, or `discarded` for an
  unmatched event; never include account identity or health profile data.
- The bridge must retry the exact same event ID after a network failure.

Browser endpoints:

- `GET /api/scale-measurements?from=&to=` — current account only.
- `POST /api/scale-measurements/{id}/reject` — hide a wrongly assigned event
  from the current account while preserving the audit record. It is allowed
  only for the account currently assigned to the event.
- `GET/PUT /api/account/body-profile` — current account only.

Discarded events have no normal or administrative feed. Rejected events are
hidden from the ordinary account feed and retained only as an audit record.

## 6. Phased implementation plan

### Phase A — account isolation (blocking prerequisite)

1. Establish one clean-slate baseline with account models, Google subject
   handling, allow-list configuration and account-scoped Google tokens.
2. Convert all routes and service queries to `current_account`.
3. Remove owner fields from browser-write schemas and frontend requests.
4. Make seed initialization explicit per account.

**Exit criterion:** two browser sessions cannot observe or modify each other’s
records through any API route or integration.

### Phase B — shared-scale ingestion and assignment

1. Introduce device registration and `scale_measurements` migration.
2. Implement v2 ingestion and idempotency; persist the raw payload only after
   a unique automatic assignment succeeds.
3. Implement non-overlapping, baseline-adaptive range validation and the
   automatic assignment service.
4. Project only assigned events into the matching account’s daily view.
5. Add the owner-only removal UX and event audit information.
6. Remove personal fields from ESP firmware configuration and payload.

**Exit criterion:** a 63 kg event appears only for the friend account, a 115 kg
event only for the owner account; 87 kg appears for neither account; retrying
an event creates one record.

### Phase C — body profile and weight-only metrics

1. Add account body-profile settings and validation.
2. Calculate BMI from a confirmed assigned weight and profile height.
3. Add account settings UI and a private scale/trend view.
4. Add reference-only copy and data export/delete behavior for the account.

**Exit criterion:** profile changes do not alter historical measurements;
historical BMI calculation inputs are traceable.

### Phase D — BIA discovery gate

1. Capture and document complete BLE manufacturer frames for a barefoot scale
   measurement, without logging credentials or personal records.
2. Establish whether impedance exists, at which frequency/units, and whether it
   is stable and attributable to the final weight event.
3. If no impedance is available, close this phase with a documented
   **weight-only** decision.  Do not implement synthetic BIA values.
4. If impedance exists, select and document an appropriate algorithm; define
   population limits, range checks, units, inputs, validation and display text.

### Phase E — BIA estimates (only after Phase D approval)

1. Store impedance and device/protocol metadata in raw events.
2. Implement a pure, tested calculation service with algorithm versioning and
   snapshots.
3. Store results separately, apply warning/range rules, and show estimates only
   in the owning account.
4. Initially expose body fat, fat mass, fat-free mass and water.  Add further
   metrics only with a defined formula; bone mass remains optional and clearly
   non-diagnostic.

## 7. Acceptance tests

### Security and ownership

- Login as A and B.  For every resource family, B receives no A data.
- B cannot alter A data by ID, query parameter, request body or offline-sync
  payload.
- OAuth callback stores each token under the matching account.
- Disconnection, Google Fit import and Calendar import affect only the current
  account.

### Scale

- Valid 63.0 kg and 115.0 kg events receive the intended account IDs.
- Boundary values, gaps, overlap attempts, unknown devices, malformed times,
  out-of-range weights and duplicate event IDs have deterministic responses.
- An owner removal is retained after ESP retry and after later range-baseline
  changes.
- An unmatched event is discarded without persisting its health payload and
  cannot leak account names or measurements in its device response.

### Body metrics

- Weight without impedance produces weight and BMI only.
- No result can call itself bone density or a medical result.
- BIA calculation result contains exact profile/input/algorithm snapshots.
- Invalid profile or impedance produces an explanatory warning, never a
  fabricated value.

### Regression checks

```bash
cd backend && pytest -q
cd frontend && npm run check && npm run lint:design && npm run build
```

## 8. Implementation decisions still intentionally deferred

- Which Google addresses belong in the production allow-list.
- Whether an administrative recovery workflow is necessary for cross-account
  measurement transfers.
- Whether the Renpho hardware actually exposes usable impedance in the current
  broadcast protocol, and which documented BIA algorithm to adopt if it does.
