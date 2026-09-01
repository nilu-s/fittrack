# Backend area rules

Read the governing spec, [`../docs/architecture/authorization-matrix.md`](../docs/architecture/authorization-matrix.md),
and the relevant contract before changing a public route, persistence, sync,
authentication, Google integration, or scale behavior.

Routes translate HTTP only; put business rules in testable services. Every ID
lookup for account-owned data includes the authenticated account scope.
Migrations are serial: one owner edits `alembic/versions/` and validates one
head plus `alembic upgrade head` on a fresh database.

Run `python -m pytest -q` for backend changes. Contract changes also regenerate
and verify `docs/contracts/openapi.json`; schema/ownership changes require the
database and A-vs-B isolation checks declared by the governing spec.
