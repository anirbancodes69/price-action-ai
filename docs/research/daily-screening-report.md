# Daily Screening Report (Ideas 1 to 4)

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Date | 2026-11-23 |
| Protocol | [daily-screening-protocol.md](daily-screening-protocol.md) (approved by the owner 2026-11-23; family N = 8, fixed) |
| Status | Screen done. **No variant was promoted, so the confirmation step did not run, as the protocol says.** Out-of-sample and holdout prices were never loaded |
| Data | Data version 2026-11-23, today's NIFTY 50 (50 stocks), Gate 0 exclusions and series cuts applied. Screen segment 2015-01-01..2018-07-24 (881 sessions); the confirmation segment (2018-07-25..2022-02-15) was not read for any entry |
| Code | `python-engine/app/backtest/diagnostics/daily_screen.py` (detectors), `daily_data.py`, `scripts/run_daily_screen.py`, with 10 new tests; no detector, ruleset or replay behaviour changed |

Hypothetical, simulated results only (TRD-06 BT-06). Aggregates only; raw output stays outside the repository. Edge = the strategy's average R minus its month-matched random-entry controls' (5 per trade), planned-risk basis, month-block bootstrap (10,000 resamples, seed 1); stop 4% to 10%, 20-session time stop, no target, 0.05% slippage each side, Groww delivery charges.

## 1. Result in one paragraph

None of the eight variants meets the pre-registered promotion rule. The two ideas that buy strength, the **trend pullback** (P1a) and the **long-range breakout** (B2a, B2b), do **worse than random entries** by 0.25R to 0.39R, with 99% intervals below zero, the same pattern as the intraday breakouts. The **failed breakdown at support** (F3a) beats its controls by +0.38R (99% interval +0.13 to +0.67) but its own gross average R is -0.04R, so it fails the rule that the gross average must be above zero; F3b has too few trades (88) and an interval that includes zero. The **selling climax** (C4a, C4b) produced only 6 and 3 trades once the 4% to 10% stop range was applied, so its figures mean nothing. P1b has 39 trades.

## 2. Screen results

| Variant | Idea | Trades | Gross R: strategy / control | Gross edge [99% interval] | Net R: strategy / control | Promoted |
|---|---|---|---|---|---|---|
| P1a | Trend pullback, depth ≥ 3% | 93 | -0.010 / +0.376 | -0.386 [-0.618, -0.157] | -0.152 / +0.233 | no |
| P1b | Trend pullback, depth ≥ 6% | 39 | +0.228 / +0.228 | +0.001 [-0.283, +0.301] | +0.090 / +0.091 | no |
| B2a | Breakout of the 50-session high | 210 | +0.017 / +0.271 | -0.254 [-0.337, -0.175] | -0.098 / +0.156 | no |
| B2b | Breakout of the 100-session high | 154 | +0.050 / +0.295 | -0.245 [-0.340, -0.159] | -0.065 / +0.181 | no |
| F3a | Failed breakdown, 20-session low | 162 | -0.044 / -0.419 | +0.376 [+0.129, +0.670] | -0.182 / -0.556 | no |
| F3b | Failed breakdown, 50-session low | 88 | -0.046 / -0.298 | +0.252 [-0.069, +0.658] | -0.183 / -0.434 | no |
| C4a | Selling climax, fall ≥ 4% | 6 | +2.198 / -0.089 | +2.287 [+0.955, +2.836] | +2.059 / -0.224 | no |
| C4b | Selling climax, fall ≥ 6% | 3 | +1.718 / -0.346 | +2.064 [+0.825, +2.684] | +1.590 / -0.469 | no |

Promotion needs at least 100 trades, average gross R above 0, an edge of at least +0.05R and a 99% interval above zero ([protocol §5](daily-screening-protocol.md#5-the-control-and-statistics-fixed-now)). Net R is shown for strategy and control; the Groww schedule and the fill-risk R basis are in the raw output and give the same picture.

How many signals reached a trade:

| Variant | Signals | Stop outside 4% to 10% | One-position skip | Fill skipped | Trades | Control draws unfilled |
|---|---|---|---|---|---|---|
| P1a | 403 | 281 | 21 | 8 | 93 | 0 |
| P1b | 82 | 38 | 3 | 2 | 39 | 0 |
| B2a | 1023 | 659 | 128 | 26 | 210 | 0 |
| B2b | 766 | 503 | 88 | 21 | 154 | 0 |
| F3a | 607 | 398 | 1 | 46 | 162 | 0 |
| F3b | 310 | 193 | 0 | 29 | 88 | 0 |
| C4a | 17 | 6 | 0 | 5 | 6 | 0 |
| C4b | 7 | 3 | 0 | 1 | 3 | 0 |

## 3. Readings

- **Buying strength loses to random entry, again.** P1a (-0.39R), B2a (-0.25R) and B2b (-0.24R) have intervals entirely below zero. The controls are strongly positive in the screen period (+0.27R to +0.38R gross: a rising market with wide stops and 20-session holds), and the strategies earn about zero gross. This matches the intraday finding that breakout entries underperform random entries, now at a daily horizon and wide stops.
- **F3a is a near miss on a technicality, not a result to chase.** Its edge is +0.38R, but the controls are -0.42R: failed breakdowns happen in sell-off months, and a month-matched control inherits the sell-off. So F3a lost less than random entries in falling months, yet its own gross is -0.04R and net -0.18R. Promoting it by changing the rule after seeing this would be exactly the post-hoc selection the protocol forbids.
- **The stop range is a strong filter.** 46% to 70% of the signals of P1, B2 and F3 fall outside 4% to 10% and are not traded; C4 nearly vanishes (17 and 7 signals, 6 and 3 trades). That follows from the pre-registered swing-sized design; it also limits power.
- **One-position and fill rules matter little** (B2: 12% of signals skipped as the stock was already held; fill skips mostly 2% to 8%, C4 aside). Controls were always available (none missing).

## 4. What the protocol says to do

Outcome row 1 of [protocol §6](daily-screening-protocol.md#6-what-each-outcome-means) applies (nothing promoted): none of the four ideas beats random entries at these stops on 2015 to mid 2018. The remaining options: other pre-registered ideas, the intraday idea 6, or pausing. Any new test is a new pre-registration; no variant may be added to this family.

If the owner wants to look further at the one result that points the other way, F3 (failed breakdown), the honest route is a new, separate pre-registration with its own approval, stating that F3a failed this screen's gross-above-zero rule, and spending the confirmation segment once; its net result would need to improve by more than 0.18R to be positive, and the strongly negative controls suggest the edge may partly reflect how the control is matched.

## 5. Limitations

- One screen segment (2015 to mid 2018, largely rising), today's NIFTY 50 (`survivorship_bias_risk`), costs `costs_unverified`, slippage an assumption; 8 variants tried (hence the 99% interval).
- The 4% to 10% stop range excludes most signals by design; trade counts are small for P1b, F3b and C4, so intervals are wide.
- Month-matched controls inherit the market regime of the trade's month: good for fairness, but they are very positive in rising months and very negative in falling ones, which is why edge and absolute result can disagree.
- The ideas are simplified definitions; a result is not a verdict on every way of trading a pullback, a breakout, a failed breakdown or a climax.
