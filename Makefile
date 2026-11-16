# PriceAction AI — developer shortcuts. The underlying docker compose commands are canonical
# (docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md §4). Only Docker and make are required.

COMPOSE      := docker compose
COMPOSE_DEV  := docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev
BACKEND_DEV  := $(COMPOSE_DEV) run --rm --no-deps backend
ENGINE_DEV   := $(COMPOSE_DEV) run --rm --no-deps engine
FRONTEND_DEV := $(COMPOSE_DEV) run --rm --no-deps frontend-dev

.DEFAULT_GOAL := help
.PHONY: help setup up dev down reset ps logs health migrate seed export-schemas test test-frontend test-backend test-engine lint lint-frontend lint-backend lint-engine build rebuild

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Create .env with random dev secrets and build images
	./scripts/setup-env.sh
	$(COMPOSE) build

up: ## Start the production-like stack and wait until healthy
	$(COMPOSE) up -d --build --wait

dev: ## Start the stack with hot reload (frontend on :3001, engine/db/redis on 127.0.0.1)
	$(COMPOSE_DEV) up -d --build --wait

down: ## Stop all services (keeps data volumes)
	$(COMPOSE_DEV) down

reset: ## Stop and DELETE local database/redis volumes
	$(COMPOSE_DEV) down -v

ps: ## Service status
	$(COMPOSE_DEV) ps

logs: ## Follow logs (make logs s=backend)
	$(COMPOSE_DEV) logs -f $(s)

health: ## Deep health check through the backend
	@curl -fsS 'http://localhost:8000/api/health?deep=1' && echo

migrate: ## Run Laravel migrations as the schema-owner role
	@set -a; . ./.env; set +a; \
	$(COMPOSE) run --rm -e DB_USERNAME=app_migrator -e DB_PASSWORD="$$DB_MIGRATOR_PASSWORD" backend php artisan migrate --force

seed: ## Seed reference + demo data as the schema-owner role (idempotent)
	@set -a; . ./.env; set +a; \
	$(COMPOSE_DEV) run --rm -e DB_USERNAME=app_migrator -e DB_PASSWORD="$$DB_MIGRATOR_PASSWORD" backend php artisan db:seed --force

export-schemas: ## Re-export engine JSON Schemas to contracts/engine (commit the result)
	$(COMPOSE_DEV) run --rm --no-deps -v $(CURDIR)/contracts:/contracts engine uv run python scripts/export_engine_schemas.py

test: test-frontend test-backend test-engine ## Run all test suites

test-frontend: ## Frontend unit tests
	$(FRONTEND_DEV) npm test

test-backend: ## Laravel tests (own throwaway DB, migrated with the schema-owner role)
	@set -a; . ./.env; set +a; \
	$(COMPOSE) exec -T postgres psql -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='priceaction_test'" | grep -q 1 \
	  || $(COMPOSE) exec -T postgres psql -U postgres -d postgres -c "CREATE DATABASE priceaction_test OWNER app_migrator"; \
	$(COMPOSE_DEV) run --rm --no-deps -e DB_DATABASE=priceaction_test -e DB_USERNAME=app_migrator -e DB_PASSWORD="$$DB_MIGRATOR_PASSWORD" backend vendor/bin/phpunit

test-engine: ## Python engine tests
	$(ENGINE_DEV) uv run pytest

lint: lint-frontend lint-backend lint-engine ## Run all linters / type checks

lint-frontend:
	$(FRONTEND_DEV) sh -c "npm run lint && npm run typecheck"

lint-backend:
	$(BACKEND_DEV) vendor/bin/pint --test

lint-engine:
	$(ENGINE_DEV) sh -c "uv run ruff check . && uv run ruff format --check . && uv run mypy"

build: ## Build all images
	$(COMPOSE) build

rebuild: ## Rebuild one service without cache (make rebuild s=engine)
	$(COMPOSE) build --no-cache $(s) && $(COMPOSE) up -d $(s)
