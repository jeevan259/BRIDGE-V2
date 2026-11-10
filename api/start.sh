#!/bin/sh
set -e

echo "=== BRIDGE v2 Backend Startup ==="
echo "Running database migrations (Alembic)..."
alembic upgrade head

echo "Ensuring tenant and baseline data is seeded..."
python -m app.seed_demo

echo "Starting Uvicorn API server on port ${PORT:-8000} with proxy headers..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips='*'

