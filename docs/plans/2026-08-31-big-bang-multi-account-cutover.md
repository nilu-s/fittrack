# FitTrack Big-Bang Multi-Account Cutover

**Status:** superseded (historical) — the implemented controls are maintained in `AGENTS.md`, specs, contracts and CI.

**Authoritative specification:**
[`../specs/multi-account-scale-and-body-composition.md`](../specs/multi-account-scale-and-body-composition.md)

## Authority and current-state baseline

Before implementation, review and commit the root `AGENTS.md` and the
authoritative specification above.  They are the only current normative
product rules for account ownership, shared-scale trust boundaries and BIA.

The authority order is:

1. approved product specification;
2. approved ADR;
3. versioned API/event contract;
4. this execution plan;
5. README and historical analysis.

The older `.hermes/plans/*` files are implementation history, not normative
requirements.  In particular, their single-user `luis` assumptions are
superseded.  `UI-ANALYSE-UND-PLAN.md` must be archived or marked historical if
it conflicts with `frontend/docs/design-system.md`.  Operational READMEs are
updated only in the same change that implements the documented behaviour.

## Outcome

Replace the single-user application in one release with the account-owned
application described by the approved specification.  The released system has
no browser-controlled owner fields, no runtime schema creation, no global
seed data, and no legacy scale endpoint that writes directly to `luis`.

The pre-existing `luis` records are migrated exactly once to the account that
first authenticates as the configured legacy-owner email.  The configuration
value is deployment-only (`LEGACY_OWNER_EMAIL`); persistent identity is the
verified Google OIDC `sub`, never an email address.

## Cutover rules

- This is a maintenance-window release with a database backup and a tested
  rollback procedure.
- The migration aborts without changing legacy ownership if exactly one
  eligible owner account cannot be resolved.
- Browser APIs accept no `user_id` or `account_id` in bodies, routes or query
  parameters for ownership selection.
- ESP firmware sends a device event only.  It sends no profile or account data.
- `POST /api/scale-sync` is removed; only `/api/scale-sync/v2` is deployed.
- Body-composition estimates are not deployed in this cutover.  Weight-only
  measurements and BMI are the maximum supported result.

## Work packages

### WP0 — freeze and release controls

1. Review and commit the current Scale/Caddy/docs changes as an explicit
   pre-cutover baseline; do not fold unrelated UI work into the migration.
2. Add `scripts/check` and CI jobs for backend, frontend and firmware builds.
3. Add a migration rehearsal fixture containing legacy `luis` rows and two
   allowed accounts.
4. Document backup, maintenance, migration and rollback commands in a runbook.
5. Create the documentation registry, system/data-flow overview, authorization
   matrix and ADRs for identity, device trust, raw-event projection and BIA
   evidence gating before application code is changed.

### WP1 — identity and ownership model

1. Add `accounts` keyed by UUID, with unique `google_subject`, mutable display
   email, display name and timestamps.
2. Add nullable UUID `account_id` to every account-owned table in a new
   Alembic revision; do not edit historical revisions.
3. Add a migration preflight that resolves `LEGACY_OWNER_EMAIL` to exactly one
   account and backfills every legacy `user_id = 'luis'` row.
4. Audit for null/orphan ownership, then make `account_id` non-null and update
   unique constraints.
5. Remove legacy `user_id` defaults and browser schemas only after the audit
   and route conversion pass.

### WP2 — authentication and all browser APIs

1. Validate Google ID tokens and create/upsert accounts by OIDC `sub` from an
   explicit email allow-list.
2. Put `account_id`, `sub` and expiry in the signed session.  Implement one
   `current_account` dependency; device credentials cannot use it.
3. Convert every route family, Google token query, import, seed and sync path
   to receive the account through that dependency.
4. Make account initialization explicit and idempotent for a newly created
   account; remove startup seeding and `Base.metadata.create_all()`.
5. Add an authorization matrix and A-versus-B API regression suite for every
   resource family.

### WP3 — shared-scale v2

1. Add registered devices, immutable `scale_measurements`, unique
   `(device_id, device_event_id)`, assignment audit fields and non-overlapping
   account weight ranges.
2. Implement device-only `POST /api/scale-sync/v2`, including payload/range
   validation, idempotent retry and response without account data.
3. Implement a server-side assignment service and deterministic day-entry
   projection for assigned events only.
4. Implement account-scoped measurement read and owner-only removal APIs, with
   the corresponding frontend view; discard unmatched visitor measurements
   before persistence.
5. Remove device profile fields from firmware config and payload; retain
   protocol fixtures without credentials or personal data.

### WP4 — frontend and operations cutover

1. Remove owner fields from TypeScript types, IndexedDB sync payloads and API
   client methods.
2. Adapt login, account display, integrations and scale/history UI to `/auth/me`
   and account-scoped contracts.
3. Update README and ESP runbook in the same change as the deployed behavior.
4. Build firmware only in CI; flashing and live BLE tests remain a documented
   manual production-smoke step.

### WP5 — repository finish and removal audit

1. Move deliberately retained visual evidence from the repository root to
   `docs/evidence/`; ignore ephemeral captures and generated output.
2. Remove unused dependencies, duplicate helpers, stale compatibility paths and
   obsolete Scale-v1 documentation in the same cutover.
3. Produce the module index and verify that every source area has one owning
   boundary, one normative source and one primary verification path.
4. Enforce protected review for specifications, ADRs and contracts after the
   target branch and CI checks exist.

## Mandatory release gates

- Fresh database reaches Alembic `head`; legacy fixture migrates to the
  designated account and no account-owned orphan remains.
- Account A cannot read, create, modify or delete account B data through any
  browser route, supplied identifier or IndexedDB replay.
- Google Fit, Calendar and OAuth tokens stay account-scoped.
- Device tests: 63 kg is assigned only to the friend, 115 kg only to the owner,
  87 kg to neither; retry creates one raw event.
- No body-composition fields are returned for weight-only device payloads.
- `pytest -q`, frontend check/design-lint/build and both firmware environments
  compile successfully.

## Agent-optimized repository contract

The target is a small product repository that multiple LLMs and human
contributors can navigate without a second, agent-only documentation system.
The repository must favour one authoritative artifact per concern over broad
commenting, generated summaries or duplicate architecture documents.

### Required, minimal control plane

| Artifact | Single responsibility |
| --- | --- |
| `AGENTS.md` | Global authority order, invariants, command matrix and stop conditions. |
| Area `AGENTS.md` files | Only rules that differ in `backend/`, `frontend/`, `esp32-scale-bridge/` and `infra/`. |
| `docs/specs/README.md` | Registry of normative specs: status, scope, owner, last review and successor. |
| `docs/architecture/overview.md` | One system/data-flow diagram and a module index. |
| `docs/architecture/authorization-matrix.md` | Resource/principal/action/enforcement/test mapping. |
| `docs/contracts/` | Versioned OpenAPI snapshot plus Scale-v2 payload fixtures. |
| `docs/adr/` | Only durable choices that change trust, data ownership, protocol or deployment boundaries. |
| `scripts/check` | One local deterministic validation entry point; CI invokes equivalent jobs. |

No catch-all wiki, generated code catalogue, duplicated README content or
per-feature agent prompt files are created unless a future requirement cannot
be represented by the control plane above.

### Traceability without comment noise

1. A module must have one clear responsibility and a name that reflects its
   domain.  Routes translate HTTP only; services own rules; migrations own
   schema/data transitions; firmware owns protocol transport only.
2. Each public route, asynchronous job, migration, device event and shared
   service has an entry in the module index.  An entry links to its owning
   spec/ADR, contract where relevant, and primary test file.
3. Inline comments explain only non-obvious safety, protocol, performance or
   compatibility decisions.  Comments that restate code are removed.
4. Every non-trivial branch must be covered by a named acceptance test or be
   linked from the module index to a justified invariant.  Coverage percentage
   alone is not an acceptance criterion.
5. Dead paths, compatibility shims, unused dependencies and duplicate helpers
   are removed in the same cutover.  CI contains a targeted unused-import/
   dead-code check only after its tool configuration has no false-positive
   baseline.

### Standard for cross-LLM work

Every implementation task names: objective, in/out-of-scope files, governing
spec/ADR/contract, acceptance tests, allowed side effects and stop conditions.
Subagents are used only for independent read-only inventory, protocol research
or test review; concurrent agents do not edit the same domain.  Deterministic
tests and contracts are the merge gate.  A later Codex review workflow is
read-only and checks only high-risk invariants; it never deploys or mutates
production.

### Planned generic role skills

No role skills are created by this plan.  After the repository control plane
is stable, create four separate, project-agnostic skills rather than one
combined FitTrack skill:

| Skill | Input | Output | Prohibited action |
| --- | --- | --- | --- |
| `spec-test-author` | Approved spec and existing contracts | Red acceptance/contract tests and fixtures | Production-code changes |
| `blind-implementer` | Approved spec, module index, contracts and red tests | Minimal conforming implementation | Editing specs, contracts or test intent |
| `independent-code-reviewer` | Approved spec, diff and test results | Prioritized review findings | Code changes or author-chat access |
| `release-verifier` | Release checklist and immutable candidate | Reproducible validation record | Product-code or production changes |

The skills remain generic.  Repository-specific rules remain in the current
repository's specs, contracts and `AGENTS.md` files.  The implementer receives
only the declared inputs above; research notes, suggested algorithms, author
reasoning and reviewer conversation are excluded.  This is a process boundary
implemented with separate tasks and one-way artifacts, not a claim of
cryptographic information hiding from a fully readable repository.

### Spec lock and red/green protocol

1. An approved spec is immutable for an implementation task.  An agent may
   read and link it, but may not edit it to make generated code appear correct.
   A required product decision is a separate spec-revision task, reviewed and
   approved before a new implementation task begins.
2. Before production code changes, create contract/acceptance tests derived
   from the approved spec.  They must fail against the current implementation
   for the intended missing behaviour (red) and pass only after the minimum
   conforming implementation (green).
3. Not every prose sentence becomes a test.  Test executable commitments:
   authorization, data ownership, API/event schema, idempotency, validation,
   projection, migration and user-visible health-language gates.  Keep design
   rationale and non-executable decisions in specs/ADRs.
4. CI rejects an implementation PR that changes an approved spec and its
   implementation in the same task, unless the PR is explicitly labelled and
   reviewed as a spec revision.  It also rejects a contract change without its
   updated fixture/OpenAPI artifact and tests.
5. Repository permissions reinforce the process: branch protection requires
   review for `docs/specs/**`, `docs/adr/**` and `docs/contracts/**`; code
   generation runs with read-only access to these files.  Local filesystem
   permissions are not used as the authority because they are easy to bypass
   and make legitimate spec revisions cumbersome.

### Completion condition for repository structure

- The root contains only product entry points and deliberately versioned
  artifacts; audit screenshots and ephemeral output live in `docs/evidence/`
  or are ignored.
- Every source directory has an index entry and a single owning boundary.
- Each index entry points to one normative source and one verification path.
- `rg` finds no legacy owner model, obsolete Scale-v1 contract or unused
  compatibility path after cutover.
- A new agent can locate the governing spec, owning module and validation
  command for a change without reading unrelated product code.

## Deployment inputs and stop conditions

The migration runner needs a production-only allow-list and
`LEGACY_OWNER_EMAIL`.  The nominated email is provided out of band and must
complete an allowed Google login before the migration preflight.  If it does
not resolve to exactly one account, the cutover stops before data migration.

No production secrets, session cookies, API keys, Wi-Fi details or raw health
payloads belong in this plan or in Git.

## Research basis

- Google OIDC `sub` is the durable identity key; email is mutable:
  <https://developers.google.com/identity/openid-connect/reference>
- Server-side, object-level authorization and regression checks address API
  ownership risks: <https://owasp.org/www-project-api-security/>.
- FastAPI supports router-level dependencies and dependency overrides for the
  account-isolation test harness:
  <https://fastapi.tiangolo.com/tutorial/bigger-applications/> and
  <https://fastapi.tiangolo.com/advanced/testing-dependencies/>.
- SQLAlchemy request-scoped sessions and Alembic's versioned migrations guide
  the persistence lifecycle:
  <https://docs.sqlalchemy.org/en/20/orm/session_basics.html> and
  <https://alembic.sqlalchemy.org/en/latest/cookbook.html>.
- SvelteKit project boundaries, PlatformIO tests/CI and GitHub Actions release
  checks inform the repository gates:
  <https://svelte.dev/docs/kit/project-structure>,
  <https://docs.platformio.org/en/stable/advanced/unit-testing/runner.html>,
  <https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow>.
- Codex `AGENTS.md`, skills and independent subagent boundaries inform the
  agent workflow:
  <https://learn.chatgpt.com/docs/agent-configuration/agents-md>,
  <https://learn.chatgpt.com/docs/agent-configuration/subagents> and
  <https://learn.chatgpt.com/docs/build-skills>.
