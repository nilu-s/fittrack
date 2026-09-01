---
name: fittrack-artifact-lifecycle
description: Keep FitTrack specs, ADRs, contracts, plans, and evidence relevant through change-triggered review, traceability, and retirement. Use when a change may invalidate an existing repository artifact or when reviewing documentation health; do not use for ordinary code changes with no artifact touchpoint.
---

# FitTrack Artifact Lifecycle

Keep one authoritative artifact per concern. Do not preserve documents merely
because they once existed, and do not create duplicate summaries to compensate
for an unclear source of truth.

Start at `docs/specs/README.md`. Treat it as the registry of normative specs.
Authority is: approved spec, then ADR, then versioned contract, then plan; a
README, evidence file, or historical plan never overrides a higher source.

## When to revalidate

Revalidate only artifacts touched by evidence, not by elapsed time. A
revalidation is required before merge when a change affects an artifact's:

- owned source path, public route, event/API contract, schema or migration;
- trust, authorization, identity, privacy, health-language, or device boundary;
- declared compatibility shim, feature removal, external integration, or user
  flow; or
- mapped verification failing, missing, or contradicting the artifact.

Also revalidate when a new approved source conflicts with it. A formatting-only
or mechanically equivalent refactor is not a touchpoint unless it changes a
declared path or verification mapping.

## Revalidation outcome

For each touched artifact, classify it with evidence:

- **confirmed** — scope and commitments still match code and verification;
- **revise** — the product decision remains valid but the artifact needs an
  approved change before implementation continues;
- **supersede** — a replacement is authoritative; link predecessor and
  successor in the registry;
- **retire** — no longer governs a live behavior and has no required audit or
  operational value; remove it in the same scoped change.

Do not leave a document in an ambiguous "old but maybe useful" state. Historical
records that must remain for audit or migration context are marked
`superseded` with a successor or `retired (historical)` with a short retention
reason; they are never discovered as active instructions.

## Testable commitments

Separate each artifact into executable commitments and rationale. Every
executable commitment needs a named verification path: an acceptance,
integration, contract, migration, firmware, browser, or static test. Link the
test file or deterministic command from the registry or artifact.

Do not invent brittle tests for rationale, trade-offs, visual intent, or other
non-executable decisions. Instead, state them as rationale and verify them at
the relevant design, architecture, or release review touchpoint.

For a new or revised normative spec, include:

1. status and owning scope;
2. touchpoints that require revalidation;
3. executable commitments with verification mappings; and
4. successor/removal condition for temporary compatibility behavior.

## Change discipline

An implementation task reads the governing artifact but does not silently edit
an approved spec to accommodate code. Stop and create a distinct spec-revision
task if the evidence requires a product decision. Update a versioned contract
and its fixtures/tests together. Remove obsolete tests, fixtures, routes, and
registry rows together with their retired behavior.

Report the artifacts considered, the triggered touchpoint, evidence inspected,
and the resulting classification. If no touchpoint applies, say so briefly and
avoid registry churn.
