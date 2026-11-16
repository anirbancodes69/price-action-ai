# CURRENT — Project State

Last verified: **2026-11-17** against the repository (`main` at `185919f`; T-103 on branch `feature/contracts-openapi-spec`).

Status vocabulary: `NOT STARTED` · `IN PROGRESS` · `COMPLETED` · `BLOCKED` · `NEEDS REVIEW`.
Update this file at the end of every substantial task, based only on verified state.

## Phase and milestone

| Item | Value |
|---|---|
| Phase | Foundation complete; feature development not yet started |
| Last completed milestone | **M0** — repository, Docker and CI foundation (merged in PR #1, 2026-11-15) |
| Current milestone | **M1** — database and contracts: `NEEDS REVIEW` (all tasks done; PR pending). Next: M2 (blocked on owner access, OQ-INT-01/02/04) or M3 (swing points and structure, can start on fixtures) |
| Detailed plan | [ROADMAP.md](ROADMAP.md) → [ENG-01](docs/engineering/01_IMPLEMENTATION_ROADMAP.md) |

## Component status

| Area | Status | What actually exists |
|---|---|---|
| Frontend UI | `COMPLETED` (Phase 1, mock data) | Next.js 16.4.6, React 19, Tailwind v4, Lightweight Charts v5. Routes: auth (login/register/forgot-password), onboarding, dashboard, market-scanner, analysis, watchlists, trade-plans, portfolio, journal, backtesting, settings. Vitest unit tests for format, labels, colours, auth validation and scanner filters (25). |
| Frontend design system | `COMPLETED` (PR #18) | [docs/design-standards.md](docs/design-standards.md) adopted ([ADR-013](docs/adr/ADR-013-DESIGN-STANDARDS.md)): OKLCH tokens with PriceAction brand values, light/dark/system themes (dark default), shared components and `lib/colors.ts`, every screen refactored, `(app)/error.tsx`. Verified locally (lint, typecheck, tests, build, screenshots in both themes at three widths, WCAG AA contrast). Implementation and deviations: [ENG-02 §11](docs/engineering/02_FRONTEND_ARCHITECTURE.md#11-design-system). |
| Frontend data | **Mock only** | Every page reads the `DataSource` mock adapter (`frontend/src/lib/data`). Analysis overlays come from a demo heuristic (`src/mocks/demo-analysis.ts`), **not** the specified trading rules. Login accepts any well-formed email and password. There is no mutation client yet. |
| Frontend ↔ spec | `NEEDS REVIEW` | 24 known discrepancies (D-01..D-24) in [ENG-02 §9](docs/engineering/02_FRONTEND_ARCHITECTURE.md#9-discrepancy-register), to be resolved in M7 (D-20 partly resolved by the design-standards work, PR #18). |
| Claude Code skills | `COMPLETED` (PR #16) | 8 project skills in `.claude/skills/` (price-action-domain, quant-engine, market-data, schema-and-contracts, frontend-ui, security-guardrails, quality-gate, docs-sync). They are workflows that link to the specs, plus two stdlib scripts (docs impact mapping, relative link and anchor check). Indexed in CLAUDE.md §10. No agents and no `.claude/settings.json`. |
| Documentation | `COMPLETED` (specification) | 58 spec files under `docs/`, the design standards and 13 accepted ADRs. They describe the target system, so most of it is **not implemented**. |
| Backend (Laravel 13) | `IN PROGRESS` | `GET /api/health`, log redaction, PHPUnit tests. **Schema (M1), merged:** ARC-03 §4–§5 (12 identity and trading-configuration tables, PR #13), §6 market data (9 tables + `trading_preferences.universe_id` FK, PR #14) and §7 analysis (ruleset versions, candle snapshots, analysis batches/runs, swing points, structure events, price zones, liquidity events, detected setups, AI explanations) with immutability triggers (PR #15). **Merged (PR #17):** §8 trading (watchlists, trade plans, paper and actual trades, journal, backtests, notifications) and single-writer role grants (`apply_role_grants()`; new tables stay closed to the runtime roles until listed). 60 backend tests incl. 55 database tests. **Seeders (T-102, merged, PR #19):** `pa-core 0.1.0` ruleset, six universes, DEMO data source, 36 demo equities + 3 NSE index instruments, DEMO universe, one backfill run and 8,640 generated demo candles (PHP port of `frontend/src/mocks`, bar-for-bar parity test). Run with `make seed` (schema-owner role, idempotent). 67 backend tests. **Not yet:** domain modules, `/api/v1` endpoints. |
| Python engine | `IN PROGRESS` (skeleton + contract) | FastAPI `/health` and authenticated `/internal/v1/ping`, arq worker settings, structured logging. **T-104 (branch):** `app/schemas` (13 contract models for the ARC-08 §5 internal API, exported to `contracts/engine/`), `app/db/tables.py` (32-table SQLAlchemy read model) and a schema-diff test against the Laravel-migrated database; SQLAlchemy 2.1 added. 23 tests (+1 DB test that CI runs). `app/domain/` is empty. **No trading logic, providers or ingestion.** |
| Contracts (`contracts/`) | `IN PROGRESS` | **T-103 (branch):** `contracts/api/openapi.yaml`, OpenAPI 3.1, all 88 ARC-04 operations tagged `x-arc04-id`, 110 schemas (enums taken from the migrated schema), shared error responses. Redocly lint is clean. `contracts/scripts/check_arc04_coverage.py` (with unit tests) fails CI if ARC-04 and the spec differ; `contracts-ci.yml` is wired into `ci-gate`. Payloads ARC-04 leaves open (backtest metrics, exposure, entity, …) are deliberately loose until the M6 contract tests. `contracts/engine/` (13 JSON Schemas from Pydantic, T-104) with a stale-export check in `python-engine-ci.yml`. |
| Infrastructure | `COMPLETED` (local dev) | Docker Compose with frontend, backend (php-fpm + nginx), queue worker, scheduler, engine, engine worker, PostgreSQL 17 and Redis 7.4, all with health checks. Dev overlay with hot reload. Makefile. `scripts/setup-env.sh`. No staging or production environments. |
| GitHub CI | `COMPLETED` (M0 gates) | `ci.yml` coordinator with path filters, semantic PR titles and the `ci-gate` job. Component workflows: frontend (lint, typecheck, test, build), backend (pint, migrate, phpunit), python-engine (ruff, mypy, pytest), docker-build (build + Compose smoke), security-scan (gitleaks, dependency audits). |
| GitHub settings | `COMPLETED` | "Protect Main" ruleset (PR required, `ci-gate` required and strict, linear history, no force-push or deletion, threads resolved); squash-only merges; auto-delete branches; secret scanning + push protection; Dependabot security updates; CodeQL runs on `main`. |
| CD / deployment | `NOT STARTED` | Phases 2–4 of [ENG-10 §11](docs/engineering/10_GITHUB_ACTIONS_CI_CD.md#11-environments-and-deployment-evolution). |

## Completed milestones

| Milestone | Date | Evidence |
|---|---|---|
| Phase 1 frontend + Phase 2 documentation imported | 2026-11-15 | commit `427de44` |
| M0 — repository, Docker, CI foundation | 2026-11-15 | PR #1 (`43c37bd`, `4103ee7`) |

## Work in progress

- Branch `feature/m1-engine-contracts-and-ci-hardening`: **T-104** (engine contract and read model), **T-105** (CI gates, ruleset check) and **T-901** (Action pinning) — committed locally, PR pending. Groww decision deferred (OQ-INT-04, T-203) and T-102 seeders are merged (PR #19).
- Local dev databases created before PR #13 must be recreated (`make reset`), because the stock Laravel `users` migration was replaced (UUID ids, no `name`, no sessions table). After that, `make migrate` then `make seed`. Note: `make migrate` runs the prebuilt image, so run `make build` (or use the dev overlay) after pulling new migrations.

## Immediate next task

**Open the PR for the M1 batch** (T-104, T-105, T-901), then choose the next milestone: M3 can start now (TRD-02 pivots on fixtures); M2 needs the Kite/Groww decisions (T-201/T-203) — see [TASKS.md](TASKS.md).

## Known blockers

| Blocks | Item |
|---|---|
| M2 | OQ-INT-01/02 — Kite Connect limits, token expiry, price adjustment and terms not verified. OQ-SEC-01 — Kite app model. Kite developer app needed. OQ-INT-04 — Groww vs Kite as first provider (deferred to M2, T-203). |
| M8 | OQ-AI-01 — LLM provider/model not chosen. |
| M9–M10 | OQ-BT-01/03 — point-in-time NIFTY 500 membership and corporate-action data sources. |

## Pending decisions and inconsistencies

| Item | Detail |
|---|---|
| Repo visibility | [ENG-09 §6](docs/engineering/09_GITHUB_REPOSITORY_STRATEGY.md#6-repository-settings) specifies **Private**; the GitHub repository is currently **public**. Owner to decide; then align the doc or the setting. |
| Ruleset merge methods | The ruleset allows merge/squash/rebase, but repo settings disable merge commits and linear history is required. Effective behaviour is squash or rebase. ENG-09 says squash only. Low impact. |
| Action pinning | Third-party Actions are pinned by major tag, not commit SHA (ENG-09 §6 asks for SHA). Known follow-up from M0. |
| Risk defaults | OQ-RM-04 — UI (6 positions / 2% heat) vs onboarding (5) vs spec (5 / 5% / 25%). |
| Test tooling vs ENG-07 | ENG-07 §2 names Pest, Larastan and import-linter. The backend actually uses PHPUnit 12, and none of the three tools exists yet. Owner to decide: align ENG-07 to PHPUnit, or adopt Pest. |
| Docs CI | ENG-10 §2.2 describes a `docs-lint` job (markdown lint, link check). `ci.yml` has none. A local link checker now exists (`.claude/skills/docs-sync/scripts/check_links.py`) and could back that job. |
| Priority open questions | [DOCUMENTATION_STATUS §3](docs/DOCUMENTATION_STATUS.md#3-priority-open-questions-block-upcoming-milestones); 61 total in §2. |
