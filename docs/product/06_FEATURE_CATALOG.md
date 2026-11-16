# Feature Catalog

| Field | Value |
|---|---|
| Document ID | PRD-06 |
| Version | 0.1.0 |
| Status | Specification ready |
| Owner | Product Manager |
| Last updated | 2026-11-15 |
| Related | [PRD-03 PRD](03_PRD.md) · [ENG-01 Roadmap](../engineering/01_IMPLEMENTATION_ROADMAP.md) · [ENG-02 Frontend mapping](../engineering/02_FRONTEND_ARCHITECTURE.md#8-route--feature--api--entity-mapping) |

## 1. Status vocabulary

| Status | Meaning |
|---|---|
| **Frontend implemented** | Works in the UI without any backend (e.g. theme toggle, client-side filtering). |
| **Mock functionality only** | UI exists and behaves plausibly, but data is sample data and actions are not persisted or computed authoritatively. |
| **Specification ready** | Fully specified in these docs; no UI and no backend yet. |
| **Backend pending** | Used in combination: the UI is ready but the backend/engine part is not built. |
| **Future scope** | Not in MVP. |

A feature can carry two statuses (e.g. "Mock functionality only · Backend pending").

## 2. Catalog

| ID | Feature & description | User value | Depends on | Functional behaviour → acceptance | Status | Milestone |
|---|---|---|---|---|---|---|
| F-01 | **Registration & login** — email/password accounts with personal tenant | Secure personal workspace | — | FR-001–006; US-01 entry; generic login errors; sessions per ARC-06 | Mock functionality only · Backend pending | M6/M7 |
| F-02 | **Password reset & email verification** | Account recovery | F-01, email provider | FR-003–004; reset token single-use 60 min | Mock functionality only (request form) · Backend pending | M6 |
| F-03 | **Route protection** | Privacy | F-01 | FR-006; unauthenticated → `/login` | Specification ready | M7 |
| F-04 | **Progressive onboarding** — 7 steps, resumable | Fast start, tailored defaults | F-01 | PRD-05; completion criteria §6 | Mock functionality only · Backend pending | M6/M7 |
| F-05 | **Demo mode** — sample data source | Explore without a broker | — | US-01; badge everywhere; never "live" | Mock functionality only (frontend mocks) · Backend pending (seeded DEMO source) | M1/M7 |
| F-06 | **Zerodha connection** — Kite login, token custody | Personal real data | F-01, ARC-08 | US-02, FR-020–022, FR-025 | Mock functionality only (placeholder buttons) · Backend pending | M2/M6 |
| F-07 | **Data source selection** | Control over data mode | F-05, F-06 | FR-023; `DATA_SOURCE_NOT_READY` until ingestion | Mock functionality only · Backend pending | M6 |
| F-08 | **Instrument master & universe** — NIFTY 500 point-in-time | Correct universe | F-06 or licensed source | ENG-05; ARC-03 §6 | Specification ready | M2 |
| F-09 | **Daily candle ingestion** with data-quality checks | Reliable data | F-08 | ENG-05 §5–8; ingestion runs visible | Specification ready | M2 |
| F-10 | **Market structure engine** — pivots, labels, state, BOS/CHoCH, wick breaches | Objective structure | F-09 | TRD-02; TV-PIV/TV-STR tests | Specification ready (frontend uses a different demo heuristic) | M3/M4 |
| F-11 | **Zones & liquidity** — S/R zones, strength, equal highs/lows | Key levels | F-10 | TRD-03; TV-ZON | Specification ready | M4 |
| F-12 | **Setup detection** — 4 setups, lifecycle, expiry | Actionable shortlist | F-10, F-11 | TRD-04 §3–7, §11; TV-SET | Specification ready | M5 |
| F-13 | **Quality score (PAQS)** | Prioritisation | F-12 | TRD-04 §10 | Mock functionality only (UI shows score/factors) · Backend pending | M5 |
| F-14 | **Signal states** — NO TRADE / BUY WATCH / ENTRY CONFIRMED / HOLD / EXIT with explanations | Clear meaning, no bare BUY/SELL | F-12, F-21 | TRD-04 §12; `lib/labels.ts` copy | Frontend implemented (labels/explanations) · Backend pending (computation) | M5 |
| F-15 | **Market scanner** | Daily shortlist | F-12 | FR-030–034; US-03 | Mock functionality only · Backend pending | M6/M7 |
| F-16 | **Dashboard** | Daily overview | F-15, F-20 | FR-035 | Mock functionality only · Backend pending | M7 |
| F-17 | **Stock analysis view** — annotated chart & panels | Understand a setup | F-10–F-13 | FR-040–049; US-04/05 | Mock functionality only · Backend pending | M7 |
| F-18 | **Global search** (⌘K) | Speed | F-08 | Instrument search API M1 | Frontend implemented (over mock list) · Backend pending | M7 |
| F-19 | **Watchlists** | Track candidates | F-01 | FR-055–058 | Mock functionality only (session store) · Backend pending | M6/M7 |
| F-20 | **Risk profile & position sizing** | Discipline | F-01 | TRD-05; US-06/07 | Mock functionality only (settings UI; client-side math) · Backend pending | M5/M6 |
| F-21 | **Trade plans** | Plan before trading | F-12, F-20 | FR-060–068; TRD-07 §3 | Mock functionality only · Backend pending | M6/M7 |
| F-22 | **Paper trading** | Practice without money | F-21, EOD pipeline | TRD-07 §4–6; US-08 | Specification ready | M9 |
| F-23 | **Actual trade log** (manual) | Track real executions separately | F-21 | FR-072; US-09 | Specification ready (UI shows mock executed orders) | M9 |
| F-24 | **Portfolio** (Paper / Actual books) | Exposure overview | F-22, F-23 | FR-073–076 | Mock functionality only · Backend pending | M9 |
| F-25 | **Trading journal** | Learn from trades | F-22, F-23 | FR-080–083; US-10 | Mock functionality only · Backend pending | M9 |
| F-26 | **Backtesting** | Validate rules | F-10–F-12, history | TRD-06; FR-090–094; US-11 | Mock functionality only (form; placeholder curve) · Backend pending | M9 |
| F-27 | **AI explanations & chart Q&A** | Plain-language understanding | F-17, LLM provider | ARC-07; FR-050–054; US-12 | Specification ready | M8 |
| F-28 | **In-app notifications** | Timely awareness | events from F-21/22/06/26 | FR-100–101 | Mock functionality only · Backend pending | M6/M9 |
| F-29 | **Settings** | Control | various | FR-007, FR-016, FR-069, FR-102 | Mock functionality only (session-only saves) · Backend pending | M6/M7 |
| F-30 | **Theme (dark/light/system)** | Comfort | — | FR-103; persisted locally; dark default (ADR-013) | Frontend implemented | — |
| F-31 | **Market session indicator** | Context | market calendar | FR-037 | Frontend implemented (clock-only, no holidays) · Backend pending (calendar API) | M2/M7 |
| F-32 | **Entitlements & quotas** | SaaS readiness, cost control | F-01 | ARC-03 §5.3 | Specification ready | M6 |
| F-33 | **Audit logging** | Accountability | F-01 | ARC-06 §10 | Specification ready | M1/M6 |
| F-34 | **Scanner CSV export** | Offline review | F-15, licensing | FR-034; licence-dependent | Mock functionality only (toast) · Backend pending | M7 |
| F-35 | **Weekly timeframe context** | Multi-timeframe view | F-10 | OQ-TRD-01 | Future scope (UI option disabled) | — |
| F-36 | **Broker order/holdings sync (read-only)** | Less manual entry | F-06 | FR-077 | Future scope | — |
| F-37 | **Automated order placement** | — | — | Excluded by ADR-010 | Future scope (explicitly not MVP) | — |
| F-38 | **Licensed SaaS data mode** | Commercial launch | Licence | ADR-011; BRD G3 | Future scope | M10+ |
| F-39 | **Additional brokers (e.g. Upstox)** | Choice | ADR-007 | Shown as "Planned" in settings | Future scope | — |
| F-40 | **Journal screenshots** | Richer journal | storage | FR-084 | Future scope (UI toast) | — |

## 3. Acceptance criteria references

Detailed acceptance criteria live with the authoritative requirement: user stories in [PRD-03 §7](03_PRD.md#7-user-stories-and-acceptance-criteria), trading behaviour in [TRD-08](../trading/08_TRADING_ENGINE_VALIDATION.md), API behaviour in [ARC-04](../architecture/04_API_SPECIFICATION.md). A feature is **done** when: its FR/US acceptance criteria pass, its tests are in CI, its API is in the OpenAPI contract, and this catalog's status is updated in the same PR.
