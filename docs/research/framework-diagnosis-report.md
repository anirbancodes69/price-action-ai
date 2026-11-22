# Framework Diagnosis Report

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Date | 2026-11-22 |
| Plan | [framework-diagnosis-plan.md](framework-diagnosis-plan.md) (pre-registered; implementation amendments §4a, written before any test ran) |
| Status | DX-0 to DX-5 and DX-7 done. **DX-6 (charges check) waits for the owner's contract notes (D-6)**. This report decides nothing: the plan's decision rules send every framework change to the owner |
| Data | In-sample only: 427 sessions, 2024-01-02..2025-09-23, today's NIFTY 50 (`survivorship_bias_risk`); the saved Strategy 01 (11,363 trades) and Strategy 02 (10,353 trades) 4a chunks. Out-of-sample and holdout untouched |
| Code | `python-engine/app/backtest/diagnostics/` and `scripts/run_diagnostics.py`, with unit tests; no detector, ruleset or replay behaviour changed |

Hypothetical, simulated results only (TRD-06 BT-06). Aggregates only; raw output stays outside the repository. Confidence intervals are 95%, bootstrap over whole sessions (10,000 resamples, seed 1). "Material" means the interval excludes zero **and** the effect is at least 0.05R (0.02% for returns), as fixed in the plan.

## 1. Result in one paragraph

The strategies lose before costs because of **friction, not because of the replay machinery and not because of the entries' timing**. Before slippage and charges, both strategies earn about zero R (-0.01R and -0.02R per trade). Random entries with the same stop distances, the same fill rule and the same exit lose just as much (DX-4). The fill rule's slippage (0.05% on every entry and on stop exits) takes about 0.16R per trade and the assumed charges about 0.16R more, on stops that are mostly 0.3% to 1.0% of price. Entry timing, exit model, drift and simulator correctness do not explain the loss. The two strategies have no measurable entry edge, but also no defect that the diagnosis could find.

## 2. Hypotheses

| ID | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | Entries carry no edge | **Supported, as "no better than random"** | DX-4: strategy minus matched controls, gross, is +0.009R for Strategy 01 (CI -0.010 to +0.027) and +0.037R for Strategy 02 (CI +0.019 to +0.056); neither reaches the 0.05R materiality line. DX-2: forward returns equal random bars in 14 of 16 comparisons; Strategy 02's 12-bar and session-exit returns are better by 0.02% (material under the 0.02% rule, about 0.03 stop distances, not material in stop units) |
| H2 | Friction is large relative to the stop | **Supported, the main cause** | DX-3: R before slippage and charges is -0.009 (S01) and -0.019 (S02); entry slippage costs 0.10 / 0.09R, stop-exit slippage 0.05 / 0.04R, charges 0.16 / 0.16R. Friction per trade falls as the stop widens (§4) |
| H3 | The exit model cuts winners | **Not supported** | DX-5 (Strategy 01 entries): target-first collision rule +0.000R; fixed 6- and 12-bar exits +0.03 and +0.02R (intervals include zero); hold to session exit +0.016R (not material). Only removing stop slippage is material, +0.054R, and that is friction again |
| H4 | Long-only intraday drift is negative | **Not supported** | DX-1: buy 09:30 open, sell 15:15 open: +0.005% per instrument-session (CI -0.060% to +0.070%, 21,250 observations); from random bars +0.014% (CI -0.026% to +0.054%) |
| H5 | The fill rule selects against the trade | **Not supported** (partly untestable) | The fill gap (fill-bar open minus the signal-bar close) averages -0.009R and -0.007R, so no adverse gap. Signals skipped by the fill rule are not in the saved chunks, so their forward returns could not be compared (plan §4a item 4) |
| H6 | The cost schedule is wrong | **Untested: waits for contract notes (DX-6)** | Charges are 0.16R per trade under `nse-intraday-assumed-0`; the figure is only as good as the schedule |
| H7 | The simulator has a defect | **Not supported in the sample** | DX-7: 20 of 20 randomly drawn Strategy 01 trades (seed 1) agree with a separate recomputation from the raw bars (entry, exit price, exit time, reason, gross P&L, gross R). 5 instrument-sessions of 21,250 had fewer than 75 bars. The check does not cover signal generation |

## 3. DX-4 and DX-2: strategies against random entries

Common exit for both sides: stop at the trade's own stop distance, target 2.5R, same fill rule, slippage, session exit, collision rule and charges; 5 controls per trade (seeds 1-5) on the same symbol and session; one position per symbol.

| | Strategy 01 | Controls | Strategy 02 | Controls |
|---|---|---|---|---|
| Trades / controls | 11,363 | 52,215 | 10,353 | 48,079 |
| Avg R gross | -0.168 | -0.177 | -0.156 | -0.193 |
| Avg R net | -0.331 | -0.332 | -0.311 | -0.341 |
| Gross difference (CI) | +0.009 (-0.010, +0.027) | | +0.037 (+0.019, +0.056) | |
| Net difference (CI) | +0.001 (-0.018, +0.020) | | +0.030 (+0.012, +0.049) | |
| Recorded 4a result (own exits) | -0.165 gross / -0.328 net | | -0.155 gross / -0.311 net | |

The strategy under the common exit matches its recorded 4a result to within 0.003R, so the common exit is a fair stand-in. Neither strategy is materially better than random entries; Strategy 02 is slightly better, by less than the 0.05R line.

## 4. DX-3: where the loss comes from (average per trade, in R)

| | Gross | Before friction | Entry slippage | Stop-exit slippage | Charges | Net | Fill gap |
|---|---|---|---|---|---|---|---|
| Strategy 01, all | -0.165 | -0.009 | 0.102 | 0.054 | 0.163 | -0.328 | -0.009 |
| Strategy 02, all | -0.155 | -0.019 | 0.092 | 0.044 | 0.156 | -0.311 | -0.007 |

`net = before friction - entry slippage - stop slippage - charges` holds for every trade (unit test).

By stop distance (descriptive; no intervals), Strategy 01 / Strategy 02:

| Stop distance | Trades | Gross R | Before friction | Entry slip | Charges | Net R |
|---|---|---|---|---|---|---|
| 0.15-0.30% | 470 / 186 | -0.19 / -0.35 | +0.09 / -0.06 | 0.18 / 0.18 | 0.23 / 0.22 | -0.42 / -0.57 |
| 0.30-0.50% | 5,227 / 3,722 | -0.22 / -0.23 | -0.02 / -0.04 | 0.13 / 0.12 | 0.18 / 0.18 | -0.40 / -0.41 |
| 0.50-1.00% | 4,868 / 5,568 | -0.13 / -0.12 | -0.02 / -0.01 | 0.08 / 0.08 | 0.15 / 0.15 | -0.28 / -0.27 |
| 1.00-2.00% | 793 / 873 | +0.02 / -0.02 | +0.07 / +0.04 | 0.04 / 0.04 | 0.09 / 0.09 | -0.07 / -0.10 |

Friction in R is roughly inversely proportional to the stop distance. 0.30% to 0.50% stops hold 46% (Strategy 01) and 36% (Strategy 02) of trades and lose about 0.40R net; only 1% to 2% stops come close to break-even, and their before-friction R (+0.07 and +0.04) is a small average over 793 and 873 trades with no interval.

## 5. DX-1, DX-5, DX-7

- **DX-1 drift:** about zero. Monthly means swing from -0.23% to +0.25% with no sustained sign; no headwind in the period.
- **DX-5 exit bounds (Strategy 01 entries, common exit baseline -0.168R gross):** target-first collision 0.000R; no stop slippage +0.054R (material); hold 6 bars +0.032R, hold 12 bars +0.024R, hold to the session exit +0.016R (none material). No exit variant turns the result positive.
- **DX-7:** 20/20 trades agree; the target is not stored, so `TARGET` exits are checked for plausibility only (plan §4a).

## 6. Limitations

- In-sample only and today's NIFTY 50 (`survivorship_bias_risk`). The result describes these two strategies and this fill and cost model, not every possible strategy.
- The target is not stored in the saved trades, so DX-2, DX-4 and DX-5 use a common 2.5R target (plan §4a). Controls take the matched trade's stop distance in % of the fill price and do not round to the tick.
- 4,600 of 56,815 Strategy 01 controls and 3,686 of 51,765 Strategy 02 controls could not be filled within 20 redraws (the fill rule rejected them, mostly the narrow stops); they are absent from the control averages.
- Skipped signals are not recoverable (H5 partly untested). DX-1 is not split by 15m context. DX-3 buckets have no intervals.
- Slippage (0.05%) and charges are unverified assumptions (D-6, audit R-2). The size of the main finding depends on them: the friction items (both slippages and charges) are 0.32R (Strategy 01) and 0.29R (Strategy 02) per trade under these numbers.

## 7. What the plan's rules say, and what is for the owner

Decision-rule row 1 applies: controls lose about as much as the strategies (difference not material), so the loss comes from the shared machinery and not from the entries. DX-3 names the shared part: slippage and charges relative to the stop distance. No defect was found (DX-7). The drift is not a headwind (DX-1). The exit model is not the cause (DX-5).

Options for the owner, none started, each a framework change needing its own approval and validation on data this plan did not use:

1. **Check the friction assumptions** (DX-6, D-6): the 0.05% slippage and the charge schedule drive about 0.3R of the loss. Contract notes and, if possible, a measured slippage on liquid NIFTY 50 names would say how much of it is real.
2. **Re-specify where trades are taken**: friction in R falls as the stop widens; the minimum stop distance (`risk.min_stop_distance_pct`) and setups with structural stops of 1% or more are the lever. This changes what a strategy must prove (a gross edge above about 0.3R per trade at today's stops).
3. **Entry research**: neither strategy has a measurable timing edge, so strategy work resumes only with a hypothesis about why price moves after its trigger (the plan's row 2 and 3 do not apply here, because the strategies are not worse than random).
4. **Scope**: a longer holding period (daily or swing) divides the same friction over larger moves; that would need a new ADR (ADR-014 sets intraday).

DX-4 must be re-run after any framework change, before strategy work resumes (plan §5).
