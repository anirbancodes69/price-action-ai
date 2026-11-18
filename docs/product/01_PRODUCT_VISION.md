# Product Vision

| Field | Value |
|---|---|
| Document ID | PRD-01 |
| Version | 0.2.0 |
| Status | Approved for intraday MVP planning (ADR-014) |
| Owner | Product Owner |
| Last updated | 2026-11-17 |
| Related | [ADR-014](../adr/ADR-014-PERSONAL-INTRADAY-WORKSTATION.md) · [PRD-02 BRD](02_BRD.md) · [PRD-03 PRD](03_PRD.md) · [TRD-01 Methodology](../trading/01_TRADING_METHODOLOGY.md) · [OPS-05 Compliance](../operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md) |

## 1. Problem statement

The owner trades NSE cash equities intraday with price action and faces five recurring problems:

1. **Too many charts, too little time.** Watching structure, levels and breakouts on 5- and 15-minute charts for 50 stocks during a live session is not possible by eye; opportunities are missed or found late.
2. **Inconsistent rules.** What counts as a breakout, a retest or a higher low changes from day to day. Without fixed definitions, results cannot be reviewed or improved.
3. **Repainting and hindsight.** Many chart tools draw pivots and signals that only exist in hindsight, which makes setups look better than they were.
4. **Risk decided too late.** Size, stop and risk/reward are often decided after the entry decision, and daily loss discipline depends on willpower.
5. **No honest record.** Plans, executions and reflections live in different places, so actual performance after costs is not measured.

## 2. Target user

| User | Description | Primary need |
|---|---|---|
| The owner (only user in the MVP) | Trades NSE cash equities intraday, manual execution on the broker platform, 1–2 positions at a time; planning capital ₹1,00,000 (HYPOTHESIS) | A live shortlist of rule-conforming intraday setups with levels, size and risk checked before the trade, and a journal that measures real results |

Retail swing traders, positional traders and price-action investors were the users of the earlier daily scope; they are not served by the MVP (ADR-014).

## 3. Market opportunity

Not applicable for the personal MVP. Any future commercial use needs market sizing first (OQ-VIS-01).

## 4. Positioning

**PriceAction AI is a personal, explainable, rule-based intraday price-action workstation for NSE cash equities — not a signal service, not a trading bot and not a broker.**

| PriceAction AI is | PriceAction AI is not |
|---|---|
| A decision-support tool that applies fixed, published rules to closed 5m and 15m bars | An investment adviser, a tips service or an autonomous trading bot |
| Transparent: every setup shows the pivots, zones, levels and bars behind it, from the moment they were known | A tool that repaints or shows hindsight signals |
| A planning, monitoring, paper-trading and journaling workflow with hard risk limits | An order-execution platform (no order placement) |
| Comfortable saying "No trade" | A tool that always finds something to trade |

## 5. Differentiation: explainable pure price action

1. **Deterministic, published rules.** Swing pivots, BOS/CHoCH, zones, session levels and setups are defined precisely ([TRD-02..04](../trading/02_MARKET_STRUCTURE_RULES.md)) and versioned (`pa-intraday`). The same bars always yield the same answer for a given ruleset version.
2. **No repainting.** Everything is evaluated on closed bars and shown only from the moment it became known; 15m context never peeks at a forming bar (TRD-01 MP-03, MP-10).
3. **Evidence-first UI.** Each setup shows why it is considered, with supporting and cautionary evidence linked to chart annotations.
4. **No indicator noise.** No RSI/MACD/moving averages — the analysis matches how price-action traders already think.
5. **Risk built into the plan.** Quantity derives from stop distance, the ₹ position cap and the account limits; a plan that would breach the daily loss limit, the losing-streak limit or the open-risk limit is blocked.
6. **Closed loop.** Setup → plan → paper/actual trade → journal → backtest, all linked to the exact inputs and ruleset version, with net P&L after costs.

## 6. Core product principles

| ID | Principle |
|---|---|
| VP-01 | No-trade is a valid outcome and is shown prominently. |
| VP-02 | Never show a bare BUY/SELL; every signal state carries its meaning and its time (`signal_at`, `valid_until`). |
| VP-03 | Demo data is always labelled and never presented as live. |
| VP-04 | Every number on screen is traceable to its inputs, ruleset version and data source, and shows how fresh it is. |
| VP-05 | Calculations are deterministic; AI (deferred) would only explain. |
| VP-06 | The owner executes trades on the broker platform; the product never places orders. |
| VP-07 | Parameters are hypotheses until backtested and forward-logged; the product says so. |
| VP-08 | Long-only actionable setups; bearish reads are informational. |
| VP-09 | Intraday only: nothing is planned or simulated overnight; the session-end exit is part of every plan. |

## 7. Product objectives (MVP)

| ID | Objective | Measure (see BRD §9) |
|---|---|---|
| PO-01 | Replace manual intraday chart watching for NIFTY 50 | Analysis of the universe is available within 60 s of each 5m close on ≥ 95% of bars in a session |
| PO-02 | Make every setup explainable and repaint-free | 100% of setups show evidence linked to chart objects; no-look-ahead tests pass in CI |
| PO-03 | Enforce plan-first risk discipline | 100% of plans have stop, target, engine-computed quantity; 0 plans accepted that breach an account limit |
| PO-04 | Measure real performance | Journal shows net P&L after costs per trade and per session for paper and actual books |
| PO-05 | Enable evidence-based rule improvement | Intraday backtests and a forward paper log exist for every MVP setup |

## 8. MVP scope

In scope: owner login, intraday market data for NIFTY 50 (5m, 15m, daily context) from the owner's broker data subscription, DEMO intraday data, deterministic analysis (structure, zones, session levels, four MVP setups, quality score), intraday scanner, stock analysis with 5m/15m chart annotations, watchlist, risk-checked trade plans with account limits, active-trade monitoring with live P&L, paper trading, manual actual-trade records, journal with net P&L, intraday backtesting, in-app notifications.

Deferred (not removed): onboarding flow, subscription entitlements and billing, data-source selection UI, licensed data mode, AI explanations, CSV export, multi-user and team features, email/push delivery.

Out of scope: order placement, F&O/derivatives, short-selling execution, overnight positions, 1-minute signals, broker order/holding sync, mobile apps, social features.

## 9. Possible future directions

The architecture keeps a later expansion possible without promising it:

1. **Wider personal use:** more symbols (NIFTY 100), 1-minute execution refinement, intraday shorts (needs an ADR superseding C-12), trend-continuation and sweep setups once validated.
2. **Sharing with others:** invited users on DEMO data or their own broker connections, subject to provider terms (OQ-SEC-01).
3. **Commercial SaaS:** licensed market data, subscriptions, 2FA, RLS and formal legal/regulatory review. The launch gates in [PRD-02 §12](02_BRD.md) and [OPS-05](../operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md) still apply.

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Rules not profitable after costs | Financial loss | Backtests with verified intraday costs, forward paper log before real money, hypotheses labelled, no performance claims |
| Intraday data unavailable, delayed or incomplete | Missed or wrong signals | Bar-close fetching with reconciliation, freshness shown on every screen, provider abstraction ([ADR-007](../adr/ADR-007-MARKET-DATA-PROVIDER-ABSTRACTION.md)) |
| Over-trust in the tool during a fast session | Harmful decisions | Signals with validity windows, hard account limits, no order placement |
| Provider terms or cost change | Data blocked | Provider abstraction; Kite and Groww both evaluated (T-201, T-203) |
| Regulatory classification if ever commercialised | Launch blocked | Personal use now; legal review before any sharing |
| Solo-developer bandwidth | Delays | Modular monolith, milestone roadmap, CI automation |

## 11. Open questions

| ID | Question |
|---|---|
| OQ-VIS-01 | Market sizing and willingness-to-pay research before any commercial phase. |
| OQ-VIS-02 | Brand/legal name availability and trademark check for "PriceAction AI". |
