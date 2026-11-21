# Experiment Registry

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Status | Current. Append only: results are never edited away or overwritten |
| Date | 2026-11-21 |
| Related | [Independent backtesting standards §5.3](independent-backtesting-standards.md#53-run-record) · [Validation criteria](validation-criteria.md) · [Backtest logs](../trading/backtests/) |

One row per experiment, including failures and discarded variants (this makes multiple testing visible). Full reports live beside the strategy page or under `docs/trading/backtests/`; this page is the index. Required fields: [standards §5.3](independent-backtesting-standards.md#53-run-record).

## 1. Independent strategy experiments

None yet. As of 2026-11-21 no single-strategy experiment has been run. The tracker shows every strategy's independent backtest as `NOT_STARTED`.

| Experiment | Date | Strategy | Ruleset | Type | Purpose | Data range | Exclusions | Flags | Result | Report |
|---|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | — | — |

## 2. Pre-framework experiments (combined strategies)

These ran several strategies together under one position limit and one score ranking, before [ADR-018](../adr/ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md). They are kept as history. They are `NOT_ISOLATED` and **are not evidence for any single strategy**, including the per-setup breakdowns inside them (the strategies competed for two slots, ordered by a score that did not rank outcomes). Figures are copied from the linked log and were not re-derived.

| Experiment | Date | What ran | Data | Result (from the log) | Flags | Log |
|---|---|---|---|---|---|---|
| PRE-001 | 2026-11-20 | `pa-intraday 0.1.0`: ORB, PDH break, Breakout-Retest together, FIXED sizing, capital ₹1,00,000 | 55 sessions, 2026-09-01..2026-11-19, today's NIFTY 50 | 176 trades, net −₹16,794, profit factor 0.52, −0.20R gross per trade | `survivorship_bias_risk`, `short_history`, `costs_unverified`, `NOT_ISOLATED` | [log](../trading/backtests/2026-11-20-pa-intraday-0.1.0-nifty50.md) |
| PRE-002 | 2026-11-20 | Variants A-D (min stop distance, retest off), same 55 sessions | as PRE-001 | D: +₹345 over 48 trades, chosen after seeing A-C on the same days (selection bias) | as above | log §4 |
| PRE-003 | 2026-11-20 | Variant D on 164 earlier sessions | 2026-01-01..2026-08-31 | net −₹13,310, profit factor 0.63, negative before costs | as above | log §5 |
| PRE-004 | 2026-11-21 | One-day real-bar smoke check of `pa-intraday 0.1.0` and `0.2.0` for T-I141 | 2026-11-19 | A functional check that the engine runs (T-I141: 0.1.0 unchanged, input hash 720ae90d33c0, 3 trades, +₹441). Not a backtest result | — | TASKS.md T-I141 |

The variant scripts for PRE-002 and PRE-003 were temporary and are not in the repository, so those runs cannot be reproduced from it.

## 3. Non-run records

| Record | Date | Purpose |
|---|---|---|
| [Research readiness audit](adaptive-strategy-validation/RESEARCH_READINESS.md) | 2026-11-21 | Audit of data, backtester reliability and strategy executability. No backtest was run |
