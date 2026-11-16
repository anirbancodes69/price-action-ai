# Feature Catalog

| Field | Value |
|---|---|
| Document ID | PRD-06 |
| Version | 0.2.0 |
| Status | Revised for the personal intraday direction (ADR-014) |
| Owner | Product Manager |
| Last updated | 2026-11-17 |
| Related | [PRD-03 PRD](03_PRD.md) · [ENG-01 Roadmap](../engineering/01_IMPLEMENTATION_ROADMAP.md) · [ENG-02 Frontend mapping](../engineering/02_FRONTEND_ARCHITECTURE.md#8-route--feature--api--entity-mapping) |

## 1. Status vocabulary

| Status | Meaning |
|---|---|
| **Frontend implemented** | Works in the UI without any backend (e.g. theme toggle, client-side filtering). |
| **Mock functionality only** | UI exists and behaves plausibly, but data is sample data and actions are not persisted or computed authoritatively. |
| **Specification ready** | Fully specified in these docs; no UI and no backend yet. |
| **Backend pending** | Used in combination: the UI is ready but the backend/engine part is not built. |
| **Deferred** | Kept in the design (schema, contracts, UI) but not built for the MVP (ADR-014). |
| **Future scope** | Not in MVP. |

A feature can carry two statuses (e.g. "Mock functionality only · Backend pending").

## 2. Catalog

Revised for the personal intraday direction ([ADR-014](../adr/ADR-014-PERSONAL-INTRADAY-WORKSTATION.md)). IDs from version 0.1.0 are kept; milestones refer to the intraday roadmap I0–I8 ([ENG-01 §0](../engineering/01_IMPLEMENTATION_ROADMAP.md#0-intraday-roadmap-adr-014)). **Deferred** means kept in the design but not built for the MVP. Today's frontend shows **daily** mock data; "Mock functionality only" therefore means the layout exists but needs intraday data and fields.

| ID | Feature & description | User value | Depends on | Functional behaviour → acceptance | Status | Milestone |
|---|---|---|---|---|---|---|
| F-01 | **Login** — owner account (seeded), email/password session | Secure personal workspace | — | FR-002, FR-005, FR-006 | Mock functionality only · Backend pending | I6 |
| F-02 | **Password reset** | Account recovery | F-01 | FR-003 | Mock functionality only (request form) · Backend pending | I6 |
| F-03 | **Route protection** | Privacy | F-01 | FR-006 | Specification ready | I6 |
| F-04 | **Progressive onboarding** | — | F-01 | PRD-05 | **Deferred** (UI exists, not linked) | — |
| F-05 | **Demo mode** — DEMO intraday data source | Use the app without a broker | — | US-01; badge everywhere | Mock functionality only · Backend: daily DEMO seeded (M1), intraday DEMO pending | I2 |
| F-06 | **Broker data connection** — Kite or Groww (T-201/T-203), token custody | Personal real data | F-01, ARC-08 | US-02, FR-020–022, FR-025 | Mock functionality only (placeholders) · Backend pending | I2/I6 |
| F-07 | **Data source switch** (DEMO/PERSONAL) | Control over data mode | F-05, F-06 | FR-023 | Mock functionality only · Backend pending | I6 |
| F-08 | **Instrument master & NIFTY 50 universe** | Correct universe | F-06 | ENG-05; ARC-03 §6 | Specification ready (schema in place, M1) | I2 |
| F-09 | **Intraday bar ingestion** — 5m/15m at bar close, daily context, reconciliation, quality checks | Reliable, fresh data | F-08 | ENG-05 §12; SM-01/02 | Specification ready | I2 |
| F-10 | **Market structure engine** — pivots, labels, state, BOS/CHoCH per timeframe, 15m→5m alignment | Objective, repaint-free structure | F-09 | TRD-02; TV-PIV/STR/HTF/SES | Specification ready | I3 |
| F-11 | **Zones & session levels** — S/R zones, PDH/PDL/PDC, opening range, equal highs/lows | Key levels | F-10 | TRD-03; TV-ZON/REF | Specification ready | I4 |
| F-12 | **Intraday setups** — opening range breakout, previous-day high/low break, breakout-retest; lifecycle bounded by the session | Actionable shortlist | F-10, F-11 | TRD-04 §3–7, §11; TV-SET | Specification ready | I4 |
| F-13 | **Quality score (PAQS intraday)** | Prioritisation | F-12 | TRD-04 §10 | Mock functionality only (daily score UI) · Backend pending | I4 |
| F-14 | **Signal states with time** — NO TRADE / BUY WATCH / ENTRY CONFIRMED / HOLD / EXIT, `signal_at`, `valid_until` | Clear meaning and freshness | F-12, F-21 | TRD-04 §12; `lib/labels.ts` | Frontend implemented (labels) · Backend pending | I4/I6 |
| F-15 | **Intraday scanner** | Live shortlist | F-12 | FR-030–033; US-03 | Mock functionality only · Backend pending | I6 |
| F-16 | **Intraday dashboard** — session clock, P&L, limits, positions | Session overview | F-15, F-41 | FR-035, FR-110 | Mock functionality only · Backend pending | I6 |
| F-17 | **Stock analysis view** — 5m/15m annotated chart & panels | Understand a setup | F-10–F-13 | FR-040–049; US-04/05 | Mock functionality only · Backend pending | I6 |
| F-18 | **Global search** (⌘K) | Speed | F-08 | M1 search API | Frontend implemented (mock list) · Backend pending | I6 |
| F-19 | **Watchlist** (default NIFTY 50) | Track candidates | F-01 | FR-055–058 | Mock functionality only · Backend pending | I6 |
| F-20 | **Risk profile & position sizing** — ₹ cap, 0.5% risk | Discipline | F-01 | TRD-05 §3; US-06/07 | Mock functionality only (client-side math) · Backend pending | I5 |
| F-21 | **Trade plans** — engine levels, limit checks, cutoff | Plan before trading | F-12, F-20, F-41 | FR-060–068; TRD-07 §3 | Mock functionality only · Backend pending | I5/I6 |
| F-22 | **Paper trading** at bar close with session-end exit | Practice and forward validation | F-21, F-09 | TRD-07 §4–6; US-08 | Specification ready | I6 |
| F-23 | **Actual trade log** (manual, timed fills) | Track real executions separately | F-21 | FR-072; US-09 | Specification ready (UI shows mock orders) | I6 |
| F-24 | **Active trades** (Paper / Actual books, live P&L) | Monitor open positions | F-22, F-23, F-42 | FR-073–076, FR-113 | Mock functionality only (daily holdings) · Backend pending | I6 |
| F-25 | **Trading journal** — planned vs actual, net P&L | Measure and learn | F-22, F-23 | FR-080–085; US-10 | Mock functionality only · Backend pending | I7 |
| F-26 | **Intraday backtesting** | Validate rules | F-10–F-12, history | TRD-06; FR-090–094; US-11 | Mock functionality only (form; placeholder curve) · Backend pending | I8 |
| F-27 | **AI explanations & chart Q&A** | Plain-language understanding | F-17, LLM | ARC-07 | **Deferred** | — |
| F-28 | **In-app notifications** — triggers, limits, cutoff, session end, data delayed | Timely awareness | F-21/22/41 | FR-100–101 | Mock functionality only · Backend pending | I6 |
| F-29 | **Settings** — profile, risk and limits, session (read-only), data and broker | Control | various | FR-007, FR-069, FR-114 | Mock functionality only · Backend pending | I6 |
| F-30 | **Theme (dark/light/system)** | Comfort | — | FR-103; dark default (ADR-013) | Frontend implemented | — |
| F-31 | **Market session indicator** from the NSE calendar | Context | calendar seed | FR-037 | Frontend implemented (clock-only) · Backend pending | I1/I6 |
| F-32 | **Entitlements & quotas** | SaaS readiness | F-01 | ARC-03 §5.3 | **Deferred** (schema exists) | — |
| F-33 | **Audit logging** | Accountability | F-01 | ARC-06 §10 | Specification ready (table in place, M1) | I6 |
| F-34 | **Scanner CSV export** | Offline review | F-15 | FR-034 | **Deferred** | — |
| F-35 | **Daily structure filter for intraday longs** | Higher-timeframe context | F-10 | OQ-TRD-01 | Future scope | — |
| F-36 | **Broker order/holdings sync (read-only)** | Less manual entry | F-06 | FR-077 | Future scope | — |
| F-37 | **Automated order placement** | — | — | Excluded by ADR-010 | Future scope (explicitly not MVP) | — |
| F-38 | **Licensed SaaS data mode** | Commercial use | Licence | ADR-011; BRD G3 | Future scope | — |
| F-39 | **Additional brokers** | Choice | ADR-007 | Kite and Groww evaluated first | Future scope | — |
| F-40 | **Journal screenshots** | Richer journal | storage | FR-084 | Specification ready | I7 |
| F-41 | **Account limits** — daily loss, losing streak, open positions, open risk; "today" panel | Hard risk discipline | F-20, trades | TRD-05 §8; FR-110–112; US-14 | Specification ready | I5/I6 |
| F-42 | **Current-price cache** for open positions and the watchlist | Live P&L without touching analysis | F-06 | ENG-05 §12; FR-115 | Specification ready | I2 |
| F-43 | **Session handling** — opening range, entry cutoff, session-end exit, special sessions | Intraday-correct behaviour | calendar | TRD-01 §4.1; FR-112–114; US-15 | Specification ready | I1/I4 |
| F-44 | **Trend continuation & sweep reversal setups** | More opportunities | F-12 validated | TRD-04 §6–7 | Future scope (specified, disabled in `pa-intraday 0.1.0`) | — |
| F-45 | **Intraday short setups (actionable)** | Trade breakdowns | ADR superseding C-12 | OQ-TRD-06 | Future scope | — |
| F-46 | **1-minute execution refinement** | Finer entries and collision resolution | 1m data | OQ-SD-02, OQ-BT-07 | Future scope | — |

## 3. Acceptance criteria references

Detailed acceptance criteria live with the authoritative requirement: user stories in [PRD-03 §7](03_PRD.md#7-user-stories-and-acceptance-criteria), trading behaviour in [TRD-08](../trading/08_TRADING_ENGINE_VALIDATION.md), API behaviour in [ARC-04](../architecture/04_API_SPECIFICATION.md). A feature is **done** when: its FR/US acceptance criteria pass, its tests are in CI, its API is in the OpenAPI contract, and this catalog's status is updated in the same PR.
