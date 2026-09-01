"""Exercise the full Alembic chain against a disposable PostgreSQL database.

Revision 021 deliberately refuses to migrate legacy rows until exactly one
authenticated legacy owner exists. A plain ``alembic upgrade head`` therefore
does not verify the production path. This rehearsal creates that required
precondition at revision 020, then validates the final cutover and current
head. It is intentionally opt-in because it writes data.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


BACKEND_ROOT = Path(__file__).resolve().parents[1]
LEGACY_OWNER_EMAIL = "migration-rehearsal@example.test"
OWNED_TABLES = (
    "day_entries", "meals", "todos", "meal_templates", "training_units",
    "training_rotation", "training_sets", "exercises", "sync_log", "photos",
    "google_tokens", "exercise_progress", "dishes", "goals",
)


def alembic(*arguments: str, env: dict[str, str]) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND_ROOT,
        env=env,
        check=True,
    )


async def insert_legacy_owner(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO accounts (id, google_subject, email, display_name) "
                    "VALUES (:id, :subject, :email, :name)"
                ),
                {
                    "id": uuid.uuid4(),
                    "subject": "migration-rehearsal-subject",
                    "email": LEGACY_OWNER_EMAIL,
                    "name": "Migration rehearsal",
                },
            )
    finally:
        await engine.dispose()


async def verify_cutover(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            account_count = await connection.scalar(
                text("SELECT count(*) FROM accounts WHERE email = :email"),
                {"email": LEGACY_OWNER_EMAIL},
            )
            if account_count != 1:
                raise RuntimeError("migration rehearsal legacy owner is not unique")
            for table in OWNED_TABLES:
                has_legacy_column = await connection.scalar(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema = current_schema() AND table_name = :table "
                        "AND column_name = 'user_id')"
                    ),
                    {"table": table},
                )
                if has_legacy_column:
                    raise RuntimeError(f"{table} retained legacy user_id after cutover")
    finally:
        await engine.dispose()


def main() -> None:
    if os.environ.get("FITTRACK_MIGRATION_REHEARSAL") != "1":
        raise SystemExit("Refusing to write: set FITTRACK_MIGRATION_REHEARSAL=1 for a disposable database")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    migration_env = os.environ.copy()
    migration_env.pop("LEGACY_OWNER_EMAIL", None)
    alembic("upgrade", "020", env=migration_env)
    asyncio.run(insert_legacy_owner(database_url))
    migration_env["LEGACY_OWNER_EMAIL"] = LEGACY_OWNER_EMAIL
    alembic("upgrade", "head", env=migration_env)
    asyncio.run(verify_cutover(database_url))
    alembic("heads", env=migration_env)


if __name__ == "__main__":
    main()
