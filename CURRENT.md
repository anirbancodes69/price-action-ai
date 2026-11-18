# CURRENT — Project State

Last verified: **2026-11-17** against the repository (`main` at `a680643`; intraday restructuring on branch `docs/intraday-direction-and-specs`).

Status vocabulary: `NOT STARTED` · `IN PROGRESS` · `COMPLETED` · `BLOCKED` · `NEEDS REVIEW`.
Update this file at the end of every substantial task, based only on verified state.

## Phase and milestone

| Item | Value |
|---|---|
| Phase | Foundation and M1 complete. **Direction changed to a personal intraday workstation** ([ADR-014](docs/adr/ADR-014-PERSONAL-INTRADAY-WORKSTATION.md)); specifications being restructured (I0) |
| Last completed milestone | **M1** — database and contracts (PRs #13–#15, #17, #19–#21; 2026-11-17) |
| Current milestone | **Intraday restructuring complete on branch** `docs/intraday-direction-and-specs` (one PR): I0 specs, I1 schema/contracts and the frontend restructure (part of I6) — `NEEDS REVIEW`. Next after merge: I2 market data (needs the provider decision) or I3 engine core |
| Detailed plan | [ROADMAP.md](ROADMAP.md) → [ENG-01](docs/engineering/01_IMPLEMENTATION_ROADMAP.md) |

## Component status

| Area | Status | What actually exists |
|---|---|---|
| Frontend UI | `COMPLETED` (Phase 1, mock data) | Next.js 16.4.6, React 19, Tailwind v4, Lightweight Charts v5. Routes: auth (login/register/forgot-password), onboarding, dashboard, market-scanner, analysis, watchlists, trade-plans, portfolio, journal, backtesting, settings. Vitest unit tests for format, labels, colours, auth validation and scanner filters (25). |
| Frontend design system | `COMPLETED` (PR #18) | [docs/design-standards.md](docs/design-standards.md) adopted ([ADR-013](docs/adr/ADR-013-DESIGN-STANDARDS.md)): OKLCH tokens with PriceAction brand values, light/dark/system themes (dark default), shared components and `lib/colors.ts`, every screen refactored, `(app)/error.tsx`. Verified locally (lint, typecheck, tests, build, screenshots in both themes at three widths, WCAG AA contrast). Implementation and deviations: [ENG-02 §11](docs/engineering/02_FRONTEND_ARCHITECTURE.md#11-design-system). |
| Frontend data | **Mock only** (intraday model) | Every page reads the `DataSource` mock adapter (`frontend/src/lib/data`). Restructured for intraday (T-I10): 5m/15m sample bars equal to the seeded DEMO bars (parity test), a 14:00 IST sample snapshot, session levels, 15m context, signal validity, today's risk per book. Setups still come from a daily demo heuristic (`src/mocks/demo-analysis.ts`), **not** the trading rules. Login accepts any well-formed email and password. No mutation client yet. |
| Frontend ↔ spec | `NEEDS REVIEW` | 24 known discrepancies (D-01..D-24) in [ENG-02 §9](docs/engineering/02_FRONTEND_ARCHITECTURE.md#9-discrepancy-register), to be resolved in M7 (D-20 partly resolved by the design-standards work, PR #18). |
| Claude Code skills | `COMPLETED` (PR #16) | 8 project skills in `.claude/skills/` (price-action-domain, quant-engine, market-data, schema-and-contracts, frontend-ui, security-guardrails, quality-gate, docs-sync). They are workflows that link to the specs, plus two stdlib scripts (docs impact mapping, relative link and anchor check). Indexed in CLAUDE.md §10. No agents and no `.claude/settings.json`. |
| Documentation | `NEEDS REVIEW` (intraday restructuring done on branch) | 58 spec files, the design standards and 15 ADRs. The trading specs (TRD-01..08) and product documents describe the intraday direction; ARC-05, parts of ARC-01, the remaining ARC-03 §4–§8 text and ARC-04 endpoint shapes are revised with I1/I2 (DOCUMENTATION_STATUS §0). Most of the target system is **not implemented**. |
| Backend (Laravel 13) | `IN PROGRESS` | **Intraday migration (T-I09, branch):** `2026_11_17_000001` moves the schema to the ADR-015 time model; seeders activate `pa-intraday`, seed the calendar mechanism (NSE holidays not loaded, labelled unverified) and DEMO 5m/15m bars; 75 backend tests. `GET /api/health`, log redaction, PHPUnit tests. **Schema (M1), merged:** ARC-03 §4–§5 (12 identity and trading-configuration tables, PR #13), §6 market data (9 tables + `trading_preferences.universe_id` FK, PR #14) and §7 analysis (ruleset versions, candle snapshots, analysis batches/runs, swing points, structure events, price zones, liquidity events, detected setups, AI explanations) with immutability triggers (PR #15). **Merged (PR #17):** §8 trading (watchlists, trade plans, paper and actual trades, journal, backtests, notifications) and single-writer role grants (`apply_role_grants()`; new tables stay closed to the runtime roles until listed). 60 backend tests incl. 55 database tests. **Seeders (T-102, merged, PR #19):** `pa-core 0.1.0` ruleset, six universes, DEMO data source, 36 demo equities + 3 NSE index instruments, DEMO universe, one backfill run and 8,640 generated demo candles (PHP port of `frontend/src/mocks`, bar-for-bar parity test). Run with `make seed` (schema-owner role, idempotent). 67 backend tests. **Not yet:** domain modules, `/api/v1` endpoints. |
| Python engine | `IN PROGRESS` (skeleton + contract) | FastAPI `/health` and authenticated `/internal/v1/ping`, arq worker settings, structured logging. **T-104 (PR #21):** `app/schemas` (13 contract models for the ARC-08 §5 internal API, exported to `contracts/engine/`), `app/db/tables.py` (32-table SQLAlchemy read model) and a schema-diff test against the Laravel-migrated database; SQLAlchemy 2.1 added. 23 tests (+1 DB test that CI runs). `app/domain/` has types, `RulesetParams`, pivots and labels, the structure machine, 15m→5m alignment, candle validation and canonical hashing (T-I22..I27; no zones, setups or `analyse` yet). **Branch `feature/kite-market-data-provider` (I2 start):** `app/providers` with the `MarketDataProvider` protocol, normalised bar/instrument types and errors, and a `KiteProvider` (REST via httpx: instrument master, 5m/15m/1D bars, JIT token, error mapping); `DemoProvider` (deterministic sample 5m/15m bars), the NSE session grid and intraday bar quality checks (`app/ingestion`); rate limiter and retries, the bar-close fetcher (in-memory store) and the Redis current-price cache with Kite/DEMO `fetch_ltp` (60 engine tests pass; ruff, mypy clean; all offline). Also: migration `2026_11_18_000001` (intraday quality-issue types), the Postgres writer (runs, idempotent candle upsert, quality issues) and the bar-close scheduler core (71 engine tests incl. 4 DB integration tests, 76 backend tests). Still missing for I2: arq cron wiring (needs the NIFTY 50 universe loader and the Kite token supplier), session-end reconciliation and stale-run recovery, NSE holidays, verification against real Kite. Endpoint shapes, history depth and rate limits are **unverified** (T-201 needs a Kite app); no live call was made. **Trading logic: pivots and structure only.** |
| Contracts (`contracts/`) | `NEEDS REVIEW` (intraday, on branch) | `contracts/api/openapi.yaml` 0.2.0: 90 operations incl. R2 `GET /risk/today` and X11 `GET /positions/live`, intraday shared schemas (timestamps, 15m context, session levels, signal validity), TRD-05 risk shape; Redocly clean; ARC-04 coverage check. `contracts/engine/` 13 JSON Schemas (risk sizing with account state and session clock, analysis by bar close). Ruleset check covers `pa-core` and `pa-intraday`. |
| Infrastructure | `COMPLETED` (local dev) | Docker Compose with frontend, backend (php-fpm + nginx), queue worker, scheduler, engine, engine worker, PostgreSQL 17 and Redis 7.4, all with health checks. Dev overlay with hot reload. Makefile. `scripts/setup-env.sh`. No staging or production environments. |
| GitHub CI | `COMPLETED` (M0 gates) | `ci.yml` coordinator with path filters, semantic PR titles and the `ci-gate` job. Component workflows: frontend (lint, typecheck, test, build), backend (pint, migrate, phpunit), python-engine (ruff, mypy, pytest), docker-build (build + Compose smoke), security-scan (gitleaks, dependency audits). |
| GitHub settings | `COMPLETED` | "Protect Main" ruleset (PR required, `ci-gate` required and strict, linear history, no force-push or deletion, threads resolved); squash-only merges; auto-delete branches; secret scanning + push protection; Dependabot security updates; CodeQL runs on `main`. |
| CD / deployment | `NOT STARTED` | Phases 2–4 of [ENG-10 §11](docs/engineering/10_GITHUB_ACTIONS_CI_CD.md#11-environments-and-deployment-evolution). |

## Completed milestones

| Milestone | Date | Evidence |
|---|---|---|
| Phase 1 frontend + Phase 2 documentation imported | 2026-11-15 | commit `427de44` |
| M0 — repository, Docker, CI foundation | 2026-11-15 | PR #1 (`43c37bd`, `4103ee7`) |
| M1 — database and contracts | 2026-11-17 | PRs #13–#15, #17, #19, #20, #21 (`a680643`) |

## Work in progress

- Branch `docs/intraday-direction-and-specs` (whole restructuring, one PR at the end): I0 specs (ADR-014/015, TRD-01..08, product docs, ARC-05/ARC-01), I1 (T-I09: intraday migration, seeders, engine contracts, read model, OpenAPI 0.2.0) and the frontend restructure on sample data (T-I10).
- Local dev databases created before PR #13 must be recreated (`make reset`), because the stock Laravel `users` migration was replaced (UUID ids, no `name`, no sessions table). After that, `make migrate` then `make seed`. Note: `make migrate` runs the prebuilt image, so run `make build` (or use the dev overlay) after pulling new migrations.

## Immediate next task

Open and merge the restructuring PR (title in the last hand-off). Then: owner decisions OQ-TRD-04 (risk defaults) and the provider (T-201/T-203); load the NSE holiday list into `backend/database/seeders/data/nse-market-calendar.json`; start **I3** (engine core on fixtures) or **I2** (market data, once the provider is chosen).

## Known blockers

| Blocks | Item |
|---|---|
| I2 | Kite Connect app active (owner, 2026-11-18); per-request limits and depth verified (ARC-08 §4.0). Still open: OQ-INT-01 rate limit, forming bar, token expiry and terms; OQ-INT-02 price adjustment; OQ-SEC-01 app model. OQ-INT-04: Kite chosen for now, Groww comparison deferred. |
| (deferred) | OQ-AI-01 — LLM provider/model not chosen; AI explanations are deferred by ADR-014. |
| I8 | Intraday history depth and quality for NIFTY 50; corporate-action source (OQ-BT-03). Point-in-time NIFTY 500 membership (OQ-BT-01) no longer blocks the MVP. |

## Pending decisions and inconsistencies

| Item | Detail |
|---|---|
| Repo visibility | [ENG-09 §6](docs/engineering/09_GITHUB_REPOSITORY_STRATEGY.md#6-repository-settings) specifies **Private**; the GitHub repository is currently **public**. Owner to decide; then align the doc or the setting. |
| Ruleset merge methods | The ruleset allows merge/squash/rebase, but repo settings disable merge commits and linear history is required. Effective behaviour is squash or rebase. ENG-09 says squash only. Low impact. |
| Risk defaults | OQ-RM-04 is replaced by the owner's intraday planning values in ADR-014 (₹1,00,000 capital, ₹50,000 per position, 0.5% risk; daily loss and streak limits configurable). TRD-05 is revised in I0; the UI values are fixed in I6. |
| Test tooling vs ENG-07 | ENG-07 §2 names Pest, Larastan and import-linter. The backend actually uses PHPUnit 12, and none of the three tools exists yet. Owner to decide: align ENG-07 to PHPUnit, or adopt Pest. |
| Docs CI | ENG-10 §2.2 describes a `docs-lint` job (markdown lint, link check). `ci.yml` has none. A local link checker now exists (`.claude/skills/docs-sync/scripts/check_links.py`) and could back that job. |
| Priority open questions | [DOCUMENTATION_STATUS §3](docs/DOCUMENTATION_STATUS.md#3-priority-open-questions-block-upcoming-milestones); 61 total in §2. |
