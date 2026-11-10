#!/bin/sh
set -e

echo "[entrypoint] applying database migrations..."
# Retry while the database is starting up.
i=0
until alembic upgrade head; do
  i=$((i + 1))
  if [ "$i" -ge 15 ]; then
    echo "[entrypoint] database not reachable after $i attempts" >&2
    exit 1
  fi
  echo "[entrypoint] database not ready, retrying in 2s ($i)..."
  sleep 2
done

if [ "${SEED_SAMPLES:-false}" = "true" ]; then
  echo "[entrypoint] seeding synthetic sample datasets..."
  python -m app.scripts.seed_samples
fi

exec "$@"
