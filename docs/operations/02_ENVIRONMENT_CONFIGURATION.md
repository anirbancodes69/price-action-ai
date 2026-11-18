# Environment Configuration

| Field | Value |
|---|---|
| Document ID | OPS-02 |
| Version | 0.1.0 |
| Status | Specification ready |
| Owner | DevOps / Technical Lead |
| Last updated | 2026-11-15 |
| Related | [ARC-06 §7 Secrets](../architecture/06_SECURITY_ARCHITECTURE.md#7-secret-management) · [ENG-08](../engineering/08_DEVELOPMENT_ENVIRONMENT.md) · [ENG-10 §5](../engineering/10_GITHUB_ACTIONS_CI_CD.md#5-required-secrets) |

## 1. Environments

| | Local | CI | Staging | Production |
|---|---|---|---|---|
| Purpose | Development | Automated checks | Pre-prod verification | Owner use |
| Data | DEMO (+ optional personal) | Ephemeral fixtures | DEMO + optional personal | Personal |
| `APP_ENV` | `local` | `testing` | `staging` | `production` |
| Debug | on | off | off | off |
| Secrets | `.env` | generated per run | GitHub Environment `staging` | GitHub Environment `production` |
| LLM | stub or dev key | stub | real key, low cap | real key |
| Kite | optional dev app | never | owner app (optional) | owner app |

## 2. Variable inventory

Legend: **S** = secret (never committed; `.env.example` holds placeholder only).

### 2.1 Shared / Compose

| Variable | Example | S | Notes |
|---|---|---|---|
| `COMPOSE_PROJECT_NAME` | `priceaction` | | |
| `POSTGRES_DB` | `priceaction` | | |
| `POSTGRES_PASSWORD` (superuser, init only) | — | S | |
| `DB_BACKEND_PASSWORD`, `DB_ENGINE_PASSWORD`, `DB_MIGRATOR_PASSWORD` | — | S | Per-role passwords (ARC-06 §6) |
| `REDIS_PASSWORD` | — | S | Redis ACL users per service recommended |
| `TZ` | `UTC` | | Containers run in UTC; exchange time computed explicitly |

### 2.2 Frontend

| Variable | Example | S | Notes |
|---|---|---|---|
| `DATA_SOURCE` | `mock` / `http` | | Server-only selection of adapter (ENG-02 §5) |
| `BACKEND_INTERNAL_URL` | `http://backend-nginx:8000` | | Server-side fetches |
| `NEXT_PUBLIC_APP_NAME` | `PriceAction AI` | | Only non-sensitive values may use `NEXT_PUBLIC_` |
| `NEXT_TELEMETRY_DISABLED` | `1` | | Already set in Dockerfiles |

### 2.3 Backend (Laravel)

| Variable | Example | S | Notes |
|---|---|---|---|
| `APP_KEY`, `APP_PREVIOUS_KEYS` | — | S | Rotation supported |
| `APP_URL` | `https://app.example.com` | | |
| `DB_HOST`, `DB_DATABASE`, `DB_USERNAME`=`app_backend`, `DB_PASSWORD` | — | S (password) | |
| `REDIS_HOST`, `REDIS_PASSWORD` | — | S | |
| `SESSION_DRIVER=redis`, `SESSION_SECURE_COOKIE=true`, `SANCTUM_STATEFUL_DOMAINS` | — | | |
| `PROVIDER_TOKEN_KEY`, `PROVIDER_TOKEN_KEY_VERSION` | — | S | Broker token encryption |
| `KITE_API_KEY` | — | S | Platform Kite app |
| `KITE_API_SECRET` | — | S | Never leaves backend |
| `KITE_REDIRECT_URL` | `https://app.example.com/api/v1/integrations/zerodha/callback` | | Must match Kite app config |
| `ENGINE_URL` | `http://engine:8100` | | |
| `ENGINE_TIMEOUT_SECONDS`, `ENGINE_SCAN_TIMEOUT_SECONDS` | `2`, `15` | | Engine call budgets; a scan or analysis reads stored bars (ADR-016) |
| `ENGINE_DATA_SOURCE_ID` | — | | `data_sources` row the owner reads; Compose passes `INGEST_DATA_SOURCE_ID`. Empty: the DEMO source |
| `TRADING_UNIVERSE` | `NIFTY50` | | Universe the scanner reads by default (`DEMO` with the demo data source) |
| `TRADING_CAPITAL_DEFAULT` | `100000` | | Planning capital used until a risk profile is stored (HYPOTHESIS, ADR-014) |
| `ENGINE_SERVICE_TOKEN`, `ENGINE_SERVICE_TOKEN_PREVIOUS` | — | S | Laravel → engine |
| `BACKEND_INTERNAL_TOKEN`, `..._PREVIOUS` | — | S | engine → Laravel |
| `EOD_PIPELINE_TIME` | `18:30` | | IST |
| `MAIL_*` | — | S | |
| `ERROR_TRACKING_DSN` | — | S | |

### 2.4 Engine and workers

| Variable | Example | S | Notes |
|---|---|---|---|
| `DATABASE_URL` (role `app_engine`) | — | S | |
| `REDIS_URL` | — | S | |
| `ENGINE_SERVICE_TOKEN` | — | S | Validates inbound |
| `BACKEND_INTERNAL_URL`, `BACKEND_INTERNAL_TOKEN` | — | S | JIT token fetch, events |
| `KITE_API_KEY` | — | S | Needed with the user access token for API calls |
| `KITE_HISTORICAL_RPS` | `3` | | Assumption, verify (ARC-08) |
| `LLM_ENABLED`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_DAILY_BUDGET_USD` | — | S (key) | ARC-07 |
| `WORKER_CONCURRENCY_ANALYSIS` etc. | — | | ENG-04 §7 |
| `ACTIVE_RULESET` | `pa-intraday@0.1.0` | | |

## 3. Rules

1. Every variable appears in the matching `.env.example` with a comment; CI checks that code-referenced variables exist in examples (simple grep script, M0).
2. `NEXT_PUBLIC_*` variables are reviewed in PRs — they are shipped to browsers.
3. Production secrets are rotated at least annually and immediately on suspected exposure (procedure in ARC-06 §7).
4. Configuration differences between environments are limited to this inventory; no environment-specific code paths except `APP_ENV` checks for debug tooling.

## 4. GitHub Environments

| Environment | Protection | Secrets |
|---|---|---|
| `staging` | Deploy only from `main` | SSH key/host, rendered env file contents (or individual secrets) |
| `production` | Required reviewer (owner), deploy only from tags `v*`, optional wait timer | Same set for production |
