# ADR-014: Personal Intraday Price-Action Workstation

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-17 |
| Deciders | Product owner |
| Version | 1.0 |
| Related | [ADR-015](ADR-015-INTRADAY-TIME-AND-SNAPSHOT-MODEL.md) · [ADR-007](ADR-007-MARKET-DATA-PROVIDER-ABSTRACTION.md) · [ADR-008](ADR-008-DETERMINISTIC-TRADING-ENGINE.md) · [ADR-010](ADR-010-MANUAL-TRADE-EXECUTION-MVP.md) · [ADR-011](ADR-011-DATA-MODES-AND-TENANT-ISOLATION.md) · [TRD-01](../trading/01_TRADING_METHODOLOGY.md) · [ROADMAP](../../ROADMAP.md) |

## Context

The specification set (2026-11-15) describes a daily-timeframe swing and positional product for the NIFTY 500, designed to become a SaaS later. On 2026-11-17 the owner changed the direction: PriceAction AI is primarily a **personal intraday trading and price-action analysis workstation** for its owner.

An assessment of the repository at the end of M1 (commit `a680643`) found that the infrastructure, schema, contracts, CI and design system are reusable, and that no trading logic, ingestion, API or backtester had been built yet. The cost of changing direction is therefore mostly in the specifications, the time model and the mock UI, not in working code.

No earlier ADR records the daily scope. It lives in TRD-01 (MP-02 "Daily timeframe is primary", scope line, §8 "does not trade intraday"), the product documents (PRD, BRD, vision), CLAUDE.md §1 and the roadmap. This ADR supersedes those statements.

Owner decisions taken with this ADR (2026-11-17):

- Bearish setups stay **informational** in the first intraday version; constraint C-12 is kept.
- The daily methodology becomes **context only**; daily setups leave the MVP.
- The MVP universe is **NIFTY 50**.

## Decision

1. **Primary use.** A single-user, personal decision-support workstation for **intraday** price-action trading of NSE cash equities. It helps the owner find opportunities, read structure, plan entry, stop, target and size, check risk before a trade, record and monitor manually executed trades, and keep a journal with measured performance.
2. **Timeframes.** 15-minute bars give structure and direction; 5-minute bars give setups and confirmation. 1-minute execution refinement is deferred. Daily bars are kept **only as context** (previous-day high, low and close; daily structure as a filter). The daily setups of TRD-04 are retired from the MVP.
3. **Closed bars only.** A signal is evaluated at the close of a completed bar and can act no earlier than the next bar. Higher-timeframe context at time `t` uses only higher-timeframe bars that closed at or before `t`. This is the intraday form of C-09 and ADR-008.
4. **Universe.** NIFTY 50 for the MVP (about 50 liquid symbols). Wider universes are a later decision.
5. **Long-only actionability (unchanged).** Bearish setups are detected and shown, but plans, sizing and paper trades are long-only (C-12). Intraday short selling needs a later ADR.
6. **Manual execution (unchanged).** No broker order placement (ADR-010, C-02).
7. **Intraday risk model.** Account-level limits are mandatory and enforced before a plan is accepted: daily loss limit, consecutive-loss limit, maximum open positions and maximum open risk, in addition to per-trade sizing from the stop distance. Every position is closed by the end of the session. Costs use an **intraday** cost schedule. The owner's planning values are recorded as **HYPOTHESIS**, not validated parameters: trading capital ₹1,00,000; maximum capital per position ₹50,000; risk per trade 0.5% of capital (₹500); daily loss limit and consecutive-loss limit configurable.
8. **Ruleset.** A new ruleset `pa-intraday` (first version `0.1.0`, all values HYPOTHESIS) replaces `pa-core` for analysis. `pa-core 0.1.0` stays in the database as a retired version (its row is immutable once active) and is not used by the MVP.
9. **Personal-first scope.** Deferred, not removed: the onboarding flow, subscription entitlements and plans, data-source selection UI, the LICENSED data mode, AI explanations (former M8) and CSV export. Kept: authentication, the tenant model (one seeded tenant and owner), role grants, the single-writer rule, audit logging and data-mode separation (ADR-011). No security or integrity protection is removed.
10. **Roadmap.** Milestones M2–M10 are replaced by intraday milestones **I0–I8** ([ROADMAP](../../ROADMAP.md), [ENG-01 §0](../engineering/01_IMPLEMENTATION_ROADMAP.md#0-intraday-roadmap-adr-014)). M0 and M1 stand as completed.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Keep the daily swing product | Does not serve the owner's actual use. |
| Build daily and intraday side by side | Roughly doubles the spec, engine and test surface before either is validated. |
| Start with 1-minute bars | More data, more noise and more provider load; 15m + 5m is enough to test the setups first. |
| Use a third-party charting or screener tool instead | Gives charts but not deterministic, versioned, testable rules, risk enforcement and a journal tied to plans. |
| Rebuild the stack for streaming (Kafka, separate services) | Not needed for one user and about 50 symbols; ADR-004 stands. |

## Consequences

+ The direction changes before any engine, ingestion or API code exists, which is the cheapest moment.
+ Architecture, CI, contracts tooling, schema principles and the design system carry over unchanged.
− Large specification rewrite: TRD-01..07, parts of ARC-03, ARC-04, ENG-05 and the product documents. The documents not yet revised are listed in [DOCUMENTATION_STATUS](../DOCUMENTATION_STATUS.md) as needing intraday revision.
− The schema time model changes (date columns become timestamps; ADR-015), as do the demo data, the contracts and every page's data.
− Intraday market data needs a broker data subscription and a live price path; availability and limits are unverified (OQ-INT-01, OQ-INT-04).
− Trading costs weigh more per trade intraday; strategy results are meaningless until costs are verified and setups are validated.

## Status

Accepted on 2026-11-17. Supersedes the daily-scope statements listed in Context. Does not supersede any earlier ADR; refines ADR-007 (providers must also serve intraday bars and current prices) and keeps ADR-008, ADR-010 and ADR-011 in force.
