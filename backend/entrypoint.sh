#!/bin/sh
#
# Container entrypoint.
#
# Two jobs before the app starts: wait for PostgreSQL to accept connections,
# then bring the schema up to date. Both matter on a `docker compose up` where
# the database container is still initialising — `depends_on` waits for the
# container to start, not for Postgres to be ready to serve.
#
# Migrations run here rather than in the app, so exactly one process owns the
# schema. The web and worker containers both use this entrypoint; `alembic
# upgrade head` is safe to run concurrently because Alembic takes a lock on its
# version table, and is a no-op when the schema is already current.

set -e

: "${DATABASE_URL:?DATABASE_URL must be set}"
: "${MIGRATE_ON_START:=true}"
: "${DB_WAIT_SECONDS:=60}"

if echo "$DATABASE_URL" | grep -q '^postgres'; then
  echo "Waiting for the database (up to ${DB_WAIT_SECONDS}s)..."
  waited=0
  until python -c "
import os, sys
import psycopg2
try:
    psycopg2.connect(os.environ['DATABASE_URL']).close()
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    waited=$((waited + 2))
    if [ "$waited" -ge "$DB_WAIT_SECONDS" ]; then
      echo "Database did not become ready within ${DB_WAIT_SECONDS}s." >&2
      exit 1
    fi
    sleep 2
  done
  echo "Database is ready."
fi

if [ "$MIGRATE_ON_START" = "true" ]; then
  echo "Applying migrations..."
  alembic upgrade head
  echo "Migrations applied."
fi

exec "$@"
