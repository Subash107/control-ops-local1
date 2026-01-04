"""Check Alembic migration drift.

This validates that the database schema at Alembic HEAD matches SQLAlchemy models.
Intended for CI: run migrations first, then run this script.

Exits:
  0 - no drift
  1 - drift detected
  2 - configuration / connection error
"""

from __future__ import annotations

import os
import sys

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.database import Base
from app import models  # noqa: F401  (ensure models are imported/registered)


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2

    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        diffs = compare_metadata(ctx, Base.metadata)

    if diffs:
        print("Migration drift detected:")
        for d in diffs:
            print(f"- {d}")
        return 1

    print("No migration drift detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
