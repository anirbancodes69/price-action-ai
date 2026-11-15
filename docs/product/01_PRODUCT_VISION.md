# Product Vision

| Field | Value |
|---|---|
| Document ID | PRD-01 |
| Version | 0.1.0 |
| Status | Approved for MVP planning (market sizing is an assumption) |
| Owner | Product Owner |
| Last updated | 2026-11-15 |
| Related | [PRD-02 BRD](02_BRD.md) · [PRD-03 PRD](03_PRD.md) · [TRD-01 Methodology](../trading/01_TRADING_METHODOLOGY.md) · [OPS-05 Compliance](../operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md) |

## 1. Problem statement

Indian retail swing and positional traders who use price action face four recurring problems:

1. **Manual chart review does not scale.** Reviewing 500 daily charts for structure, levels and setups takes hours; most traders review a small, biased subset.
2. **Inconsistent rules.** The same trader labels a "breakout" or "higher low" differently on different days. Without fixed definitions, results cannot be reviewed or improved.
3. **Opaque tools.** Screeners and "AI signals" output BUY/SELL without showing why, often built on indicators the trader does not use, and frequently implying certainty they do not have.
4. **Weak risk discipline.** Position size, stop placement and risk/reward are often decided emotionally after the entry decision, and plans, executions and reflections live in different places.

## 2. Target users

| Segment | Description | Primary need |
|---|---|---|
| Retail swing trader (primary) | Trades NSE cash equities on daily charts, holds days to weeks, 1–5 open positions | A daily shortlist of rule-conforming setups with clear levels and risk |
| Positional trader | Holds weeks to months; cares about structure and key levels | Structure state and level quality across the universe |
| Price-action investor | Uses support/resistance for entry timing on longer-term holdings | Explainable levels and invalidation |

Experience ranges from "getting started" to "experienced" (matches onboarding options in the current frontend).

## 3. Market opportunity (assumption)

> **ASSUMPTION:** India has a large and growing base of retail demat accounts and active equity traders, and a meaningful subset trades swing/positional styles with chart-based methods. No market sizing has been performed for this document; quantify before any commercial planning (OQ-VIS-01).

## 4. Positioning

**PriceAction AI is an explainable, rule-based price-action analysis and trade-planning workspace for NSE cash equities — not a signal service and not a broker.**

| PriceAction AI is | PriceAction AI is not |
|---|---|
| A decision-support tool that applies fixed, published rules to daily charts | An investment adviser or a tips/signal service |
| Transparent: every setup shows the pivots, zones and candles behind it | A black box that outputs BUY/SELL |
| A planning, paper-trading and journaling workflow | An order-execution platform (no order placement in MVP) |
| Comfortable saying "No trade" | A tool that always finds something to trade |

## 5. Differentiation: explainable pure price action

1. **Deterministic, published rules.** Swing pivots, BOS/CHoCH, zones and setups are defined precisely ([TRD-02..04](../trading/02_MARKET_STRUCTURE_RULES.md)) and versioned. The same chart always yields the same answer for a given ruleset version.
2. **Evidence-first UI.** Each setup shows "Why is this setup being considered?" with supporting and cautionary evidence linked to chart annotations (implemented visually in the current `/analysis/[symbol]` screen with sample data).
3. **No indicator noise.** No RSI/MACD/moving averages — the analysis matches how price-action traders already think.
4. **AI that explains, never decides.** The LLM rephrases and answers questions about computed facts; it never produces prices, levels or sizes ([ADR-009](../adr/ADR-009-LLM-EXPLANATION-ONLY.md)).
5. **Risk built into the plan.** Quantity derives from stop distance and the user's risk profile; plans cannot be saved without a stop.
6. **Closed loop.** Setup → plan → paper/actual trade → journal → backtest, all linked to the exact analysis snapshot.

## 6. Core product principles

| ID | Principle |
|---|---|
| VP-01 | No-trade is a valid outcome and is shown prominently. |
| VP-02 | Never show a bare BUY/SELL; every signal state carries its meaning (BUY WATCH ≠ entry). |
| VP-03 | Demo data is always labelled and never presented as live. |
| VP-04 | Every number on screen is traceable to an analysis snapshot, ruleset version and data source. |
| VP-05 | Calculations are deterministic; AI is explanatory only. |
| VP-06 | The user executes trades themselves on their broker; the product never places orders in MVP. |
| VP-07 | Parameters are hypotheses until backtested; the product says so. |
| VP-08 | Long-only actionable setups for cash equities; bearish reads are informational. |

## 7. Product objectives (MVP)

| ID | Objective | Measure (see BRD §9) |
|---|---|---|
| PO-01 | Replace manual daily chart review for the owner's universe | Daily scan of NIFTY 500 completes after market close on ≥ 95% of trading days |
| PO-02 | Make every setup explainable | 100% of setups show evidence linked to chart objects |
| PO-03 | Enforce plan-first risk discipline | 100% of plans have stop, target, engine-computed quantity |
| PO-04 | Enable evidence-based rule improvement | Backtests for all four setups with look-ahead tests passing in CI |
| PO-05 | Prove the SaaS architecture without commercial risk | Data modes isolated; no personal data redistribution possible by design |

## 8. MVP scope

In scope: registration/login, progressive onboarding with demo mode, Zerodha connection for personal daily data, NIFTY 500 EOD ingestion, deterministic analysis (structure, zones, liquidity, four setups, quality score), scanner, stock analysis with chart annotations, watchlists, risk-sized trade plans, paper trading, manual actual-trade records, journal, backtesting, AI explanations, in-app notifications.

Out of scope (MVP): order placement, intraday timeframes, F&O/derivatives, short-selling execution, weekly/monthly signals, broker order/holding sync, mobile apps, social features, paid subscriptions/billing, licensed SaaS data.

## 9. Long-term SaaS vision

Personal-first, SaaS-ready:

1. **Phase A — Personal (MVP):** single owner using personal Kite data.
2. **Phase B — Private beta:** invited users on DEMO data or their own personal connections, subject to provider terms review (OQ-SEC-01).
3. **Phase C — SaaS:** licensed market data shared across tenants, subscription plans via `subscription_entitlements`, organisation tenants, 2FA, RLS, formal compliance review. Possible extensions: weekly context, alerts by email/push, broker read-only sync, additional brokers (Upstox is listed as "Planned" in the current settings UI), multi-timeframe.

SaaS launch gates (licensing, legal/regulatory review) are defined in [PRD-02 §10](02_BRD.md) and [OPS-05](../operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md).

## 10. Business risks

| Risk | Impact | Mitigation |
|---|---|---|
| Regulatory classification (research analyst / investment adviser rules) if commercialised | Launch blocked or liability | Legal review before SaaS; decision-support framing; no personalised advice; disclaimers ([OPS-05](../operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md)) |
| Data licensing (personal API data cannot be redistributed) | SaaS blocked | Data-mode isolation; licensed vendor before SaaS |
| Rules not profitable | Low value / user harm | Backtests, hypotheses labelled, no performance claims |
| Users over-trust AI text | Harmful decisions | Explanation-only LLM, validator, disclaimers |
| Provider dependency (single broker API) | Outage, terms change | Provider abstraction ([ADR-007](../adr/ADR-007-MARKET-DATA-PROVIDER-ABSTRACTION.md)) |
| Solo-developer bandwidth | Delays | Modular monolith, milestone roadmap, CI automation |

## 11. Open questions

| ID | Question |
|---|---|
| OQ-VIS-01 | Market sizing and willingness-to-pay research before Phase C. |
| OQ-VIS-02 | Brand/legal name availability and trademark check for "PriceAction AI". |
