# Business Requirements Document (BRD)

| Field | Value |
|---|---|
| Document ID | PRD-02 |
| Version | 0.2.0 |
| Status | Revised for the personal intraday direction (ADR-014); draft for owner sign-off |
| Owner | Product Owner |
| Last updated | 2026-11-17 |
| Related | [ADR-014](../adr/ADR-014-PERSONAL-INTRADAY-WORKSTATION.md) · [PRD-01 Vision](01_PRODUCT_VISION.md) · [PRD-03 PRD](03_PRD.md) · [ENG-01 Roadmap](../engineering/01_IMPLEMENTATION_ROADMAP.md#0-intraday-roadmap-adr-014) · [OPS-05 Compliance](../operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md) |

## 1. Purpose

States the business objectives, requirements, scope, constraints and acceptance gates for PriceAction AI as a **personal intraday price-action workstation** (ADR-014). Functional detail lives in the PRD; this document defines *what the owner needs* and *how success is judged*.

## 2. Business objectives

| ID | Objective |
|---|---|
| BO-01 | Deliver a working personal decision-support tool for intraday trading of NSE cash equities within roadmap milestones I0–I7, with intraday backtesting in I8. |
| BO-02 | Establish a rule-based, versioned analysis engine whose behaviour can be validated by backtests and a forward paper log before real money is risked. |
| BO-03 | Enforce risk discipline structurally: per-trade sizing and account-level daily limits that block, not warn. |
| BO-04 | Measure real performance after costs for paper and actual trades. |
| BO-05 | Keep operating cost low (one host, one broker data subscription, no other paid services). |
| BO-06 | Keep the architecture extensible (tenancy, data modes, contracts) without building SaaS features now. |

## 3. Stakeholders

| Stakeholder | Interest | Role |
|---|---|---|
| Owner (only user, solo developer) | Reliable intraday tool, honest results | Decision maker, implementer, user |
| Broker data provider (Zerodha Kite Connect and/or Groww; decision T-201/T-203) | API terms compliance | External provider |
| Future users (only if ever shared) | Clarity, reliability | Out of scope for the MVP |
| Legal / compliance advisor (future) | Regulatory classification | Reviewer before any sharing |

## 4. Business requirements

Identifiers use the prefix `BRQ-`. `BR-` is reserved for business rules in the [PRD](03_PRD.md).

| ID | Requirement | Priority |
|---|---|---|
| BRQ-001 | The product shall analyse NIFTY 50 NSE cash equities intraday on closed 5m bars with 15m context and daily context, using only price-action rules. | Must |
| BRQ-002 | The product shall never place, modify or cancel broker orders. | Must |
| BRQ-003 | The product shall be fully usable on clearly labelled DEMO intraday data without a broker connection. | Must |
| BRQ-004 | The product shall obtain personal market data from the owner's broker data subscription without collecting the broker password; tokens stay server-side. | Must |
| BRQ-005 | Every analysis shall be reproducible from its immutable inputs (bar ranges with content hashes) and a versioned ruleset. | Must |
| BRQ-006 | All trading calculations (levels, quantity, R:R, limits) shall be deterministic and independent of any LLM. | Must |
| BRQ-007 | The product shall size positions from the stop distance, the ₹ position cap and the risk profile, and refuse plans without a stop-loss or below the minimum R:R. | Must |
| BRQ-008 | The product shall keep proposed plans, paper trades and actual executed trades as separate records. | Must |
| BRQ-009 | The product shall provide intraday backtesting free of look-ahead bias, with session rules, costs and conservative collision handling. | Must |
| BRQ-010 | The product shall treat bearish setups as informational only. | Must |
| BRQ-011 | AI explanations are deferred; if added later they shall only explain computed results. | Could |
| BRQ-012 | The product shall provide a trading journal linked to trades, with planned vs actual and net P&L after costs. | Must |
| BRQ-013 | Data sources and tenants shall stay isolated so personal data cannot be redistributed (kept from the earlier design). | Must |
| BRQ-014 | The product shall present "No trade" as a first-class outcome. | Must |
| BRQ-015 | The product shall display disclaimers that it is decision support, not investment advice. | Must |
| BRQ-016 | All source changes shall pass automated CI on GitHub Actions before merging to `main`. | Must |
| BRQ-017 | Production deployments shall require manual approval. | Must |
| BRQ-018 | The product shall block new plans once the daily loss limit or the consecutive-loss limit is reached, and when open positions or open risk are at their limits. | Must |
| BRQ-019 | The product shall treat every position as intraday: no plan after the entry cutoff, a session-end exit for simulations, and warnings for open actual positions. | Must |
| BRQ-020 | Every screen with market data or signals shall show the data mode and the time of the last completed bar. | Must |

## 5. Scope

| In scope (MVP) | Notes |
|---|---|
| Web application (desktop-first, responsive) | Existing frontend, pages reworked for intraday |
| NSE cash equities, NIFTY 50, 5m + 15m + daily context | |
| DEMO and PERSONAL data modes | LICENSED mode stays designed only |
| Intraday scanner, analysis, watchlist, risk-checked plans, active-trade monitoring, paper trading, actual-trade log, journal, intraday backtesting, in-app notifications | |
| One owner, one tenant | Multi-user designed only |

## 6. Out of scope

Order placement/automation; overnight or positional holding; F&O, currency, commodity; BSE; short-selling execution; 1-minute signals; mobile apps; billing and paid plans; licensed SaaS data; onboarding flow; AI explanations; social/community; broker portfolio sync; custom user-defined strategies; email/push notifications.

## 7. Assumptions

| ID | Assumption | Validate by |
|---|---|---|
| AS-01 | The chosen broker API provides historical 5m/15m/daily bars and current prices for NSE equities to an authorised user, with enough history for backtests. | I2 spike (T-201/T-203, OQ-INT-01, OQ-BT-06) |
| AS-02 | Personal API use for the account holder's own analysis is permitted by the provider's terms. | Terms review (OQ-SEC-01) |
| AS-03 | Completed 5m bars are available from the provider within about 20 s of the bar end. | I2 observation |
| AS-04 | Initial rule parameters and risk defaults are reasonable starting points but unvalidated (TRD-01 §6, OQ-TRD-04). | I8 backtests and forward paper log |
| AS-05 | A single Docker host is sufficient for one user and about 50 symbols. | I6 observation |
| AS-06 | Intraday cost schedule in TRD-06 §5 is approximately right. | Verify before showing results (OQ-BT-02) |

## 8. Dependencies

| Dependency | Needed for | Status |
|---|---|---|
| Broker data subscription (Kite Connect and/or Groww) | Personal intraday data | Owner to procure after T-201/T-203 |
| NSE trading calendar | Session handling, completeness checks | Seed in I1 |
| NIFTY 50 constituent history | Survivorship-aware backtests | Unresolved (OQ-BT-01) |
| Hosting | Running the stack during market hours | Local machine first; host decision later |
| GitHub repository + Actions | CI/CD | In place |

## 9. Success metrics

| ID | Metric | Target (MVP) |
|---|---|---|
| SM-01 | Bar-close pipeline (fetch + analyse) | Analysis for the universe available within 60 s of the 5m close on ≥ 95% of bars per session |
| SM-02 | Data completeness | ≥ 99% of expected 5m bars per session after reconciliation |
| SM-03 | Analysis page p95 latency (cached run) | < 800 ms API, < 2.5 s LCP |
| SM-04 | Determinism | 100% hash match in a re-run sample |
| SM-05 | Trading test catalogue coverage | 100% of TV-* tests implemented and passing |
| SM-06 | Plans with engine-computed risk and limit checks | 100%; 0 accepted plans breaching an account limit |
| SM-07 | Journal completeness | Every closed paper/actual trade has a journal entry with net P&L |
| SM-08 | Owner usage | Sessions monitored in-app on ≥ 80% of trading days over 4 weeks (self-reported) |

No financial performance (returns) target is set; the product does not promise returns.

## 10. Business acceptance criteria

| ID | Criterion |
|---|---|
| BAC-01 | The owner can log in and use the scanner, analysis and planner on DEMO intraday data with the sample-data badge visible. |
| BAC-02 | With the broker connected, NIFTY 50 5m/15m bars arrive at each bar close, the analysis updates, and the data mode shows PERSONAL with the last bar time. |
| BAC-03 | From a BUY WATCH or ENTRY CONFIRMED setup, the owner can create a plan whose quantity matches TRD-05 for the risk profile; plans that breach a stop, R:R or account-limit rule are refused with clear reasons. |
| BAC-04 | A paper trade fills and exits per TRD-07 at bar closes (including the session-end exit) and creates a journal draft with net P&L. |
| BAC-05 | An intraday backtest over the available history runs and reports TRD-06 metrics with versions, cost schedule and bias flags. |
| BAC-06 | No screen offers order placement. |
| BAC-07 | No broker token or secret is observable in browser devtools, logs or API responses. |
| BAC-08 | After the daily loss limit is hit (paper or actual book), new plans for that book are blocked for the rest of the session. |

## 11. Risks

See [PRD-01 §10](01_PRODUCT_VISION.md#10-risks); technical risks in [ENG-01 §0](../engineering/01_IMPLEMENTATION_ROADMAP.md#0-intraday-roadmap-adr-014). Delivery risks:

| ID | Risk | Mitigation |
|---|---|---|
| RK-01 | Scope creep into execution features | ADR-010; BRQ-002 is a hard gate |
| RK-02 | Spec drift between docs and code | Docs-as-code; PR template requires doc updates |
| RK-03 | Look-ahead or repainting bugs inflate backtests | TRD-08 TV-NLA and TV-HTF tests as required CI checks |
| RK-04 | Real money used before validation | Forward paper log and I8 backtests before any real trade based on the tool (owner discipline; G1) |

## 12. Release gates

| Gate | Applies to | Conditions |
|---|---|---|
| G1 — Personal intraday MVP | Owner use with real money | I0–I7 exit criteria met; BAC-01..08 pass; required CI checks green; intraday cost schedule verified; at least 20 sessions of forward paper log reviewed; backups configured |
| G2 — Sharing with others | Any other user | G1 + provider terms review for multi-user use (OQ-SEC-01) + privacy policy + terms of use + account deletion + 2FA |
| G3 — Commercial SaaS | Paying users | G2 + **signed market-data redistribution licence** + **legal/regulatory review** of product classification (incl. SEBI research analyst / investment adviser considerations) + RLS + DR drill + billing + security review |

G3 conditions are non-negotiable (constraints C-04, C-05).
