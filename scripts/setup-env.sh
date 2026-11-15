#!/bin/sh
# Creates the root .env for Docker Compose with random development secrets.
# Never commit .env (constraint C-17). Safe to re-run: refuses to overwrite unless --force.
set -eu
cd "$(dirname "$0")/.."

if [ -f .env ] && [ "${1:-}" != "--force" ]; then
  echo ".env already exists (use --force to regenerate; this rotates all local secrets)." >&2
  exit 0
fi

rand() { openssl rand -hex 24; }

sed \
  -e "s|^APP_KEY=.*|APP_KEY=base64:$(openssl rand -base64 32)|" \
  -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(rand)|" \
  -e "s|^DB_MIGRATOR_PASSWORD=.*|DB_MIGRATOR_PASSWORD=$(rand)|" \
  -e "s|^DB_BACKEND_PASSWORD=.*|DB_BACKEND_PASSWORD=$(rand)|" \
  -e "s|^DB_ENGINE_PASSWORD=.*|DB_ENGINE_PASSWORD=$(rand)|" \
  -e "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=$(rand)|" \
  -e "s|^ENGINE_SERVICE_TOKEN=.*|ENGINE_SERVICE_TOKEN=$(rand)|" \
  -e "s|^BACKEND_INTERNAL_TOKEN=.*|BACKEND_INTERNAL_TOKEN=$(rand)|" \
  .env.example > .env
chmod 600 .env
echo "Created .env with random development secrets."
echo "Note: Postgres reads its passwords only when the volume is first created;"
echo "after regenerating, reset the volume with: docker compose down -v"
