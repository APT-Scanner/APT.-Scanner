#!/usr/bin/env bash
set -e

# The working directory is already /app/backend, so alembic will find its config
echo "Running database migrations..."
alembic upgrade head
echo "Database migrations complete."

# Start the Uvicorn server
echo "Starting Uvicorn server..."
exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level ${LOG_LEVEL:-info}