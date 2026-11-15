# Business Requirements Document (BRD)

| Field | Value |
|---|---|
| Document ID | PRD-02 |
| Version | 0.1.0 |
| Status | Draft for owner sign-off |
| Owner | Product Owner |
| Last updated | 2026-11-15 |
| Related | [PRD-01 Vision](01_PRODUCT_VISION.md) · [PRD-03 PRD](03_PRD.md) · [ENG-01 Roadmap](../engineering/01_IMPLEMENTATION_ROADMAP.md) · [OPS-05 Compliance](../operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md) |

## 1. Purpose

States the business objectives, requirements, scope, constraints and acceptance gates for PriceAction AI's MVP and its path to SaaS. Functional detail lives in the PRD; this document defines *what the business needs* and *how success is judged*.

## 2. Business objectives

| ID | Objective |
|---|---|
| BO-01 | Deliver a working personal decision-support tool for NSE swing trading within the roadmap milestones M0–M9. |
| BO-02 | Establish a rule-based, versioned analysis engine whose behaviour can be validated by backtests. |
| BO-03 | Build the product on an architecture that can become multi-tenant SaaS without a rewrite. |
| BO-04 | Avoid regulatory and data-licensing exposure during the personal phase. |
| BO-05 | Keep operating cost low (single host, minimal paid services) during the personal phase. |

## 3. Stakeholders

| Stakeholder | Interest | Role |
|---|---|---|
| Product owner / founder (also the first user and solo developer) | Usable tool, future business | Decision maker, implementer |
| Future beta users | Clarity, reliability | Feedback (Phase B) |
| Zerodha (Kite Connect) | API terms compliance | External provider |
| Licensed data vendor (future) | Licence compliance | External provider |
| LLM provider | API terms, data handling | External provider |
| Legal / compliance advisor (future) | Regulatory classification | Reviewer before SaaS |

## 4. Business requirements

Identifiers use the prefix `BRQ-` (business requirement). `BR-` is reserved for business rules in the [PRD](03_PRD.md).

| ID | Requirement | Priority |
|---|---|---|
| BRQ-001 | The product shall analyse NIFTY 500 NSE cash equities on the daily timeframe using only price-action rules. | Must |
| BRQ-002 | The product shall never place, modify or cancel broker orders in the MVP. | Must |
| BRQ-003 | The product shall allow full exploration in a clearly labelled demo mode without connecting a broker. | Must |
| BRQ-004 | The product shall connect to Zerodha Kite Connect for personal market data without collecting the user's Zerodha password. | Must |
| BRQ-005 | Every analysis shall be reproducible from an immutable candle snapshot and a versioned ruleset. | Must |
| BRQ-006 | All trading calculations (levels, quantity, R:R) shall be deterministic and independent of any LLM. | Must |
| BRQ-007 | The product shall size positions from the user's risk profile and refuse plans without a stop-loss or below the minimum R:R. | Must |
| BRQ-008 | The product shall keep proposed plans, paper trades and actual executed trades as separate records. | Must |
| BRQ-009 | The product shall provide backtesting free of look-ahead bias and flag survivorship-bias risk. | Must |
| BRQ-010 | The product shall treat bearish setups as informational only. | Must |
| BRQ-011 | The product shall provide AI explanations that only explain computed results. | Should |
| BRQ-012 | The product shall support a trading journal linked to trades. | Should |
| BRQ-013 | The architecture shall isolate tenants and data sources so personal data cannot be redistributed. | Must |
| BRQ-014 | The product shall present "No trade" as a first-class outcome. | Must |
| BRQ-015 | The product shall display disclaimers that it is not investment advice. | Must |
| BRQ-016 | All source changes shall pass automated CI on GitHub Actions before merging to `main`. | Must |
| BRQ-017 | Production deployments shall require manual approval. | Must |

## 5. Scope

| In scope (MVP) | Notes |
|---|---|
| Web application (desktop-first, responsive) | Existing frontend |
| NSE cash equity, NIFTY 500, daily | |
| Demo, personal (Zerodha) data modes | Licensed mode designed only |
| Analysis, scanner, watchlists, plans, paper trading, actual-trade log, journal, backtesting, AI explanations, notifications (in-app) | |
| Single-owner tenants | Multi-user tenants designed only |

## 6. Out of scope

Order placement/automation; intraday; F&O, currency, commodity; BSE (type exists in frontend but not supported); short-selling execution; mobile apps; billing and paid plans; licensed SaaS data; social/community; broker portfolio sync; custom user-defined strategies; push/email notifications beyond essentials (later milestones).

## 7. Assumptions

| ID | Assumption | Validate by |
|---|---|---|
| AS-01 | Kite Connect provides daily historical candles for NSE equities and indices for an authorised user. | M2 spike |
| AS-02 | Personal API use for the account holder's own analysis is permitted by Kite terms; multi-user or commercial use is **not** assumed to be. | Terms review (OQ-SEC-01) |
| AS-03 | End-of-day processing after 18:30 IST captures final daily candles. | M2 observation |
| AS-04 | Initial rule parameters are reasonable starting points but unvalidated. | M9/M10 backtests |
| AS-05 | A single Docker host is sufficient through Phase B. | Load test M10 |
| AS-06 | The owner is the only production user until Phase B. | — |

## 8. Dependencies

| Dependency | Needed for | Status |
|---|---|---|
| Kite Connect developer app + subscription | Personal data | Owner to procure (OQ-INT-01) |
| Point-in-time NIFTY 500 constituents | Survivorship-free backtests | Unresolved (OQ-BT-01) |
| NSE holiday calendar | Ingestion completeness | Manual yearly seed |
| LLM provider account | Explanations | Unresolved (OQ-AI-01) |
| Hosting (VPS/cloud) + domain | Staging/production | M10 |
| GitHub repository + Actions | CI/CD | Repo initialised locally, no commits yet |

## 9. Risks

See [PRD-01 §10](01_PRODUCT_VISION.md#10-business-risks) for business risks; technical risks in [ENG-01 §5](../engineering/01_IMPLEMENTATION_ROADMAP.md). Additional delivery risks:

| ID | Risk | Mitigation |
|---|---|---|
| RK-01 | Scope creep into execution features | ADR-010; BRQ-002 is a hard gate |
| RK-02 | Spec drift between docs and code | Docs-as-code; PR template requires doc updates |
| RK-03 | Look-ahead bugs inflate backtests | TRD-08 TV-NLA tests as required CI checks |

## 10. Success metrics

| ID | Metric | Target (MVP) |
|---|---|---|
| SM-01 | EOD pipeline success rate (ingest + analyse) | ≥ 95% of trading days complete by 20:00 IST |
| SM-02 | Scanner availability after pipeline | Latest batch visible within 5 min of completion |
| SM-03 | Analysis page p95 latency (cached run) | < 800 ms API, < 2.5 s LCP |
| SM-04 | Determinism | 100% hash match in nightly re-run sample |
| SM-05 | Trading test catalogue coverage | 100% of TV-* tests implemented and passing |
| SM-06 | Plans with engine-computed risk | 100% |
| SM-07 | AI explanation validation pass rate | ≥ 90% (rest fall back safely) |
| SM-08 | Owner usage | Daily review done in-app on ≥ 80% of trading days over 4 weeks (self-reported) |

No financial performance (returns) target is set; the product does not promise returns.

## 11. Business acceptance criteria

| ID | Criterion |
|---|---|
| BAC-01 | A new user can register, complete onboarding in demo mode and view a demo analysis with the sample-data badge visible. |
| BAC-02 | The owner can connect Zerodha via Kite login, see personal data ingested and analysed by next EOD run, and see the data mode as PERSONAL. |
| BAC-03 | From a BUY WATCH setup, the owner can create a plan whose quantity matches TRD-05 for their risk profile; invalid plans are refused with clear reasons. |
| BAC-04 | A paper trade fills/exits per TRD-07 and creates a journal draft. |
| BAC-05 | A backtest over ≥ 3 years runs and reports TRD-06 metrics with versions and bias flags. |
| BAC-06 | No screen offers order placement. |
| BAC-07 | No broker token or secret is observable in browser devtools, logs or API responses. |

## 12. Release gates

| Gate | Applies to | Conditions |
|---|---|---|
| G1 — Personal MVP | Owner production use | M0–M9 exit criteria met; BAC-01..07 pass; required CI checks green; backups configured and one restore tested |
| G2 — Private beta | Other users | G1 + provider terms review for multi-user use (OQ-SEC-01) + privacy policy + terms of use + account deletion working + 2FA available |
| G3 — SaaS commercial | Paying users | G2 + **signed market-data redistribution licence** + **legal/regulatory review** of product classification (incl. SEBI research analyst / investment adviser considerations) + RLS enabled + DR drill passed + billing + security review/pen-test |

G3 conditions are non-negotiable (constraints C-04, C-05).
