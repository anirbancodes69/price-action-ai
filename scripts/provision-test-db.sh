#!/bin/sh
# Provision the dedicated test roles and the throwaway test database (D0, DR-6). Idempotent; never prints a secret.
#
#   app_test         engine integration tests: DML only inside the test database (DB_TEST_PASSWORD)
#   app_test_schema  Laravel/PHPUnit: owns the test database so RefreshDatabase can migrate (DB_TEST_SCHEMA_PASSWORD)
#
# Both roles are created at cluster level with NO privilege on the development database (its ACL already limits
# CONNECT to the application roles; this script never connects to, grants on or alters it). The only database
# touched is $TEST_DB, which must match the approved name pattern. A missing password is generated with openssl
# and appended to .env (gitignored, mode 0600); an existing role's password is never changed.
#
# Provisioning is deliberately separate from the historical D0 baseline (globals.sql), which predates these roles:
# after restoring a baseline into a fresh instance, run this script again.
set -eu
cd "$(dirname "$0")/.."

TEST_DB=${TEST_DB:-priceaction_test}
if ! printf '%s' "$TEST_DB" | grep -Eq '^priceaction_test(_[a-z0-9]+)*$'; then
  echo "refusing: '$TEST_DB' is not an approved test database name" >&2
  exit 2
fi
[ -f .env ] || { echo ".env not found (run make setup first)" >&2; exit 1; }

env_value() { grep "^$1=" .env | tail -n 1 | cut -d= -f2-; }
ensure_secret() {
  if [ -z "$(env_value "$1")" ]; then
    umask 077
    printf '\n# %s\n%s=%s\n' "$2" "$1" "$(openssl rand -hex 24)" >> .env
    echo "generated $1 in .env (value not shown)"
  fi
}
ensure_secret DB_TEST_PASSWORD "Dedicated role for the engine integration tests (D0): DML only inside priceaction_test"
ensure_secret DB_TEST_SCHEMA_PASSWORD "Dedicated role for the Laravel tests (D0): owns priceaction_test only"

pg() { docker compose exec -T postgres psql -X -q -U postgres -v ON_ERROR_STOP=1 "$@"; }
role_exists() { [ "$(pg -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$1'")" = 1 ]; }
create_role() {  # create_role <role> <env var holding the password>; the password travels on stdin only
  if role_exists "$1"; then echo "role $1 exists (password unchanged)"; return; fi
  printf "CREATE ROLE %s LOGIN PASSWORD '%s' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 8;\n" \
    "$1" "$(env_value "$2")" | pg -d postgres
  echo "created role $1"
}
create_role app_test DB_TEST_PASSWORD
create_role app_test_schema DB_TEST_SCHEMA_PASSWORD

if [ "$(pg -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$TEST_DB'")" = 1 ]; then
  pg -d postgres -c "ALTER DATABASE \"$TEST_DB\" OWNER TO app_test_schema"
else
  pg -d postgres -c "CREATE DATABASE \"$TEST_DB\" OWNER app_test_schema"
  echo "created database $TEST_DB"
fi

# Everything below runs connected to the TEST database only.
pg -d "$TEST_DB" <<SQL
GRANT CONNECT ON DATABASE "$TEST_DB" TO app_test;
GRANT USAGE ON SCHEMA public TO app_test;
DO \$\$
DECLARE r record;
BEGIN
  -- hand existing objects to the Laravel test role so migrate:fresh can drop and recreate them
  FOR r IN SELECT format('ALTER TABLE %I.%I OWNER TO app_test_schema', schemaname, tablename) AS s
           FROM pg_tables WHERE schemaname = 'public' AND tableowner <> 'app_test_schema' LOOP EXECUTE r.s; END LOOP;
  FOR r IN SELECT format('ALTER SEQUENCE %I.%I OWNER TO app_test_schema', s.schemaname, s.sequencename) AS s
           FROM pg_sequences s JOIN pg_class c ON c.relname = s.sequencename AND c.relnamespace = 'public'::regnamespace
           WHERE s.schemaname = 'public' AND s.sequenceowner <> 'app_test_schema'
             AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype IN ('a', 'i')) LOOP EXECUTE r.s; END LOOP;
  FOR r IN SELECT format('ALTER FUNCTION %s OWNER TO app_test_schema', p.oid::regprocedure) AS s
           FROM pg_proc p WHERE p.pronamespace = 'public'::regnamespace AND p.prokind = 'f'
             AND pg_get_userbyid(p.proowner) <> 'app_test_schema'
             AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e') LOOP EXECUTE r.s; END LOOP;
END \$\$;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_test;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO app_test;
-- tables that Laravel's migrate:fresh creates later stay usable by the engine test role
ALTER DEFAULT PRIVILEGES FOR ROLE app_test_schema IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_test;
ALTER DEFAULT PRIVILEGES FOR ROLE app_test_schema IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO app_test;
SQL
echo "test database $TEST_DB provisioned (roles app_test, app_test_schema)"
