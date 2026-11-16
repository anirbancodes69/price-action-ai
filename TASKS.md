# TASKS — Development Task Register

Actionable work only. Milestone scope is in [ENG-01](docs/engineering/01_IMPLEMENTATION_ROADMAP.md). Add tasks when they become actionable, not speculatively. Move a task to Completed only after its acceptance criteria are **verified** (tests run, behaviour checked).

Priority: `P0` blocks the next milestone · `P1` needed in the current milestone · `P2` follow-up.
Status: `NOT STARTED` · `IN PROGRESS` · `COMPLETED` · `BLOCKED` · `NEEDS REVIEW`.

## Ready

| ID | Task | Pri | M | Depends on | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-I05 | TRD-04 for intraday: opening range breakout, previous-day high/low break, S/R breakout-retest (MVP); trend continuation and sweep reversal specified as later; session context; expiry within the session; NO_TRADE | P0 | I0 | T-I03 | Each setup has definition, confirmation, invalidation, levels and vectors with boundary cases | NOT STARTED |
| T-I06 | TRD-05 for intraday: sizing from stop distance with the ₹ position cap; daily loss, consecutive-loss, open-positions and open-risk limits; end-of-day exit; intraday cost schedule (to verify) | P0 | I0 | T-I03 | Worked examples for ₹1,00,000 / ₹50,000 / 0.5%; every limit has a block rule and error code; replaces OQ-RM-04 (T-301) | NOT STARTED |
| T-I07 | TRD-06 and TRD-07 for intraday: bar replay, session rules, same-bar collision, end-of-day exit, slippage, costs, out-of-sample and walk-forward; candle-close paper trading | P1 | I0 | T-I05, T-I06 | Specs and TRD-08 vectors updated | NOT STARTED |
| T-I08 | Product documents for ADR-014: vision, BRD, PRD, PRD-06 feature catalog, PRD-07 pages (intraday dashboard, scanner, analysis, planner, active trades) | P1 | I0 | T-I01 | Product docs describe the intraday personal scope; deferred SaaS features marked | NOT STARTED |
| T-I09 | I1 expand migrations per ADR-015 (bar timestamps, timeframes, timestamp columns, snapshot by reference, risk state, NSE calendar seed); contracts and `tables.py` | P0 | I1 | T-I02, T-I04..T-I06 | Fresh DB migrates and seeds; all contract and schema checks green | NOT STARTED |

## Backlog

| ID | Task | Pri | M | Depends on | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-201 | Kite Connect verification spike for intraday: minute-bar history depth per request and overall, rate limits, quote/ticker access, token expiry, personal-use terms | P0 | I2 | Kite developer app | Findings recorded in ARC-08; OQ-INT-01/02 resolved or re-scoped | BLOCKED (needs Kite app) |
| T-203 | Compare Groww API with Kite as first real data provider: historical daily candles, instrument master, rate limits, cost, terms (OQ-INT-04) | P0 | I2 | Groww API access (owner) | Findings in ARC-08; owner picks provider; ADR-007 note or new ADR per CLAUDE.md §8; OQ-INT-04 closed | NOT STARTED |
| T-202 | Owner decision on Kite app model (platform app vs bring-your-own key) | P0 | I2 | T-201 | Decision recorded as an ADR + DECISIONS.md row; OQ-SEC-01 closed | NOT STARTED |
| T-903 | Error boundaries for `(auth)` and `onboarding`; request id on `ErrorState` from the typed `ApiError` (ENG-02 D-20 remainder) | P2 | M7 | HTTP adapter | Every route group has `error.tsx`; request id shown | NOT STARTED |
| T-902 | Resolve repository visibility mismatch (ENG-09 says private; GitHub repo is public) | P2 | M0 | Owner decision | Setting and ENG-09 agree | NOT STARTED |

## In Progress

None.

## Blocked

See T-201 (needs a Kite developer app).

## Completed

| ID | Task | M | Verified |
|---|---|---|---|
| T-901 | Pin third-party GitHub Actions by commit SHA: `shivammathur/setup-php`, `astral-sh/setup-uv`, `gitleaks/gitleaks-action`, `dorny/paths-filter`, `docker/setup-buildx-action` (GitHub-owned `actions/*` stay on tags per ENG-09 §6) | M0 | 2026-11-17 (every SHA resolved from its release tag through the GitHub API; all workflows parse; Dependabot `github-actions` keeps them current; CI pending) |
| T-105 | M1 required checks: every M1 gate enforced through `ci-gate` and documented as built in ENG-10 §10; `ci-gate` hardened (only `success`/`skipped` pass, `changes` must succeed, PR title must succeed on PRs); migration PRs now trigger the engine schema-diff; ruleset `pa-core 0.1.0` copied to `python-engine/rulesets/` with a CI check that engine file, seeder file and TRD-01 §6 are identical | M1 | 2026-11-17 (gate script simulated in 6 scenarios; 13 contract-script tests; PHP and Python hashes equal; CI pending) |
| T-I04 | TRD-02 v0.2.0 (per-timeframe parameters, confirmation time, 15m→5m alignment without look-ahead, sessions, repainting checklist) and TRD-03 v0.2.0 (lookback in sessions, 15m pivots in 5m zones, intraday strength, 1-close zone break, session reference levels PDH/PDL/PDC/OR/session high-low); TRD-08 vectors TV-HTF, TV-SES, TV-REF, TV-ZON-09/10 | I0 | 2026-11-17 (spec) |
| T-I03 | TRD-01 v0.2.0 for intraday: scope, MP-02/03 rewritten, MP-10 (higher-timeframe alignment), MP-11 (session-bounded), §4.1 session conventions, `pa-intraday 0.1.0` registry (41 parameters) with engine and seeder JSON copies, `pa-core` registry moved to Appendix A, OQ-TRD-04..06; ruleset check now accepts timeframe-suffixed keys | I0 | 2026-11-17 (ruleset check OK for both rulesets; 14 checker tests) |
| T-I02 | ADR-015 intraday time model and snapshots by reference; ARC-03 §2.2 target schema, ARC-04 §2.9 time conventions, ENG-05 §12 intraday ingestion; DEC-017 | I0 | 2026-11-17 (spec only; implemented by T-I09) |
| T-I01 | ADR-014 personal intraday workstation: DECISIONS DEC-016, ADR index, CLAUDE.md §1, ROADMAP (I0–I8, M1 completed), ENG-01 §0, CURRENT, TASKS, DOCUMENTATION_STATUS §0 | I0 | 2026-11-17 (owner decisions: bearish informational, daily as context, NIFTY 50; link check clean) |
| T-104 | Engine Pydantic contract models (13, `app/schemas`) exported to `contracts/engine/*.json`; SQLAlchemy read model `app/db/tables.py` (32 tables); schema-diff test; `export_engine_schemas.py --check` and a `schema-diff` job in `python-engine-ci.yml` | M1 | 2026-11-17 (23 engine tests, ruff/format/mypy clean; schema-diff 4/4 against a freshly migrated DB and caught an injected type and nullability drift; CI pending) |
| T-103 | `contracts/api/openapi.yaml` derived from ARC-04 (88 operations, `x-arc04-id`), Redocly lint + ARC-04 coverage check in `contracts-ci.yml` (wired into `ci-gate`) | M1 | 2026-11-17 (lint clean, coverage 88/88, checker tests 6/6 locally; PR pending) |
| T-102 | Seeders: ruleset `pa-core 0.1.0` (ACTIVE, HYPOTHESIS), six universes, DEMO data source, 36 demo equities + 3 NSE indices, DEMO universe membership, one backfill ingestion run and 8,640 generated demo candles (PHP port of `frontend/src/mocks`, parity-tested); `make seed` | M1 | 2026-11-17 (verified locally: 67 backend tests; seeded twice on a fresh DB; PR #19 merged) |
| T-003 | Adopt `docs/design-standards.md` across the frontend (ADR-013) | — | 2026-11-16 (PR #18 merged) |
| T-101d | Migrations for ARC-03 §8 trading (12 tables) and per-table writer grants (`apply_role_grants()`) | M1 | 2026-11-16 (PR #17 merged) |
| T-002 | Project Claude Code skills in `.claude/skills/` + CLAUDE.md §10 index | — | 2026-11-16 (PR #16 merged) |
| T-101c | Migrations for ARC-03 §7 analysis (9 tables) with immutability triggers | M1 | 2026-11-16 (PR #15 merged) |
| T-101b | Migrations for ARC-03 §6 market data (9 tables) + `trading_preferences.universe_id` FK | M1 | 2026-11-16 (PR #14 merged) |
| T-101a | Migrations for ARC-03 §4–§5 (12 identity and trading-configuration tables) with constraint tests | M1 | 2026-11-16 (PR #13 merged) |
| T-001 | Project-control documentation (CLAUDE, CURRENT, ROADMAP, DECISIONS, TASKS, CHANGELOG, CONTRIBUTING) and stale-line fixes in `docs/` | — | 2026-11-16 (PR #12 merged; link check clean) |
| T-000 | M0 foundation: Compose stack with health checks, Laravel/FastAPI skeletons, CI workflows + `ci-gate`, PR/issue templates, CODEOWNERS, Dependabot, "Protect Main" ruleset | M0 | 2026-11-15 (PR #1; ruleset and settings checked via GitHub API 2026-11-16) |
