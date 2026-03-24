#!/bin/bash
set -e

if [ "$SERVICE_TYPE" = "worker" ]; then
    echo "Starting Worker..."
    exec python scripts/worker.py
else
    echo "Starting API..."
    python scripts/run_migrations.py
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
fi
