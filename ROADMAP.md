# ROADMAP — Milestone Progress

High-level progress tracker. The **detailed plan** (scope, files, tests, exit criteria, dependency graph, risks) is in **[docs/engineering/01_IMPLEMENTATION_ROADMAP.md](docs/engineering/01_IMPLEMENTATION_ROADMAP.md)** (ENG-01). This file must not duplicate that plan. Update the status and date columns when a milestone's acceptance criteria are **verified**.

Status: `NOT STARTED` · `IN PROGRESS` · `COMPLETED` · `BLOCKED` · `NEEDS REVIEW`. Target dates are not set yet (OQ-RD-01).

Direction changed on 2026-11-17 to a **personal intraday workstation** ([ADR-014](docs/adr/ADR-014-PERSONAL-INTRADAY-WORKSTATION.md)). M0 and M1 stand. The daily milestones M2–M10 are superseded by the intraday milestones I0–I8 (detail in [ENG-01 §0](docs/engineering/01_IMPLEMENTATION_ROADMAP.md#0-intraday-roadmap-adr-014)). Effort ranges are solo engineering days, not dates.

| M | Milestone | Objective | Depends on | Status | Completed |
|---|---|---|---|---|---|
| M0 | Repository and infrastructure foundation | Monorepo, Compose stack skeleton, GitHub repo config and CI gates | — | `COMPLETED` | 2026-11-15 |
| M1 | Database and API contracts | ARC-03 schema, seeders, OpenAPI and engine JSON Schemas | M0 | `COMPLETED` | 2026-11-17 (PRs #13–#15, #17, #19–#21) |
| M2–M10 | Daily-timeframe roadmap | — | — | Superseded by ADR-014 (not started) | — |
| I0 | Direction and specifications | ADR-014/015, intraday TRD-01..07, product docs | M1 | `IN PROGRESS` | — |
| I1 | Intraday schema and contracts | Bar timestamps, 1m/5m/15m/1D, snapshot by reference, risk state, calendar seed | I0 | `NOT STARTED` | — |
| I2 | Intraday market data | Provider adapter (Kite or Groww), bar-close fetcher, current-price cache, quality checks, DEMO intraday data | I1, provider access | `NOT STARTED` (blocked: OQ-INT-01/04) | — |
| I3 | Engine core on 15m/5m | Pivots, structure, BOS/CHoCH, higher-timeframe alignment | I1 | `NOT STARTED` | — |
| I4 | Session context and setups | Opening range, previous-day levels, S/R zones, breakout-retest, levels, NO_TRADE | I3 | `NOT STARTED` | — |
| I5 | Intraday risk and trade state | Sizing with ₹ caps, daily loss and streak limits, open risk, intraday costs, end-of-day exit | I1 | `NOT STARTED` | — |
| I6 | API and frontend integration | `/api/v1` subset, HTTP adapter, intraday chart, polling | I2–I5 | `NOT STARTED` | — |
| I7 | Journal and performance | Planned vs actual, net P&L, server-side stats | I6 | `NOT STARTED` | — |
| I8 | Intraday backtesting | 5m bar replay, sessions, collisions, end-of-day exit, costs, out-of-sample | I3–I5, history | `NOT STARTED` | — |

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

## Open roadmap questions

- OQ-RD-01 — target dates per milestone.
- OQ-RD-02 — defer M8 (LLM) until after M9 to reach G1 sooner?
