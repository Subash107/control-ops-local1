#!/bin/sh
set -e

# Ensure the project root is on PYTHONPATH so alembic and uvicorn can import the `app` package
export PYTHONPATH="/app"

echo "Running database migrations..."
alembic upgrade head || {
  echo "Alembic upgrade failed; attempting to stamp head (useful for existing schema)."
  alembic stamp head
}

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
