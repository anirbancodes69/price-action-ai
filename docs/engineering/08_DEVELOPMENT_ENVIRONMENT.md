# Development Environment

| Field | Value |
|---|---|
| Document ID | ENG-08 |
| Version | 0.1.0 |
| Status | Partially implemented (frontend services exist; others specified) |
| Owner | Technical Lead |
| Last updated | 2026-11-15 |
| Related | [OPS-02 Environment configuration](../operations/02_ENVIRONMENT_CONFIGURATION.md) · [ENG-09 Repository](09_GITHUB_REPOSITORY_STRATEGY.md) · [ARC-01 §11](../architecture/01_SYSTEM_ARCHITECTURE.md#11-deployment-topology) |

## 1. Principles

- Docker Compose is the only required local tool (plus Git). No local PHP, Python or PostgreSQL installation is needed; Node is optional for editor tooling.
- One `docker-compose.yml` at the root; development overrides via Compose **profiles** (`dev`) and an optional `docker-compose.override.yml` (gitignored).
- Services mirror production topology (ARC-01) so behaviour matches.

## 2. Current state (M0 complete, 2026-11-15)

All services below exist and pass their health checks. Quick start:

```bash
./scripts/setup-env.sh      # once: root .env with random dev secrets (never committed)
make up                     # production-like stack, waits until healthy
make dev                    # hot reload: backend/engine source mounted, frontend-dev on :3001,
                            # engine/postgres/redis published on 127.0.0.1 only
make health                 # deep check through the backend (DB, Redis, engine)
make test && make lint      # all suites inside containers
```

Files: `docker-compose.yml` (all services), `docker-compose.dev.yml` (dev overlay: dev image targets, bind mounts, localhost ports), `Makefile`, `scripts/setup-env.sh`, `infrastructure/docker/{nginx,postgres,redis}/`.

## 3. Services

| Service | Image / build | Ports (host, dev only) | Depends on | Health check |
|---|---|---|---|---|
| `frontend` / `frontend-dev` | `frontend/Dockerfile(.dev)` | 3000 / 3001 | — (mock data until M7) | `GET /login` |
| `backend` | `backend/Dockerfile` (php-fpm; targets `runtime`/`dev`) | — | postgres, redis | FPM `/ping` via `cgi-fcgi` |
| `backend-nginx` | `nginx:1.27-alpine` + `infrastructure/docker/nginx/backend.conf` (Docker DNS resolver, so backend restarts need no nginx restart) | 8000 | backend | `GET /api/health` |
| `backend-queue` | backend image, `php artisan queue:work redis` (Horizon added in M6) | — | backend | process check |
| `backend-scheduler` | backend image, `php artisan schedule:work` | — | backend | process check |
| `engine` | `python-engine/Dockerfile`, uvicorn | 8100 (dev only) | postgres, redis | `GET /health` |
| `engine-worker` | engine image, `arq app.workers.settings.WorkerSettings` | — | engine | `arq --check` |
| `postgres` | `postgres:17-alpine` + `infrastructure/docker/postgres/init/` (roles `app_migrator`/`app_backend`/`app_engine`, extensions) | 5432 (dev only) | — | `pg_isready` |
| `redis` | `redis:7.4-alpine`, AOF everysec, password required | 6379 (dev only) | — | `redis-cli ping` |
| `mailpit` (planned, M6) | local SMTP catcher | 8025 | — | — |

Named volumes: `pgdata`, `redisdata`. The dev overlay bind-mounts source for backend and engine with auto-reload (`uvicorn --reload`, `arq --watch`, PHP-FPM reads files directly); `vendor/` stays in an anonymous volume and the Python venv lives at `/opt/venv`.

Postgres reads role passwords only when the volume is first created. After regenerating `.env`, run `make reset`.

## 4. Commands

The `Makefile` wraps the commands below (`make help`); the raw Compose commands are canonical.

| Task | Command |
|---|---|
| Initial setup | `./scripts/setup-env.sh` → `docker compose build` (= `make setup`) |
| Start all (dev) | `docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev up -d --wait` (= `make dev`) |
| Start production-like | `docker compose up -d --build --wait` (= `make up`) |
| Stop | `docker compose down` (keep volumes) |
| Reset everything | `docker compose down -v` (**deletes local DB**) |
| Logs | `docker compose logs -f backend engine-worker` |
| Shell | `docker compose exec backend sh` / `docker compose exec engine sh` |
| Migrations (as schema owner) | `make migrate` (runs artisan with `DB_USERNAME=app_migrator`) |
| Rollback last migration (dev only) | `docker compose run --rm backend php artisan migrate:rollback --step=1` |
| Seed demo data | `docker compose run --rm backend php artisan db:seed --class=DemoSeeder` |
| Frontend tests | `make test-frontend` |
| Frontend lint/typecheck | `make lint-frontend` |
| Laravel tests | `make test-backend` (`vendor/bin/phpunit` against a throwaway `priceaction_test` database that the target creates, migrated by the `app_migrator` role; `artisan test` warns when no `backend/.env` file exists) |
| Python tests | `make test-engine` |
| Trading tests only | `docker compose run --rm engine uv run pytest tests/trading` |
| Rebuild one service | `docker compose build --no-cache engine && docker compose up -d engine` |
| Run a worker job manually | `docker compose exec engine uv run python -m app.workers.cli ingest-daily --source demo --date 2026-11-13` |

## 5. Environment files

Templates committed: `/.env.example` (Compose-level), `backend/.env.example`, `python-engine/.env.example`, `frontend/.env.example`. Real `.env` files are gitignored. Variables are listed in [OPS-02](../operations/02_ENVIRONMENT_CONFIGURATION.md). Local development never needs real Kite credentials: DEMO provider works offline; Kite can be enabled with a personal developer app.

## 6. Editor support (optional)

Dev containers (`.devcontainer/`) may be added later; not required. Lint/format run inside containers via pre-commit hooks (`scripts/pre-commit`) that call `docker compose run`.

## 7. Known local quirks

- macOS file watching in containers: `WATCHPACK_POLLING=true` is already set in `frontend/Dockerfile.dev`.
- `frontend/AGENTS.md` is regenerated by `next dev`; commit it to keep the tree clean (as the file itself notes).
- Remove `.DS_Store` and `frontend/tsconfig.tsbuildinfo` from version control via root `.gitignore` (M0).
