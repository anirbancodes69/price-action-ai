# Technology Stack

| Field | Value |
|---|---|
| Document ID | ARC-02 |
| Version | 0.1.0 |
| Status | Specification ready (backend/engine versions to be pinned in M0) |
| Owner | Solution Architect |
| Last updated | 2026-11-15 |
| Related | [ARC-01](01_SYSTEM_ARCHITECTURE.md) · [ADR index](../adr/README.md) · [ENG-08 Dev environment](../engineering/08_DEVELOPMENT_ENVIRONMENT.md) |

## 1. Purpose

Lists each technology, why it was chosen, what it is responsible for, alternatives considered and how versions are managed. Versions marked **(existing)** are what the repository uses today (`frontend/package.json`, `frontend/Dockerfile`); others are **targets** to be pinned when the component is created.

## 2. Stack by layer

### 2.1 Frontend

| Technology | Version | Responsibility | Alternatives considered |
|---|---|---|---|
| Next.js (App Router, Cache Components, standalone output) | 16.4.6 (existing) | Routing, SSR, server components | Remix, Vite SPA — see [ADR-001](../adr/ADR-001-FRONTEND-ARCHITECTURE.md) |
| React | 19.3.0 (existing) | UI | — |
| TypeScript (strict) | ^5 (existing) | Type safety; `src/types` is the frontend's view of the API contract | — |
| Tailwind CSS v4 + `@tailwindcss/turbopack` | 4.3.3 (existing) | Styling via design tokens (`src/styles/tokens.css`) | CSS modules, component libraries (MUI/Chakra) rejected to keep a custom trading UI |
| TradingView Lightweight Charts | ^5.3.0 (existing) | Candlestick charts with zone/BOS primitives | Highcharts Stock (licensing cost), ECharts |
| lucide-react, clsx, tailwind-merge | existing | Icons, class utilities | — |
| ESLint 9 + eslint-config-next | existing | Linting | Biome |
| Test tooling | **to add (M0)**: Vitest + Testing Library; Playwright for E2E (M7) | Unit/component/E2E tests | Jest |
| Node.js runtime | 24-alpine (existing Docker base) | Build/runtime | — |

### 2.2 Application backend

| Technology | Target | Responsibility | Alternatives |
|---|---|---|---|
| PHP | 8.4 | Runtime | — |
| Laravel | Latest stable major at M0 | Modular monolith, REST API, auth, queues | NestJS, Django — [ADR-002](../adr/ADR-002-LARAVEL-APPLICATION-BACKEND.md) |
| Laravel Sanctum | bundled | SPA cookie auth | Passport (OAuth server unnecessary), JWT (revocation complexity) |
| Laravel Horizon | bundled | Redis queue workers + dashboard (admin-only) | Plain `queue:work` |
| Pest + PHPUnit | latest | Unit, feature, architecture tests | — |
| Larastan (PHPStan) | latest, start at level 6 | Static analysis | Psalm |
| Laravel Pint | latest | Code style | PHP-CS-Fixer directly |
| Web server | Nginx + PHP-FPM | HTTP | FrankenPHP/Octane (revisit for performance later) |

### 2.3 Quantitative engine

| Technology | Target | Responsibility | Alternatives |
|---|---|---|---|
| Python | 3.13 | Runtime | — |
| FastAPI + Uvicorn | latest | Internal API | Flask — [ADR-003](../adr/ADR-003-PYTHON-QUANTITATIVE-ENGINE.md) |
| Pydantic v2 | latest | Request/response schemas, settings | — |
| numpy (pandas only where justified) | latest | Array computations | Polars (revisit for backtest speed) |
| `decimal` (stdlib) | — | Money and price arithmetic in risk functions | float (rejected for money) |
| SQLAlchemy 2 (Core) + psycopg 3 | latest | DB access | asyncpg directly |
| arq | latest | Redis job queue for workers | Celery, RQ |
| httpx | latest | Kite and LLM HTTP clients | requests |
| uv | latest | Dependency and lockfile management | pip-tools, Poetry |
| Ruff (lint + format), mypy | latest | Quality | Black + flake8 |
| pytest, Hypothesis | latest | Tests incl. property-based | — |

### 2.4 Data and infrastructure

| Technology | Target | Responsibility | Notes |
|---|---|---|---|
| PostgreSQL | 17 (18 acceptable if all extensions/tools support it at M0) | System of record | Extensions: `citext`, `btree_gist`, `pgcrypto` — [ADR-005](../adr/ADR-005-POSTGRESQL-DATABASE.md) |
| Redis | 7.4 (or Valkey 8 as drop-in) | Cache, queues, sessions, rate limiting | Licensing of Redis versions should be checked at M0 — [ADR-006](../adr/ADR-006-REDIS-CACHING-AND-QUEUES.md) |
| Docker + Docker Compose v2 | latest | Local, CI and server runtime | No Kubernetes |
| Reverse proxy | Caddy (automatic TLS) or Nginx | TLS termination, routing | Decide in M10 (OQ-OPS-01) |
| GitHub + GitHub Actions + GHCR | — | Source control, CI/CD, image registry | [ADR-012](../adr/ADR-012-GITHUB-ACTIONS-CI-CD.md) |

### 2.5 External services

| Service | Purpose | Status |
|---|---|---|
| Zerodha Kite Connect | Personal-mode market data (instruments, daily historical candles) | Selected; adapter specified in [ARC-08](08_INTEGRATION_ARCHITECTURE.md) |
| LLM provider | Explanations only | Provider/model **unresolved** (OQ-AI-01); adapter-based |
| Licensed market-data vendor | SaaS mode | **Unresolved**; release gate ([OPS-05](../operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md)) |
| Error tracking (e.g. Sentry or GlitchTip self-hosted) | Exceptions | Decide in M10 |
| Transactional email | Verification, password reset | Decide in M6 |

## 3. Compatibility requirements

- The frontend talks only to `/api/v1`. API changes follow the versioning rules in ARC-04 §2.
- Engine ↔ Laravel contracts are JSON Schemas generated from Pydantic models and committed to `contracts/engine/` (path decided in [ENG-09](../engineering/09_GITHUB_REPOSITORY_STRATEGY.md)); Laravel contract tests validate against them.
- Public API OpenAPI spec committed at `contracts/api/openapi.yaml`; the frontend's TypeScript types for the HTTP adapter are generated from it (M7).
- All timestamps are UTC `timestamptz` in storage; trading dates are `date` in exchange time (Asia/Kolkata). Display formatting is en-IN / Asia/Kolkata (existing `frontend/src/lib/format.ts`).

## 4. Version management strategy

| Concern | Rule |
|---|---|
| Lockfiles | Committed for every component (`package-lock.json` exists; `composer.lock`, `uv.lock` to add). CI fails if lockfile is out of sync. |
| Runtime versions | Pinned in Dockerfiles by major.minor tag; base image digests pinned for production builds. |
| Upgrades | Dependabot (grouped weekly PRs per ecosystem); majors handled manually with a short ADR if behaviour changes. |
| Framework docs drift | The frontend `AGENTS.md` warns that Next.js 16 differs from older conventions; read bundled docs in `node_modules/next/dist/docs/` before framework-level changes. |
| Ruleset vs engine version | Engine semantic version (`engine_version`) and ruleset version (`pa-core x.y.z`) are independent and both recorded on every analysis run. |
