# TASKS — Development Task Register

Actionable work only. Milestone scope is in [ENG-01](docs/engineering/01_IMPLEMENTATION_ROADMAP.md). Add tasks when they become actionable, not speculatively. Move a task to Completed only after its acceptance criteria are **verified** (tests run, behaviour checked).

Priority: `P0` blocks the next milestone · `P1` needed in the current milestone · `P2` follow-up.
Status: `NOT STARTED` · `IN PROGRESS` · `COMPLETED` · `BLOCKED` · `NEEDS REVIEW`.

## Ready

| ID | Task | Pri | M | Depends on | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-101b | Migrations for ARC-03 §6 market data (instruments, provider refs, snapshots, universes + memberships, candles with OHLC checks, corporate actions, ingestion runs, quality issues, market calendar); add FK `trading_preferences.universe_id → universes` | P0 | M1 | T-101a | Migrate/rollback clean; constraint tests (OHLC validity, effective-date exclusion, duplicate-run guard) pass | NOT STARTED |
| T-101c | Migrations for ARC-03 §7 analysis (ruleset_versions, candle_snapshots, analysis_batches/runs, swing/structure/zone/liquidity children, detected_setups, ai_explanations) | P0 | M1 | T-101b | Same as T-101b, incl. immutability and unique-run constraints | NOT STARTED |
| T-101d | Migrations for ARC-03 §8 trading (watchlists, trade_plans with long-only and stop < entry < target checks, paper/actual trades, journal, backtests, notifications) + per-table writer grants (ARC-01 §6) | P0 | M1 | T-101c | Same as T-101b; role-grant test for single-writer tables | NOT STARTED |
| T-102 | Seeders: ruleset `pa-core 0.1.0`, universes, DEMO data source, demo instruments and candles ported from `frontend/src/mocks` | P0 | M1 | T-101d | Fresh DB migrates and seeds; demo data flagged DEMO | NOT STARTED |
| T-103 | `contracts/api/openapi.yaml` derived from ARC-04, with OpenAPI lint in CI | P0 | M1 | — | Spec validates in CI; every ARC-04 endpoint ID present | NOT STARTED |
| T-104 | Engine Pydantic models + exported `contracts/engine/*.json` schemas; SQLAlchemy table definitions (`python-engine/app/db/tables.py`) | P0 | M1 | T-101d | Schemas export reproducibly; schema-diff test (Laravel migrations vs engine tables) passes | NOT STARTED |
| T-105 | Add M1 required checks: `backend / migrations`, `backend / tests`, `python-engine / tests` covered by `ci-gate` | P1 | M1 | T-101d, T-104 | Checks run on PRs touching backend/engine; documented in ENG-10 §10 | NOT STARTED |

## Backlog

| ID | Task | Pri | M | Depends on | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-201 | Kite Connect verification spike: historical limits, rate limits, token expiry, price adjustment, personal vs multi-user terms | P0 | M2 | Kite developer app | Findings recorded in ARC-08; OQ-INT-01/02 resolved or re-scoped | BLOCKED (needs Kite app) |
| T-202 | Owner decision on Kite app model (platform app vs bring-your-own key) | P0 | M2 | T-201 | Decision recorded as an ADR + DECISIONS.md row; OQ-SEC-01 closed | NOT STARTED |
| T-301 | Owner decision on canonical risk defaults (OQ-RM-04) | P1 | M6 | — | TRD-05 defaults confirmed; UI/onboarding values listed as discrepancies to fix in M7 | NOT STARTED |
| T-901 | Pin third-party GitHub Actions by commit SHA (M0 follow-up) | P2 | M0 | — | All non-GitHub-owned `uses:` pinned by SHA; Dependabot still updates them | NOT STARTED |
| T-902 | Resolve repository visibility mismatch (ENG-09 says private; GitHub repo is public) | P2 | M0 | Owner decision | Setting and ENG-09 agree | NOT STARTED |

## In Progress

| ID | Task | Pri | M | Depends on | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-101a | Migrations for ARC-03 §4–§5 (tenants, users, memberships, profiles, onboarding, audit log, preferences, risk profiles, entitlements, provider connections, data sources, selections) | P0 | M1 | M0 | `make test-backend` green (13 tests incl. 8 schema-constraint tests); rollback + re-migrate clean; Pint clean; `audit_logs` is insert-only for runtime roles. **Verified locally 2026-11-16; awaiting PR + CI.** | NEEDS REVIEW |

## Blocked

See T-201 (needs a Kite developer app).

## Completed

| ID | Task | M | Verified |
|---|---|---|---|
| T-001 | Project-control documentation (CLAUDE, CURRENT, ROADMAP, DECISIONS, TASKS, CHANGELOG, CONTRIBUTING) and stale-line fixes in `docs/` | — | 2026-11-16 (PR #12 merged; link check clean) |
| T-000 | M0 foundation: Compose stack with health checks, Laravel/FastAPI skeletons, CI workflows + `ci-gate`, PR/issue templates, CODEOWNERS, Dependabot, "Protect Main" ruleset | M0 | 2026-11-15 (PR #1; ruleset and settings checked via GitHub API 2026-11-16) |
