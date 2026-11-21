# ROADMAP — Milestone Progress

High-level progress tracker. The **detailed plan** (scope, files, tests, exit criteria, dependency graph, risks) is in **[docs/engineering/01_IMPLEMENTATION_ROADMAP.md](docs/engineering/01_IMPLEMENTATION_ROADMAP.md)** (ENG-01). This file must not duplicate that plan. Update the status and date columns when a milestone's acceptance criteria are **verified**.

Status: `NOT STARTED` · `IN PROGRESS` · `COMPLETED` · `BLOCKED` · `NEEDS REVIEW`. Target dates are not set yet (OQ-RD-01).

Direction changed on 2026-11-17 to a **personal intraday workstation** ([ADR-014](docs/adr/ADR-014-PERSONAL-INTRADAY-WORKSTATION.md)). M0 and M1 stand. The daily milestones M2–M10 are superseded by the intraday milestones I0–I8 (detail in [ENG-01 §0](docs/engineering/01_IMPLEMENTATION_ROADMAP.md#0-intraday-roadmap-adr-014)). Effort ranges are solo engineering days, not dates.

| M | Milestone | Objective | Depends on | Status | Completed |
|---|---|---|---|---|---|
| M0 | Repository and infrastructure foundation | Monorepo, Compose stack skeleton, GitHub repo config and CI gates | — | `COMPLETED` | 2026-11-15 |
| M1 | Database and API contracts | ARC-03 schema, seeders, OpenAPI and engine JSON Schemas | M0 | `COMPLETED` | 2026-11-17 (PRs #13–#15, #17, #19–#21) |
| M2–M10 | Daily-timeframe roadmap | — | — | Superseded by ADR-014 (not started) | — |
| I0 | Direction and specifications | ADR-014/015, intraday TRD-01..07, product docs | M1 | `COMPLETED` | 2026-11-17 (PR #22) |
| I1 | Intraday schema and contracts | Bar timestamps, 1m/5m/15m/1D, snapshot by reference, risk state, calendar seed | I0 | `COMPLETED` (calendar seeded as a mechanism only; NSE holidays not loaded, tracked under I2) | 2026-11-17 (PR #22, T-I09) |
| I2 | Intraday market data | Provider adapter (Kite or Groww), bar-close fetcher, current-price cache, quality checks, DEMO intraday data | I1, provider access | `IN PROGRESS` (Kite chosen; adapter, DEMO provider, quality checks, fetcher, writer, scheduler, instrument sync, universe loader, token supplier, cron job, stale-run recovery, session-end reconciliation, history coverage check and backfill built. Real Kite history stored for NIFTY 50: 5m and 15m bars 2026-01-01..2026-11-19 and 1D bars from 2026-01-01 (T-I126, T-I133). Open: the bar-close cron has not run in a live session (`INGEST_ENABLED` is off), no daily 1D job, NSE holidays not loaded, OHLC/aggregate checks over the backfilled history) | — |
| I3 | Engine core on 15m/5m | Pivots, structure, BOS/CHoCH, higher-timeframe alignment | I1 | `IN PROGRESS` (pivots, labels, structure machine, 15m→5m alignment, candle validation, result hash, snapshot status and `analyse` done and tested. Acceptance not yet met: only 13 of the 103 TRD-08 vector IDs are referenced in tests and there are no property-based no-look-ahead tests (audit 2026-11-21)) | — |
| I4 | Session context and setups | Opening range, previous-day levels, S/R zones, breakout-retest, levels, NO_TRADE | I3 | `IN PROGRESS` (session levels, zones with strength and equal-level pools, OPENING_RANGE_BREAKOUT, PREV_DAY_HIGH_BREAK and BREAKOUT_RETEST long, target ladder, PAQS and NO_TRADE / BUY_WATCH / ENTRY_CONFIRMED mapping done (PR #31 onward). Open: the BREAKOUT_RETEST short mirror. Trend continuation and sweep reversal are specified but wait for validation (TRD-04 §6–7). The first real backtest found no edge, see I8) | — |
| I5 | Intraday risk and trade state | Sizing with ₹ caps, daily loss and streak limits, open risk, intraday costs, end-of-day exit | I1 | `IN PROGRESS` (engine sizing, limits, validation, fills, exits and the HOLD/EXIT position monitor done; Laravel risk calculate, risk today, risk profile, trade plans and the manual trade log persisted. Open: cost estimates in live plans (the backtest cost schedule is unverified, OQ-BT-02), a trades-per-day limit (not specified), bar-close plan status changes (ADR-017), the paper book) | — |
| I6 | API and frontend integration | `/api/v1` subset, HTTP adapter, intraday chart, polling | I2–I5 | `IN PROGRESS` (Laravel `/api/v1` personal-mode subset (ADR-016): login, scanner, analysis, risk, risk profile, trade plans, actual trades, live positions, watchlists, journal. HTTP mode in the frontend for login, scanner, analysis, dashboard, watchlists, trade plans, Active trades, journal and the Settings risk section. Open: several of these not yet checked in a browser, a full `DataSource` over HTTP for the remaining pages, notifications, the ENG-02 §9 discrepancies) | — |
| I7 | Journal and performance | Planned vs actual, net P&L, server-side stats | I6 | `IN PROGRESS` (journal of closed actual trades with notes, setup type and R-multiple when the trade followed a plan (T-I107, T-I108, T-I121). Open: server-side statistics, paper-book entries, screenshots) | — |
| I8 | Intraday backtesting | 5m bar replay, sessions, collisions, end-of-day exit, costs, out-of-sample | I3–I5, history | `IN PROGRESS` (engine library, loader and `scripts/run_backtest.py` done; first real-bar replay 2026-11-20 on 55 sessions lost −₹16,794, profit factor 0.52, no edge before costs ([log](docs/trading/backtests/2026-11-20-pa-intraday-0.1.0-nifty50.md)). Open: an out-of-sample replay on the stored 2026-01..08 bars, at least 120 sessions per run, a per-setup switch, persistence and API) | — |

## Milestone acceptance (summary)

Full acceptance and exit criteria are in ENG-01 §3.

| M | Acceptance criteria |
|---|---|
| M0 | `docker compose up` healthy; CI green on PR; `main` protected; required check `ci-gate`. **Verified:** PRs #1–#11 ran through `ci-gate`, and the "Protect Main" ruleset is active. |
| M1 | Fresh DB migrates and seeds; OpenAPI validates; engine schema matches Laravel migrations. |
| I0 | ADR-014/015 accepted; TRD-01..07 describe the intraday methodology; the documents still describing daily scope are listed in DOCUMENTATION_STATUS. |
| I1 | Fresh DB migrates and seeds with intraday timeframes; schema-diff, OpenAPI coverage and ruleset checks green. |
| I2 | One full NIFTY 50 session of 5m/15m bars ingested without gaps against the calendar; adapter tests on recorded fixtures; token never logged. |
| I3–I5 | Intraday TRD-08 vectors pass, including no-look-ahead and higher-timeframe alignment properties; risk limits block violating plans. |
| I6–I7 | MVP workflows (scan, analyse, plan, record, monitor, journal) run end to end on DEMO data, then on the provider. |
| I8 | Reproducible intraday backtests (input hash) with collision, end-of-day and cost vectors passing. |
| M2 | *(superseded)* DEMO + Kite candles ingested for NIFTY 500 with quality checks; adapter tests use recorded fixtures; token never logged. |
| M3 | TRD-02 test vectors and no-look-ahead tests pass. |
| M4 | TRD-02/03 break, zone and liquidity vectors pass. |
| M5 | Analysis runs contain setups with levels and evidence; risk endpoint matches TRD-05 examples; engine contract v1 frozen. |
| M6 | OpenAPI contract tests pass for all M6 endpoints; cross-tenant isolation matrix passes. |
| M7 | BAC-01 and BAC-03 pass end to end on DEMO data; no screen redesign. |
| M8 | US-12 passes; ≥ 90% validator pass rate on the eval set; spend cap verified. |
| M9 | BAC-04 and BAC-05 pass; gate G1 evaluated. |
| M10 | G2 conditions met; G3 workstreams owned and decisions recorded. |

## M0 notes

M0 included the GitHub repository configuration (ruleset, squash-only merges, secret scanning, Dependabot, CODEOWNERS, templates) and the GitHub Actions CI implementation. Deviations recorded in ENG-01 M0: backend and engine CI were pulled forward from M1; Trivy and Semgrep were deferred to image publishing; third-party Actions were pinned by tag at first and are now pinned by commit SHA (T-901, 2026-11-17).

## Strategy library

The intraday milestones above are being followed by a validation programme for twelve independent strategies ([ADR-018](docs/adr/ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md)). The order, per-strategy status and blockers are in the [strategy roadmap and master tracker](docs/development/strategy-development-roadmap.md). Next: Strategy 01, Liquidity Sweep / Reversal. This does not change the milestone statuses above.

## Open roadmap questions

- OQ-RD-01 — target dates per milestone.
- OQ-RD-02 — defer M8 (LLM) until after M9 to reach G1 sooner?
