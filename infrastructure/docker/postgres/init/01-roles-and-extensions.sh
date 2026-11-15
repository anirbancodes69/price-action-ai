#!/bin/sh
# Runs once, on first initialisation of the postgres data volume.
# Creates per-service roles and extensions (docs/architecture/06_SECURITY_ARCHITECTURE.md §6,
# docs/architecture/03_DATABASE_DESIGN.md §2). Table-level grants are added by migrations in M1.
set -eu

: "${DB_MIGRATOR_PASSWORD:?DB_MIGRATOR_PASSWORD must be set}"
: "${DB_BACKEND_PASSWORD:?DB_BACKEND_PASSWORD must be set}"
: "${DB_ENGINE_PASSWORD:?DB_ENGINE_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v migrator_pw="$DB_MIGRATOR_PASSWORD" \
  -v backend_pw="$DB_BACKEND_PASSWORD" \
  -v engine_pw="$DB_ENGINE_PASSWORD" \
  -v db="$POSTGRES_DB" <<'SQL'
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Schema owner: only this role runs DDL (migrations).
CREATE ROLE app_migrator LOGIN PASSWORD :'migrator_pw';
-- Runtime roles: DML only, never DDL.
CREATE ROLE app_backend LOGIN PASSWORD :'backend_pw';
CREATE ROLE app_engine LOGIN PASSWORD :'engine_pw';

REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db" TO app_migrator, app_backend, app_engine;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO app_migrator;
GRANT USAGE ON SCHEMA public TO app_backend, app_engine;

-- Baseline: runtime roles can read/write tables the migrator creates. M1 migrations narrow this
-- per table to the single-writer model (ARC-01 §6), e.g. REVOKE UPDATE/DELETE on audit_logs.
ALTER DEFAULT PRIVILEGES FOR ROLE app_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_backend, app_engine;
ALTER DEFAULT PRIVILEGES FOR ROLE app_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO app_backend, app_engine;
SQL
