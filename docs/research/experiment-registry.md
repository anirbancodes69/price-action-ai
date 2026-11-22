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
| S01-4a-IS-chunks | 2026-11-21 | `liquidity_sweep_reversal` | `pa-intraday 0.3.0` | 4a, 7 chunks | EXPLORATION | 2024-01-02..2025-09-23 | as above | as above | Completed 2026-11-21 (code da8b0af, 7/7 chunks rc=0, 427 sessions, 3 special sessions excluded). 11,363 trades; win 32.5%; avg R gross -0.16, net -0.33; PF 0.54; net P&L -₹1,842,560 at fixed ₹500 risk unit (unlimited-capital 4a, so drawdown % is not meaningful); cost drag 15.5% of gross. Every anchor, every 15m regime, every half hour and all 21 months have negative net avg R (best month 2025-04 -0.19R, worst 2025-09 -0.47R). Skips: SKIPPED_RR_DEGRADED 7556, ALREADY_IN_POSITION 3627. Flags: survivorship_bias_risk, costs_unverified, UNSUPPORTED_DIRECTION:SHORT. Raw output kept outside the repo (research dir, merged.json). G-3 count (2026-11-22): 32 pairs, 64 trades (0.6%) share a swept price within a session and symbol; no effect on the aggregate. No parameter changed | this section |

### 1.2 Pre-registration: Strategy 02, experiment 4a, in-sample (registered 2026-11-22, before any chunk ran)

Same protocol as §1.1, fixed in advance. Any change is a new, separately logged experiment.

| Item | Value |
|---|---|
| Strategy / ruleset | `failed_breakout` (`FAILED_BREAKDOWN_RECLAIM`), `pa-intraday 0.4.0` (`0.3.0` plus `setup.failed_breakout_enabled`, `setup.failed_break_max_bars` = 6; approved P-1..P-5, 2026-11-22) |
| Experiment / purpose | `4a` trade-level quality; `EXPLORATION` on the in-sample segment only |
| Sessions and split | Identical to §1.1: 427 in-sample sessions (2024-01-02 to 2025-09-23). Out-of-sample (142 sessions, 2025-09-24 to 2026-04-24) and holdout (143 sessions, 2026-04-27 to 2026-11-19) are not touched |
| Chunks (run sequentially, each saved) | Same seven as §1.1 |
| Sizing | FIXED, capital ₹1,00,000, risk 0.5% = ₹500 per trade; no position, open-risk, daily-loss, streak, value or capital limit; one open trade per symbol |
| Costs / slippage | `nse-intraday-assumed-0` (unverified, D-6); 0.05% adverse slippage on entries and stop exits only |
| Universe, data, exclusions | As §1.1: today's NIFTY 50 (`--members-on 2026-11-19`), 1D-bar previous-day levels (D-7), the special sessions and the previous-day exclusions, reported per run |
| Regime key | `context_15m`, fixed before results |
| Also reported | by anchor, month, half hour; skip counts; the number of bars from breakdown to reclaim (descriptive only, not used to tune `N`); trades sharing a level. Strategy 01's in-sample result is shown beside it as context, never pooled |
| Flags | `survivorship_bias_risk`, `costs_unverified`, `UNSUPPORTED_DIRECTION:SHORT` |
| Decision rule, fixed now | The run changes no parameter. If gross average R is not positive, or net average R is negative in every anchor and regime as it was for Strategy 01, the strategy goes to the owner for a decision (park, or a hypothesis-led variant under the 3-round limit of [criteria §5](validation-criteria.md#5-improvement-rounds)). No variant is tried on this in-sample data before that decision. No result of this run is used to choose between experiments on the out-of-sample or holdout data |
| Code | `main` at `b0af09c` (Stage 3 merged, PR #75); chunks merged by `scripts/merge_backtests.py` |
| Harness check | A 4-session smoke run (2024-01-02..2024-01-05, 45 trades, about 44 s) confirmed the harness runs this strategy end to end. Those 4 sessions are inside chunk 1 and are re-run with it; the smoke figures are not recorded as a result |

| Experiment | Date | Strategy | Ruleset | Type | Purpose | Data range | Exclusions | Flags | Result | Report |
|---|---|---|---|---|---|---|---|---|---|---|
| S02-4a-IS-chunks | 2026-11-22 | `failed_breakout` | `pa-intraday 0.4.0` | 4a, 7 chunks | EXPLORATION | 2024-01-02..2025-09-23 | as above | as above | Completed 2026-11-22 (code bffbb93, 7/7 chunks rc=0, 427 sessions, 3 special sessions excluded). 10,353 trades; win 33.8%; avg R gross -0.15, net -0.31; PF 0.52; net P&L -₹15,89,298 at fixed ₹500 risk unit (gross -₹7,93,868, costs ₹7,95,430; unlimited-capital 4a, so drawdown % is not meaningful); cost drag 16.4% of gross. Every anchor, every 15m context, every half hour and all 21 months have negative net avg R (best month 2025-04 -0.08R, worst 2024-10 -0.42R; BULLISH context worst at -0.42R). Exits: SESSION_END 5,122, STOP 4,670, STOP_GAP 7, TARGET 554. Skips: SKIPPED_RR_DEGRADED 4,158, ALREADY_IN_POSITION 2,133. Trades sharing a level in a session and symbol: 2 pairs, 4 trades (0.04%). Bars from breakdown to reclaim: not reported (the trade record does not store the breakdown bar; descriptive only, no parameter depends on it). Strategy 01 beside it (context, not pooled): -0.16 gross / -0.33 net, PF 0.54. **Decision rule triggered** (gross not positive; net negative in every anchor and regime): owner decision 2026-11-22 = park (`DEFERRED`), no variant tried, improvement rounds 0 of 3. Raw output kept outside the repo (research dir, merged.json) | this section; [strategy page §21](../strategies/failed-breakout.md#21-in-sample-results) |

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

## 4. Framework diagnosis experiments

Pre-registered 2026-11-22, before any of them ran, in the [framework diagnosis plan](framework-diagnosis-plan.md) (hypotheses, methods, statistics and decision rules fixed there). These test the shared replay machinery, not a strategy, and change no ruleset. All except DX-0 use only the in-sample segment (2024-01-02..2025-09-23).

| Experiment | Date | What runs | Data | Result | Flags | Report |
|---|---|---|---|---|---|---|
| PRE-005 (DX-0) | 2026-11-22 | `pa-intraday 0.1.0` combined, FIXED sizing, capital ₹1,00,000, the same 4 chunks as PRE-003 (2026-01-01..02-27, 03-02..05-05, 05-06..07-03, 07-06..08-31) | 164 sessions, 2026-01-01..2026-08-31, today's NIFTY 50 | Completed 2026-11-22 (4/4 chunks rc=0; input hashes 1229094ed2d0, 59e0a79fa0b1, bdf5ea618d3e, bc4b3efafab3). 570 trades; win 30.7%; avg R gross -0.18, net -0.37; PF 0.56; net -₹50,433 (gross -₹22,119, costs ₹28,314); both halves negative; BREAKOUT_RETEST 437 trades -0.21R gross. Variant D (PRE-003) did better on the same days (-0.18R net) but also loses before costs. Context only: no decision may rest on it (plan §3) | `survivorship_bias_risk`, `costs_unverified`, `NOT_ISOLATED` | [log §7](../trading/backtests/2026-11-20-pa-intraday-0.1.0-nifty50.md#7-baseline-pa-intraday-010-on-2026-01-01-to-2026-08-31-t-i134-dx-0) |
| DX-3 | 2026-11-22 | R decomposition by stop-distance bucket (Strategy 01 and 02) | in-sample trades (11,363 and 10,353) | Completed. Before slippage and charges: -0.009R (S01), -0.019R (S02). Entry slippage 0.10/0.09R, stop-exit slippage 0.05/0.04R, charges 0.16/0.16R; 1-2% stops near break-even (-0.07/-0.10R net), 0.3-0.5% stops -0.40R net. Fill gap -0.009/-0.007R | `survivorship_bias_risk`, `costs_unverified` | [report §4](framework-diagnosis-report.md#4-dx-3-where-the-loss-comes-from-average-per-trade-in-r) |
| DX-1 | 2026-11-22 | Drift baseline, 09:30 open to 15:15 open, and seeded random entry bars | 21,250 in-sample instrument-sessions | Completed. +0.005% (CI -0.060, +0.070) from 09:30; +0.014% (CI -0.026, +0.054) from random bars; no sustained monthly sign | `survivorship_bias_risk` | [report §5](framework-diagnosis-report.md#5-dx-1-dx-5-dx-7) |
| DX-4 | 2026-11-22 | Matched random-entry control, 5 seeds per trade (Strategy 01 and 02), common 2.5R exit | in-sample | Completed. Gross R strategy minus controls: S01 +0.009 (CI -0.010, +0.027), S02 +0.037 (CI +0.019, +0.056); neither material (< 0.05R). Controls -0.177/-0.193R gross, -0.332/-0.341R net | `survivorship_bias_risk`, `costs_unverified` | [report §3](framework-diagnosis-report.md#3-dx-4-and-dx-2-strategies-against-random-entries) |
| DX-2 | 2026-11-22 | Signal forward returns vs random bars | in-sample | Completed. Equal to random bars in 14 of 16 comparisons; S02 12-bar and session-exit returns +0.02% better (material under the 0.02% rule, not in stop units). Skipped signals not recoverable | `survivorship_bias_risk` | [report §3](framework-diagnosis-report.md#3-dx-4-and-dx-2-strategies-against-random-entries) |
| DX-5 | 2026-11-22 | Exit-model bounds on Strategy 01 entries (common 2.5R exit) | in-sample | Completed. Target-first collision +0.000R; no stop slippage +0.054R (material); hold 6 / 12 bars / to session exit +0.032 / +0.024 / +0.016R (none material) | `survivorship_bias_risk`, `costs_unverified` | [report §5](framework-diagnosis-report.md#5-dx-1-dx-5-dx-7) |
| DX-7 | 2026-11-22 | Simulator spot check (20 trades, seed 1) and gap count | in-sample | Completed. 20 of 20 trades agree with a separate recomputation from the raw bars; 5 instrument-sessions with fewer than 75 bars | — | [report §5](framework-diagnosis-report.md#5-dx-1-dx-5-dx-7) |
| DX-6 | 2026-11-23 | Charges check against the broker's published schedule (Groww; the owner has no Zerodha contract notes, plan §4a item 7) | the saved Strategy 01 and 02 4a in-sample trades | Completed. Statutory items match (STT 0.025% sell, stamp 0.003% buy, SEBI 0.0001%, GST 18%, NSE exchange 0.00297%; Groww's pricing page says 0.00307%). Brokerage differs: Groww 0.1% per order capped at ₹20, ours 0.03% capped at ₹20. Charges per trade: 0.163R to 0.168R (S01), 0.156R to 0.161R (S02), +0.005R; net about -0.333R and -0.316R. Not modelled: investor-protection-fund charge (0.0001%). Published rates read 2026-11-23, no dated history verified (OQ-BT-02); slippage not checked | `survivorship_bias_risk`, `costs_unverified` | [report §6](framework-diagnosis-report.md#6-dx-6-charges-check-published-schedule) |

## 5. Fast screening experiments

Pre-registered 2026-11-23 in the [fast screening protocol](fast-screening-protocol.md) (approved by the owner the same day); screen run 2026-11-23, results in the [report](fast-screening-report.md). Family size N = 13; promotion needs a gross difference to the matched random-entry control of at least +0.05R with a 99% interval excluding zero (screen, 2024, 10 stocks or the saved trades) and confirmation on 2025-01-01..2025-09-23 over all 50 stocks. Out-of-sample and holdout are not used.

| Experiment | Date | What runs | Data | Result | Flags | Report |
|---|---|---|---|---|---|---|
| T0-1..T0-4 | 2026-11-23 | Stop-distance filters (≥ 0.75%, ≥ 1.00%) on the saved Strategy 01 and 02 trades vs matched controls | 2024 screen (50 stocks); 2025 confirmation not run (nothing promoted) | Screen done, none promoted. Gross edge over control +0.015 to +0.053R, every 99% interval includes zero; gross R -0.022 to +0.019; net -0.07 to -0.13R | `survivorship_bias_risk`, `costs_unverified` | [report §2](fast-screening-report.md#2-screen-results-2024) |
| M1..M3 × 3 filters (9 variants) | 2026-11-23 | Minimal entries (opening-range breakout, previous-day-high break, failed opening-range breakdown) with stop filters none, ≥ 0.75%, ≥ 1.00% vs matched controls | 2024 screen on 10 stocks; confirmation 2025 not run (nothing promoted) | Screen done, none promoted. M1 and M2 worse than random in all six variants (-0.10 to -0.15R gross, 99% intervals below zero); M3 no difference (+0.02R, 569 trades), wide-stop M3 only 100 and 39 trades | `survivorship_bias_risk`, `costs_unverified` | [report §2](fast-screening-report.md#2-screen-results-2024) |

## 6. Daily Gate 0 experiments

Pre-registered 2026-11-23 in the [Gate 0 plan](gate0-daily-diagnosis-plan.md) (approved by the owner the same day) and run 2026-11-23 on **data version 2026-11-23** (one backfill run, 2015-01-01..2026-11-19, today's NIFTY 50; in-sample 2015-01-01..2022-02-15, 1,761 sessions; out-of-sample and holdout prices not loaded). Three runs (plan §8.2): run 1 as registered, run 2 after the data fixes, run 3 after the sizing fix and the planned-risk R basis; results below are run 3. Report: [gate0-daily-diagnosis-report.md](gate0-daily-diagnosis-report.md).

| Experiment | Date | What runs | Data | Result | Flags | Report |
|---|---|---|---|---|---|---|
| DG-0 | 2026-11-23 | Data audit: coverage, missing sessions, OHLC sanity, gaps above 15%, adjustedness | daily bars, data version 2026-11-23 | Done. Adjusted for splits and bonuses, not for demergers and mergers: 3 unadjusted events (ADANIENT 2015-06-03 and 2018-09-06, GRASIM 2017-07-19) cut, 1 bad bar dropped, 4 special sessions excluded; ONGC 2020-03-23 genuine (COVID crash) | `survivorship_bias_risk` | [report §3](gate0-daily-diagnosis-report.md#3-dg-0-data-audit) |
| DG-1 | 2026-11-23 | Drift baseline: buy the next open, hold 5, 10, 20 sessions | in-sample | Done. Gross mean +0.23% (5), +0.62% (10), +1.38% (20; interval +0.45 to +2.21) per entry; 2017, 2020, 2021 positive, 2015, 2018, 2022 negative | `survivorship_bias_risk` | [report §4](gate0-daily-diagnosis-report.md#4-dg-1-and-dg-2) |
| DG-2 | 2026-11-23 | Friction decomposition by stop distance, delivery schedule | in-sample | Done. 0.30R (2%), 0.23R (3%), 0.19R (4%), 0.16R (5%), 0.12R (8%): ADR-019's table confirmed | `costs_unverified` | [report §4](gate0-daily-diagnosis-report.md#4-dg-1-and-dg-2) |
| DG-3 | 2026-11-23 | Random-entry baseline grid (4 stops × 3 targets × 2 holds = 24 configurations), 5 seeds, 3 slippage levels | in-sample | Done. Gross +0.00 to +0.12R, net -0.29R (2% stops) to about 0 (5% to 8% stops, 20 sessions: -0.04 to +0.01R, intervals include zero); no net interval above zero | `survivorship_bias_risk`, `costs_unverified` | [report §5](gate0-daily-diagnosis-report.md#5-dg-3-random-entry-baseline-grid-the-bar-a-strategy-must-beat) |
| DG-4 | 2026-11-23 | Simulator spot check, 20 trades (5 overnight gap exits) | in-sample | Done. 20 of 20 agree | — | [report §2](gate0-daily-diagnosis-report.md#2-hypotheses) |
| DG-5 | 2026-11-23 | Survivorship and coverage sensitivity (44 full-history stocks vs all) | in-sample | Done. Difference within ±0.02R, intervals include zero (a weak test) | `survivorship_bias_risk` | [report §5](gate0-daily-diagnosis-report.md#5-dg-3-random-entry-baseline-grid-the-bar-a-strategy-must-beat) |
| DG-6 | 2026-11-23 | Charges sensitivity (exchange rate, brokerage) | in-sample | Done. Exchange rate under 0.001R; brokerage 0 about +0.05R; cap ₹40 about 0.001R | `costs_unverified` | [report §5](gate0-daily-diagnosis-report.md#5-dg-3-random-entry-baseline-grid-the-bar-a-strategy-must-beat) |
