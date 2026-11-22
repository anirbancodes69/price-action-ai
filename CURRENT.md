# CURRENT — Project State

Last verified: **2026-11-21** against the repository (`main` at `4e7791c`). Includes the findings of a code-level strategy audit run that day (no code changed).

Status vocabulary: `NOT STARTED` · `IN PROGRESS` · `COMPLETED` · `BLOCKED` · `NEEDS REVIEW`.
Update this file at the end of every substantial task, based only on verified state.

## Phase and milestone

| Item | Value |
|---|---|
| Phase | Personal intraday workstation ([ADR-014](docs/adr/ADR-014-PERSONAL-INTRADAY-WORKSTATION.md)). The engine produces signals on real stored Kite bars and the main workflows run over `/api/v1`, but **the rules have not shown an edge**: the first real-bar backtest lost money. |
| Last completed milestones | **I0** specifications and **I1** intraday schema and contracts (PR #22, 2026-11-17) |
| Current milestones | I2 market data, I3 engine core, I4 setups, I5 risk and trade state, I6 API and frontend, I7 journal, I8 backtesting, all `IN PROGRESS` ([ROADMAP.md](ROADMAP.md)) |
| Detailed plan | [ROADMAP.md](ROADMAP.md) → [ENG-01](docs/engineering/01_IMPLEMENTATION_ROADMAP.md) |

## Component status

| Area | Status | What actually exists |
|---|---|---|
| Frontend UI | `COMPLETED` (screens) | Next.js 16.4.6, React 19, Tailwind v4, Lightweight Charts v5. Routes: auth, onboarding (deferred, not linked), dashboard, market-scanner, analysis, watchlists, trade-plans, portfolio (Active trades), journal, backtesting, settings. 88 Vitest tests (T-I129). |
| Frontend design system | `COMPLETED` (PR #18) | [docs/design-standards.md](docs/design-standards.md) adopted ([ADR-013](docs/adr/ADR-013-DESIGN-STANDARDS.md)): OKLCH tokens, light/dark/system themes (dark default), shared components, error boundaries. Deviations: [ENG-02 §11](docs/engineering/02_FRONTEND_ARCHITECTURE.md#11-design-system). |
| Frontend data | `IN PROGRESS` (hybrid) | With `NEXT_PUBLIC_DATA_SOURCE=http`: login, session check, scanner, analysis (5m/15m/1D bars, PAQS evidence, reason codes), dashboard, watchlists, trade plans, Active trades (manual trade log, live P&L at the latest stored 5m close, HOLD/EXIT), journal and the Settings risk section use the API. Backtesting, notifications and the other settings sections stay on sample data. Several HTTP pages were not checked in a browser (see TASKS). |
| Frontend ↔ spec | `NEEDS REVIEW` | 29 discrepancies recorded in [ENG-02 §9](docs/engineering/02_FRONTEND_ARCHITECTURE.md#9-discrepancy-register) (D-01..D-29), several resolved. |
| Claude Code skills | `COMPLETED` (PR #16) | 8 project skills in `.claude/skills/`, indexed in CLAUDE.md §10. |
| Documentation | `IN PROGRESS` | Specs, the design standards and 17 ADRs. TRD-01..08 and the product documents describe the intraday direction. Feature states: [PRD-06](docs/product/06_FEATURE_CATALOG.md). |
| Backend (Laravel 13) | `IN PROGRESS` | Schema per ARC-03 with the ADR-015 time model, single-writer grants and immutability triggers; seeders (`pa-intraday 0.1.0` active, DEMO 5m/15m bars, calendar mechanism with **no holidays**). `/api/v1` personal-mode subset (ADR-016, ADR-017): owner auth (Sanctum SPA cookie), scanner and analysis (live engine proxy), `risk/calculate`, `risk/today`, risk profile, trade plans (no stored analysis runs; `plans:expire` at the entry cutoff), actual trades with fills and optional stop/target, live positions, watchlists, journal. `php artisan owner:create`, `source:create-kite`. No trading logic in PHP: sizing and limits come from the engine. 194 backend tests (T-I130). |
| Python engine | `IN PROGRESS` | **Domain** (`app/domain`): pivots and labels, structure machine (BOS, CHoCH, wick breaches), 15m→5m alignment without look-ahead, candle validation and hashing, session levels, S/R zones (clustering, break/flip, strength, proximity), equal-level pools, three long setups (OPENING_RANGE_BREAKOUT, PREV_DAY_HIGH_BREAK, BREAKOUT_RETEST; short ORB and PDL informational), target ladder, PAQS, signal mapping, risk sizing, account limits, fills, exits and the position monitor. **Not built:** volume, VWAP, candlestick patterns, trend-continuation and sweep-reversal setups, the retest short mirror. **Backtest** (`app/backtest`, `scripts/run_backtest.py`): replay with next-bar fills, costs (unverified schedule), metrics, splits, run record, zone cache. **Market data:** `KiteProvider`, `DemoProvider`, ingestion (fetcher, backfill, quality checks, scheduler, reconciliation, coverage check), `ingest_tick` cron (off unless `INGEST_ENABLED=true`, not yet run in a live session). Real Kite bars stored for NIFTY 50: 5m and 15m 2026-01-01..2026-11-19, 1D from 2026-01-01. **Internal API** `/internal/v1`: scan, analysis, risk position-size, validate-levels, account-state, positions evaluate. 268 test functions: 264 passed, 4 DB tests skipped in the container run on 2026-11-21; ruff and mypy clean at T-I133. |
| Contracts (`contracts/`) | `COMPLETED` (current scope) | `contracts/api/openapi.yaml` 0.2.0 with 91 operations, Redocly clean, ARC-04 coverage check; `contracts/engine/` 21 JSON Schemas; ruleset hash check covers `pa-core` and `pa-intraday`. |
| Infrastructure | `COMPLETED` (local dev) | Docker Compose with frontend, backend (php-fpm + nginx), queue worker, scheduler, engine, engine worker (Kite token file mounted read-only), PostgreSQL 17 and Redis 7.4, all with health checks. Dev overlay. No staging or production. |
| GitHub CI | `COMPLETED` (M0 gates) | `ci.yml` with path filters, semantic PR titles and `ci-gate`; frontend, backend, python-engine, docker-build and security-scan workflows. |
| GitHub settings | `COMPLETED` | "Protect Main" ruleset; squash-only merges; secret scanning and push protection; Dependabot; CodeQL on `main`. |
| CD / deployment | `NOT STARTED` | Phases 2–4 of [ENG-10 §11](docs/engineering/10_GITHUB_ACTIONS_CI_CD.md#11-environments-and-deployment-evolution). |

## Strategy validation state

| Item | Value |
|---|---|
| First real backtest | 2026-11-20, 55 sessions (2026-09-01..2026-11-19), `pa-intraday 0.1.0`: 176 trades, win rate 28.4%, −₹16,794 net, profit factor 0.52, −0.20R per trade before costs ([log](docs/trading/backtests/2026-11-20-pa-intraday-0.1.0-nifty50.md)) |
| By setup | BREAKOUT_RETEST 130 trades −0.48R; PREV_DAY_HIGH_BREAK 33 trades −0.27R; OPENING_RANGE_BREAKOUT 13 trades +0.10R (too few to read) |
| Best candidate | Variant D (BREAKOUT_RETEST off, min stop distance 0.7%) was about break-even on the days it was chosen on (+₹345, 48 trades) but **lost −₹13,310 over 164 earlier sessions (2026-01..08), profit factor 0.63, negative before costs**: not out-of-sample positive ([log §5](docs/trading/backtests/2026-11-20-pa-intraday-0.1.0-nifty50.md)). Not adopted |
| Sweep reversal | `LIQUIDITY_SWEEP_REVERSAL` is built and enabled only in `pa-intraday 0.2.0` (T-I141); `0.1.0` is unchanged. Not backtested yet; two spec gaps are open (OQ-SD-07 scoring of non-zone anchors, OQ-SD-08 implementation choices) |
| Stored history | NIFTY 50 5m and 15m bars for 2024-01-01..2026-11-19 (717 sessions; 498 added 2026-11-21, T-I140). Four special sessions in it (Saturdays 2024-03-02 and 2024-05-18, Muhurat 2024-11-01 and 2025-10-21) are short and need the special-session list (T-I137) before a replay |
| Next check | `pa-intraday 0.1.0` on the same 2026-01..08 bars for a baseline (remaining part of T-I134); then research on entry quality, since exits and stop distance do not create an edge |

## Strategy library programme (ADR-018, 2026-11-21)

Documentation and planning only; no strategy or production code changed. The 12-strategy roadmap, development process, isolation and validation standards, data limitations and the experiment registry are in place. Master tracker: [docs/development/strategy-development-roadmap.md](docs/development/strategy-development-roadmap.md#5-master-strategy-tracker). Verified starting state: Strategy 01 (liquidity sweep), 09 (ORB), 10 (PDH break) and 11 (breakout-retest) are `IMPLEMENTED` as long-only setups; strategy 03 has a draft specification (TRD-04 §6) and no code; 02, 04-08 have no setup code; 12 is `DEFERRED`. **No strategy has an independent backtest**, and all earlier backtests were combined runs ([registry](docs/research/experiment-registry.md)). Owner decisions recorded 2026-11-21: D-1, D-2, D-5, D-7 approved; D-3, D-4, D-6 deferred (roadmap §6). Task in progress: Strategy 01, Liquidity Sweep / Reversal (T-I142), parked 2026-11-22 (see the end of this paragraph). Specification approved 2026-11-21 (P-1..P-4, [page](docs/strategies/liquidity-sweep-reversal.md)). Stage 2 done 2026-11-21: single-strategy run mode (`--strategy`, experiments 4a and 4b) and ruleset `pa-intraday 0.3.0`; engine tests pass, ruff and mypy (`app`) clean. Stage 3 done 2026-11-21: 24 new sweep tests plus a real-bar isolation proof (`scripts/check_strategy_isolation.py`, 0 differences over 8,910 analyses). D-7 data done. Stage 4 experiment 4a in-sample done 2026-11-21 (427 sessions, 11,363 trades): win 32.5%, avg R gross -0.16 / net -0.33, PF 0.54, negative in every anchor, regime and month ([registry](docs/research/experiment-registry.md)); costs unverified (D-6), no parameter changed. Strategy 01 was parked on 2026-11-22 (owner decision, `DEFERRED`; out-of-sample and holdout data untouched; 4b not run). **Next authorised task:** Strategy 02, Failed Breakout (T-I143): the specification was approved 2026-11-22 (P-1..P-5 as written, [page](docs/strategies/failed-breakout.md)); Stage 2 built 2026-11-22 (`FAILED_BREAKDOWN_RECLAIM` detector, ruleset `pa-intraday 0.4.0`, shared `support_levels` module; 17 tests, real-bar isolation proof 0 differences); next is Stage 3 tests after the PR merges.

## Completed milestones

| Milestone | Date | Evidence |
|---|---|---|
| Phase 1 frontend + Phase 2 documentation imported | 2026-11-15 | commit `427de44` |
| M0 — repository, Docker, CI foundation | 2026-11-15 | PR #1 (`43c37bd`, `4103ee7`) |
| M1 — database and contracts | 2026-11-17 | PRs #13–#15, #17, #19, #20, #21 (`a680643`) |
| I0 — intraday direction and specifications | 2026-11-17 | PR #22 (`7bbee7e`) |
| I1 — intraday schema and contracts | 2026-11-17 | PR #22 (T-I09) |

## Work in progress

- Branch `docs/sync-project-state`: project-control docs synced with the code and the 2026-11-21 audit (ROADMAP, CURRENT, TASKS, PRD-06).
- Local dev databases created before PR #13 must be recreated (`make reset`), then `make migrate` and `make seed`. `make migrate` runs the prebuilt image, so run `make build` (or use the dev overlay) after pulling new migrations.

## Immediate next task

0. **Strategy 01 (T-I142):** audit, complete, test and independently validate Liquidity Sweep / Reversal, (roadmap approved 2026-11-21). The items below are the earlier backtest follow-ups.
1. **Out-of-sample check (T-I134):** variant D is done (negative, see above); the remaining part is `pa-intraday 0.1.0` on the same bars as a baseline. No `pa-intraday 0.2.0` proposal is justified by the evidence so far.
2. **Correctness fixes from the 2026-11-21 audit (T-I135..T-I138):** scanner signal vs risk rejection, gap check at analysis time, NSE holiday calendar, previous-day levels from the previous trading session.
3. **Owner steps:** load the NSE holiday list into `backend/database/seeders/data/nse-market-calendar.json` and check the cost schedule against Zerodha contract notes (OQ-BT-02). To run ingestion live: `scripts/kite_login.py` each trading day (token expires about 06:00 IST), `INGEST_ENABLED=true` in `.env`, `docker compose up -d engine-worker`; re-run `backfill --timeframe 1D` after each close until a daily job exists.

## Known blockers

| Blocks | Item |
|---|---|
| I2 | Kite Connect app active (owner, 2026-11-18); per-request limits and depth verified (ARC-08 §4.0). Still open: OQ-INT-01 rate limit, forming bar, token expiry and terms; OQ-INT-02 price adjustment; OQ-SEC-01 app model. OQ-INT-04: Kite chosen for now, Groww comparison deferred. |
| I2, I8 | NSE holidays not loaded: `SessionClock` treats every weekday as a session; the backtest takes sessions from days with bars. |
| I8 | Cost schedule and slippage unverified (OQ-BT-02); corporate-action source (OQ-BT-03); no point-in-time NIFTY 50 membership (OQ-BT-01), so every backtest carries survivorship risk. |
| (deferred) | OQ-AI-01 — LLM provider/model not chosen; AI explanations are deferred by ADR-014. |

## Pending decisions and inconsistencies

| Item | Detail |
|---|---|
| Scanner signal vs risk check | `analysis/scan.py` `scan_symbol` keeps `ENTRY_CONFIRMED` / `BUY_WATCH` when `calculate_risk` rejects the plan (for example `STOP_TOO_WIDE`); it only appends the error to the reasons, and Laravel passes the signal through. Stop-distance limits apply at sizing, not in `choose_signal`. Owner to decide where the fix goes (T-I135); moving it into `choose_signal` changes analysis output and needs a ruleset version. |
| Gaps at analysis time | `candles.missing_bar_starts` exists (TV-SES-03) but `analyse` never calls it, so gaps in stored bars reach pivots and structure unflagged (T-I136). |
| Previous-day levels | Built from the previous *stored* day's 5m bars, which end at 15:15 with Kite. A missing session silently shifts PDH/PDL/PDC to an older day (T-I138). |
| Unused ruleset parameters | `setup.rejection_min_wick_ratio` and `score.min_display` are in `pa-intraday 0.1.0` but no code reads them. Wire them up or drop them in the next ruleset version. |
| PAQS ordering | PAQS orders simultaneous signals, but in the first backtest it did not rank outcomes (D7 in the log). |
| Costs in live plans | `RiskResult.est_round_trip_costs` and `rr_after_costs` are always `None`; costs exist only in the backtest. |
| Not specified | No trades-per-day limit and no margin model in TRD-05. Owner to decide whether they are needed. |
| Repo visibility | [ENG-09 §6](docs/engineering/09_GITHUB_REPOSITORY_STRATEGY.md#6-repository-settings) specifies **Private**; the GitHub repository is **public**. Owner to decide; then align the doc or the setting. |
| Ruleset merge methods | The ruleset allows merge/squash/rebase, but repo settings disable merge commits and linear history is required. Effective behaviour is squash or rebase. ENG-09 says squash only. Low impact. |
| Test tooling vs ENG-07 | ENG-07 §2 names Pest, Larastan and import-linter. The backend uses PHPUnit 12, and none of the three tools exists. Owner to decide: align ENG-07 to PHPUnit, or adopt Pest. |
| Docs CI | ENG-10 §2.2 describes a `docs-lint` job. `ci.yml` has none. The local link checker (`.claude/skills/docs-sync/scripts/check_links.py`) could back it. |
| Priority open questions | [DOCUMENTATION_STATUS §3](docs/DOCUMENTATION_STATUS.md#3-priority-open-questions-block-upcoming-milestones). |
