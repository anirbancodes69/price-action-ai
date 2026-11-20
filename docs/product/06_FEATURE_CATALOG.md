# Feature Catalog

| Field | Value |
|---|---|
| Document ID | PRD-06 |
| Version | 0.3.0 |
| Status | Revised for the personal intraday direction (ADR-014) |
| Owner | Product Manager |
| Last updated | 2026-11-21 |
| Related | [PRD-03 PRD](03_PRD.md) · [ENG-01 Roadmap](../engineering/01_IMPLEMENTATION_ROADMAP.md) · [ENG-02 Frontend mapping](../engineering/02_FRONTEND_ARCHITECTURE.md#8-route--feature--api--entity-mapping) |

## 1. Status vocabulary

| Status | Meaning |
|---|---|
| **Working** / **Working in HTTP mode** | Works end to end on real backend data; "in HTTP mode" means with `NEXT_PUBLIC_DATA_SOURCE=http` (sample data otherwise). |
| **Implemented** / **Engine implemented** | Built and tested in the backend or engine; not necessarily visible in the UI yet. Says nothing about whether the trading rules are profitable. |
| **Frontend implemented** | Works in the UI without any backend (e.g. theme toggle, client-side filtering). |
| **Mock functionality only** | UI exists and behaves plausibly, but data is sample data and actions are not persisted or computed authoritatively. |
| **Specification ready** | Fully specified in these docs; no UI and no backend yet. |
| **Backend pending** | Used in combination: the UI is ready but the backend/engine part is not built. |
| **Deferred** | Kept in the design (schema, contracts, UI) but not built for the MVP (ADR-014). |
| **Future scope** | Not in MVP. |

A feature can carry two statuses (e.g. "Mock functionality only · Backend pending").

## 2. Catalog

Revised for the personal intraday direction ([ADR-014](../adr/ADR-014-PERSONAL-INTRADAY-WORKSTATION.md)). IDs from version 0.1.0 are kept; milestones refer to the intraday roadmap I0–I8 ([ENG-01 §0](../engineering/01_IMPLEMENTATION_ROADMAP.md#0-intraday-roadmap-adr-014)). **Deferred** means kept in the design but not built for the MVP. Statuses verified against the code on 2026-11-21. The frontend's sample data follows the intraday model (T-I10); "Mock functionality only" means the screen exists but does not read the API yet.

| ID | Feature & description | User value | Depends on | Functional behaviour → acceptance | Status | Milestone |
|---|---|---|---|---|---|---|
| F-01 | **Login** — owner account (`php artisan owner:create`), email/password session | Secure personal workspace | — | FR-002, FR-005, FR-006 | **Working in HTTP mode** (Sanctum SPA cookie, CSRF, rate limit); mock login otherwise | I6 |
| F-02 | **Password reset** | Account recovery | F-01 | FR-003 | Mock functionality only (request form) · Backend pending | I6 |
| F-03 | **Route protection** | Privacy | F-01 | FR-006 | **Working in HTTP mode** (session check in the browser, redirect to sign in) | I6 |
| F-04 | **Progressive onboarding** | — | F-01 | PRD-05 | **Deferred** (UI exists, not linked) | — |
| F-05 | **Demo mode** — DEMO intraday data source | Use the app without a broker | — | US-01; badge everywhere | **Working** (DEMO 5m/15m bars seeded, `DemoProvider` in the engine; sample badge in the UI) | I2 |
| F-06 | **Broker data connection** — Kite or Groww (T-201/T-203), token custody | Personal real data | F-01, ARC-08 | US-02, FR-020–022, FR-025 | Backend partly built (`KiteProvider`, token file read just in time, `php artisan source:create-kite`; real history backfilled). In-app connect flow and broker settings UI pending | I2/I6 |
| F-07 | **Data source switch** (DEMO/PERSONAL) | Control over data mode | F-05, F-06 | FR-023 | Mock functionality only · Backend pending | I6 |
| F-08 | **Instrument master & NIFTY 50 universe** | Correct universe | F-06 | ENG-05; ARC-03 §6 | **Implemented** (instrument sync; NIFTY 50 universe loaded from an owner-supplied symbol list, no verified constituent source, OQ-BT-01) | I2 |
| F-09 | **Intraday bar ingestion** — 5m/15m at bar close, daily context, reconciliation, quality checks | Reliable, fresh data | F-08 | ENG-05 §12; SM-01/02 | **Implemented**, not yet run live: bar-close `ingest_tick` cron (off unless `INGEST_ENABLED=true`), backfill (5m/15m from 2026-01-01, 1D from 2026-01-01; no daily 1D job), quality checks, reconciliation. NSE holidays not loaded | I2 |
| F-10 | **Market structure engine** — pivots, labels, state, BOS/CHoCH per timeframe, 15m→5m alignment | Objective, repaint-free structure | F-09 | TRD-02; TV-PIV/STR/HTF/SES | **Engine implemented** (pivots, labels, structure machine, BOS/CHoCH, wick breaches, 15m→5m alignment). TRD-08 coverage incomplete, no property-based tests (T-I139) | I3 |
| F-11 | **Zones & session levels** — S/R zones, PDH/PDL/PDC, opening range, equal highs/lows | Key levels | F-10 | TRD-03; TV-ZON/REF | **Engine implemented** (zones with strength and break/flip, equal-level pools, PDH/PDL/PDC, opening range, session high/low). PDH/PDL/PDC come from 5m bars ending 15:15 (T-I138) | I4 |
| F-12 | **Intraday setups** — opening range breakout, previous-day high/low break, breakout-retest; lifecycle bounded by the session | Actionable shortlist | F-10, F-11 | TRD-04 §3–7, §11; TV-SET | **Engine implemented** for the three long setups; short ORB and PDL informational; BREAKOUT_RETEST short mirror missing. First real backtest lost money ([log](../trading/backtests/2026-11-20-pa-intraday-0.1.0-nifty50.md)) | I4 |
| F-13 | **Quality score (PAQS intraday)** | Prioritisation | F-12 | TRD-04 §10 | **Engine implemented**; components shown on the analysis page in HTTP mode. Did not rank outcomes in the first backtest | I4 |
| F-14 | **Signal states with time** — NO TRADE / BUY WATCH / ENTRY CONFIRMED / HOLD / EXIT, `signal_at`, `valid_until` | Clear meaning and freshness | F-12, F-21 | TRD-04 §12; `lib/labels.ts` | **Working in HTTP mode** (NO TRADE / BUY WATCH / ENTRY CONFIRMED with `signal_at` and `valid_until` from the engine; HOLD / EXIT from the position monitor). The scanner can show an actionable signal whose plan the risk check rejects (T-I135) | I4/I6 |
| F-15 | **Intraday scanner** | Live shortlist | F-12 | FR-030–033; US-03 | **Working in HTTP mode** (live engine proxy, 30 s polling; DEMO data labelled as sample). Mock rows otherwise. Not yet run against real Kite bars | I6 |
| F-16 | **Intraday dashboard** — session clock, P&L, limits, positions | Session overview | F-15, F-41 | FR-035, FR-110 | **Working in HTTP mode** (live scan, today's risk, open positions, 30 s polling); index series, triggers and activity not available | I6 |
| F-17 | **Stock analysis view** — 5m/15m annotated chart & panels | Understand a setup | F-10–F-13 | FR-040–049; US-04/05 | **Working in HTTP mode** (5m/15m/1D bars, setup, levels, PAQS evidence, reason codes, 30 s polling); event markers not supplied; not checked in a browser | I6 |
| F-18 | **Global search** (⌘K) | Speed | F-08 | M1 search API | Frontend implemented (mock list) · Backend pending | I6 |
| F-19 | **Watchlist** (default NIFTY 50) | Track candidates | F-01 | FR-055–058 | **Working in HTTP mode** (watchlists API W1-W6, server-backed store) | I6 |
| F-20 | **Risk profile & position sizing** — ₹ cap, 0.5% risk | Discipline | F-01 | TRD-05 §3; US-06/07 | **Working in HTTP mode** (risk profile API, engine sizing via `risk/calculate`); no cost estimate in plans | I5 |
| F-21 | **Trade plans** — engine levels, limit checks, cutoff | Plan before trading | F-12, F-20, F-41 | FR-060–068; TRD-07 §3 | **Working in HTTP mode** (plans from the live setup or manual, engine-sized, cancel, expire at the entry cutoff); no stored analysis runs (ADR-017), bar-close status changes not built | I5/I6 |
| F-22 | **Paper trading** at bar close with session-end exit | Practice and forward validation | F-21, F-09 | TRD-07 §4–6; US-08 | Specification ready | I6 |
| F-23 | **Actual trade log** (manual, timed fills) | Track real executions separately | F-21 | FR-072; US-09 | **Working in HTTP mode** (log a buy, record sells with charges, optional stop and target, link to a plan) | I6 |
| F-24 | **Active trades** (Paper / Actual books, live P&L) | Monitor open positions | F-22, F-23, F-42 | FR-073–076, FR-113 | **Working in HTTP mode** for the Actual book (live P&L at the latest stored 5m close, HOLD/EXIT signal, today's risk); Paper book empty | I6 |
| F-25 | **Trading journal** — planned vs actual, net P&L | Measure and learn | F-22, F-23 | FR-080–085; US-10 | **Working in HTTP mode** for closed actual trades (notes; setup type and R-multiple when the trade followed a plan); no server-side statistics, no paper entries | I7 |
| F-26 | **Intraday backtesting** | Validate rules | F-10–F-12, history | TRD-06; FR-090–094; US-11 | Engine library and CLI (`scripts/run_backtest.py`; first real run 2026-11-20). UI is mock only; no persistence or API | I8 |
| F-27 | **AI explanations & chart Q&A** | Plain-language understanding | F-17, LLM | ARC-07 | **Deferred** | — |
| F-28 | **In-app notifications** — triggers, limits, cutoff, session end, data delayed | Timely awareness | F-21/22/41 | FR-100–101 | Mock functionality only · Backend pending | I6 |
| F-29 | **Settings** — profile, risk and limits, session (read-only), data and broker | Control | various | FR-007, FR-069, FR-114 | Risk and limits section **working in HTTP mode**; other sections mock only | I6 |
| F-30 | **Theme (dark/light/system)** | Comfort | — | FR-103; dark default (ADR-013) | Frontend implemented | — |
| F-31 | **Market session indicator** from the NSE calendar | Context | calendar seed | FR-037 | Frontend implemented (session phases and countdowns, no holidays) · Backend pending | I1/I6 |
| F-32 | **Entitlements & quotas** | SaaS readiness | F-01 | ARC-03 §5.3 | **Deferred** (schema exists) | — |
| F-33 | **Audit logging** | Accountability | F-01 | ARC-06 §10 | Specification ready (table in place, M1) | I6 |
| F-34 | **Scanner CSV export** | Offline review | F-15 | FR-034 | **Deferred** | — |
| F-35 | **Daily structure filter for intraday longs** | Higher-timeframe context | F-10 | OQ-TRD-01 | Future scope | — |
| F-36 | **Broker order/holdings sync (read-only)** | Less manual entry | F-06 | FR-077 | Future scope | — |
| F-37 | **Automated order placement** | — | — | Excluded by ADR-010 | Future scope (explicitly not MVP) | — |
| F-38 | **Licensed SaaS data mode** | Commercial use | Licence | ADR-011; BRD G3 | Future scope | — |
| F-39 | **Additional brokers** | Choice | ADR-007 | Kite and Groww evaluated first | Future scope | — |
| F-40 | **Journal screenshots** | Richer journal | storage | FR-084 | Specification ready | I7 |
| F-41 | **Account limits** — daily loss, losing streak, open positions, open risk; "today" panel | Hard risk discipline | F-20, trades | TRD-05 §8; FR-110–112; US-14 | Mock functionality only (today's risk panel) · Backend pending | I5/I6 |
| F-42 | **Current-price cache** for open positions and the watchlist | Live P&L without touching analysis | F-06 | ENG-05 §12; FR-115 | Specification ready | I2 |
| F-43 | **Session handling** — opening range, entry cutoff, session-end exit, special sessions | Intraday-correct behaviour | calendar | TRD-01 §4.1; FR-112–114; US-15 | **Engine implemented** (opening range, entry cutoff, session-end exit in backtest and position monitor; plans expire at the cutoff). Special sessions only via calendar rows; holidays not loaded (T-I137) | I1/I4 |
| F-44 | **Trend continuation & sweep reversal setups** | More opportunities | F-12 validated | TRD-04 §6–7 | Future scope (specified, disabled in `pa-intraday 0.1.0`) | — |
| F-45 | **Intraday short setups (actionable)** | Trade breakdowns | ADR superseding C-12 | OQ-TRD-06 | Future scope | — |
| F-46 | **1-minute execution refinement** | Finer entries and collision resolution | 1m data | OQ-SD-02, OQ-BT-07 | Future scope | — |

## 3. Acceptance criteria references

Detailed acceptance criteria live with the authoritative requirement: user stories in [PRD-03 §7](03_PRD.md#7-user-stories-and-acceptance-criteria), trading behaviour in [TRD-08](../trading/08_TRADING_ENGINE_VALIDATION.md), API behaviour in [ARC-04](../architecture/04_API_SPECIFICATION.md). A feature is **done** when: its FR/US acceptance criteria pass, its tests are in CI, its API is in the OpenAPI contract, and this catalog's status is updated in the same PR.
