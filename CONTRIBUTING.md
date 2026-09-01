# Contributing to FitTrack

Use a separate branch or worktree for each implementation task. Before editing,
record the following in the pull request or task description:

```text
Objective:
Conflict domain and owner:
In scope / out of scope paths:
Governing spec, ADR, or contract:
Acceptance checks:
Allowed side effects:
Stop conditions:
Artifact touchpoint and lifecycle result (if any):
```

One writer owns a conflict domain. In particular, migrations, API contracts,
authentication/ownership, shared frontend API/types, and infrastructure are
serialized. Independent researchers and reviewers are read-only.

Run `./scripts/check` before review. For a changed spec, contract, migration,
authorization boundary, sync behavior, or browser flow, run the additional
mapped checks and report the result. Do not modify an approved spec merely to
make an implementation pass; make a separately reviewed spec revision.

For an Alembic change, run `FITTRACK_MIGRATION_REHEARSAL=1 DATABASE_URL=... \
python backend/scripts/verify_migrations.py` only against a disposable
PostgreSQL database. The rehearsal proves the legacy-owner cutover rather than
silently bypassing it.
