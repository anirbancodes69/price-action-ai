# Experiment Registry

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Status | Current. Append only: results are never edited away or overwritten |
| Date | 2026-11-21 |
| Related | [Independent backtesting standards §5.3](independent-backtesting-standards.md#53-run-record) · [Validation criteria](validation-criteria.md) · [Backtest logs](../trading/backtests/) |

One row per experiment, including failures and discarded variants (this makes multiple testing visible). Full reports live beside the strategy page or under `docs/trading/backtests/`; this page is the index. Required fields: [standards §5.3](independent-backtesting-standards.md#53-run-record).

## 1. Independent strategy experiments

### 1.1 Pre-registration: Strategy 01, experiment 4a, in-sample (registered 2026-11-21, before any chunk ran)

Fixed in advance so that nothing below can change after results are seen. Any change is a new, separately logged experiment.

| Item | Value |
|---|---|
| Strategy / ruleset | `liquidity_sweep_reversal`, `pa-intraday 0.3.0` (`0.2.0` plus structure exit off, approved P-4) |
| Experiment / purpose | `4a` trade-level quality; `EXPLORATION` on the in-sample segment only |
| Sessions | 712 usable (718 stored minus the 5 special sessions minus the first session, which has no previous day); chronological 60 / 20 / 20 split (`app/backtest/splits.py`) |
| In-sample (this run) | 427 sessions, 2024-01-02 to 2025-09-23 |
| Out-of-sample (not touched) | 142 sessions, 2025-09-24 to 2026-04-24 |
| Holdout (not touched) | 143 sessions, 2026-04-27 to 2026-11-19 |
| Chunks (run sequentially, each saved) | 2024-01-02..03-28, 2024-04-01..06-28, 2024-07-01..09-30, 2024-10-01..12-31, 2025-01-01..03-28, 2025-04-01..06-30, 2025-07-01..09-23 |
| Sizing | FIXED, capital ₹1,00,000, risk 0.5% = ₹500 per trade; no position, open-risk, daily-loss, streak, value or capital limit; one open trade per symbol |
| Costs / slippage | `nse-intraday-assumed-0` (unverified, D-6); 0.05% adverse slippage on entries and stop exits only (audit R-2) |
| Universe | today's NIFTY 50 (`--members-on 2026-11-19`): `survivorship_bias_risk` |
| Data | Kite 5m, 15m and 1D bars stored for 2024-01-01 to 2026-11-19; previous-day levels from the 1D bars (D-7) |
| Exclusions | the 5 special sessions (whole session); instrument-sessions with no or inconsistent previous-day bar (`MISSING_PREV_DAY_LEVELS`, `INCONSISTENT_PREV_DAY_LEVELS`); reported per run |
| Regime key | `context_15m`, the 15m structure state at the signal (BULLISH, BEARISH, SIDEWAYS, TRANSITION), fixed before results |
| Also reported | by anchor (`PDL`, `OR_LOW`, `SWING_LOW_5M`, `SWING_LOW_15M`, `EQUAL_LOWS`, `ZONE`), month, half hour; skip counts (including `SKIPPED_RR_DEGRADED`); trades sharing a swept price (G-3) |
| Flags | `survivorship_bias_risk`, `costs_unverified`, `UNSUPPORTED_DIRECTION:SHORT` |
| What this run may do | produce the first independent in-sample evidence. It changes no parameter. A weak result goes through the failure path ([process §6](../development/strategy-development-process.md#6-when-validation-fails)) with a recorded hypothesis and a new ruleset version |
| Code | harness at the merge commit of the branch `feat/strategy-01-4a-in-sample`; chunks merged by `scripts/merge_backtests.py` |

| Experiment | Date | Strategy | Ruleset | Type | Purpose | Data range | Exclusions | Flags | Result | Report |
|---|---|---|---|---|---|---|---|---|---|---|
| S01-4a-IS-chunks | 2026-11-21 | `liquidity_sweep_reversal` | `pa-intraday 0.3.0` | 4a, 7 chunks | EXPLORATION | 2024-01-02..2025-09-23 | as above | as above | Running; filled in below as each chunk is saved | this section |

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
