# TASKS — Development Task Register

Actionable work only. Milestone scope is in [ENG-01](docs/engineering/01_IMPLEMENTATION_ROADMAP.md). Add tasks when they become actionable, not speculatively. Move a task to Completed only after its acceptance criteria are **verified** (tests run, behaviour checked).

Priority: `P0` blocks the next milestone · `P1` needed in the current milestone · `P2` follow-up.
Status: `NOT STARTED` · `IN PROGRESS` · `COMPLETED` · `BLOCKED` · `NEEDS REVIEW`.

## Ready

| ID | Task | Pri | M | Depends on | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-103 | `contracts/api/openapi.yaml` derived from ARC-04, with OpenAPI lint in CI | P0 | M1 | — | Spec validates in CI; every ARC-04 endpoint ID present | NOT STARTED |
| T-104 | Engine Pydantic models + exported `contracts/engine/*.json` schemas; SQLAlchemy table definitions (`python-engine/app/db/tables.py`) | P0 | M1 | T-101d | Pydantic models and JSON Schemas exported; engine read model matches the migrated schema (schema-diff test) | NOT STARTED |
| T-105 | Add M1 required checks: `backend / migrations`, `backend / tests`, `python-engine / tests` covered by `ci-gate` | P1 | M1 | T-101d, T-104 | Checks run on PRs touching backend/engine; documented in ENG-10 §10 | NOT STARTED |

## Backlog

| ID | Task | Pri | M | Depends on | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-201 | Kite Connect verification spike: historical limits, rate limits, token expiry, price adjustment, personal vs multi-user terms | P0 | M2 | Kite developer app | Findings recorded in ARC-08; OQ-INT-01/02 resolved or re-scoped | BLOCKED (needs Kite app) |
| T-203 | Compare Groww API with Kite as first real data provider: historical daily candles, instrument master, rate limits, cost, terms (OQ-INT-04) | P1 | M2 | Groww API access (owner) | Findings in ARC-08; owner picks provider; ADR-007 note or new ADR per CLAUDE.md §8; OQ-INT-04 closed | NOT STARTED |
| T-202 | Owner decision on Kite app model (platform app vs bring-your-own key) | P0 | M2 | T-201 | Decision recorded as an ADR + DECISIONS.md row; OQ-SEC-01 closed | NOT STARTED |
| T-301 | Owner decision on canonical risk defaults (OQ-RM-04) | P1 | M6 | — | TRD-05 defaults confirmed; UI/onboarding values listed as discrepancies to fix in M7 | NOT STARTED |
| T-901 | Pin third-party GitHub Actions by commit SHA (M0 follow-up) | P2 | M0 | — | All non-GitHub-owned `uses:` pinned by SHA; Dependabot still updates them | NOT STARTED |
| T-903 | Error boundaries for `(auth)` and `onboarding`; request id on `ErrorState` from the typed `ApiError` (ENG-02 D-20 remainder) | P2 | M7 | HTTP adapter | Every route group has `error.tsx`; request id shown | NOT STARTED |
| T-902 | Resolve repository visibility mismatch (ENG-09 says private; GitHub repo is public) | P2 | M0 | Owner decision | Setting and ENG-09 agree | NOT STARTED |

## In Progress

None.

## Blocked

See T-201 (needs a Kite developer app).

## Completed

| ID | Task | M | Verified |
|---|---|---|---|
| T-102 | Seeders: ruleset `pa-core 0.1.0` (ACTIVE, HYPOTHESIS), six universes, DEMO data source, 36 demo equities + 3 NSE indices, DEMO universe membership, one backfill ingestion run and 8,640 generated demo candles (PHP port of `frontend/src/mocks`, parity-tested); `make seed` | M1 | 2026-11-17 (verified locally: 67 backend tests; seeded twice on a fresh DB; PR pending) |
| T-003 | Adopt `docs/design-standards.md` across the frontend (ADR-013) | — | 2026-11-16 (PR #18 merged) |
| T-101d | Migrations for ARC-03 §8 trading (12 tables) and per-table writer grants (`apply_role_grants()`) | M1 | 2026-11-16 (PR #17 merged) |
| T-002 | Project Claude Code skills in `.claude/skills/` + CLAUDE.md §10 index | — | 2026-11-16 (PR #16 merged) |
| T-101c | Migrations for ARC-03 §7 analysis (9 tables) with immutability triggers | M1 | 2026-11-16 (PR #15 merged) |
| T-101b | Migrations for ARC-03 §6 market data (9 tables) + `trading_preferences.universe_id` FK | M1 | 2026-11-16 (PR #14 merged) |
| T-101a | Migrations for ARC-03 §4–§5 (12 identity and trading-configuration tables) with constraint tests | M1 | 2026-11-16 (PR #13 merged) |
| T-001 | Project-control documentation (CLAUDE, CURRENT, ROADMAP, DECISIONS, TASKS, CHANGELOG, CONTRIBUTING) and stale-line fixes in `docs/` | — | 2026-11-16 (PR #12 merged; link check clean) |
| T-000 | M0 foundation: Compose stack with health checks, Laravel/FastAPI skeletons, CI workflows + `ci-gate`, PR/issue templates, CODEOWNERS, Dependabot, "Protect Main" ruleset | M0 | 2026-11-15 (PR #1; ruleset and settings checked via GitHub API 2026-11-16) |
