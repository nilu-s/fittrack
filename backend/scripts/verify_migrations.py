"""Verify the single Cronicl baseline against a disposable database."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if os.environ.get("APP_MIGRATION_REHEARSAL") != "1":
        raise SystemExit("Refusing to write: set APP_MIGRATION_REHEARSAL=1 for a disposable database")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    for args in (("upgrade", "head"), ("heads",)):
        subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND_ROOT, check=True)


if __name__ == "__main__":
    main()
