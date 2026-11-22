# Fast Screening Report

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Date | 2026-11-23 |
| Protocol | [fast-screening-protocol.md](fast-screening-protocol.md) (approved by the owner 2026-11-23; family N = 13, fixed) |
| Status | Tier 0 and Tier 1 screen done. **No variant was promoted, so Tier 2 (confirmation) did not run, as the protocol says.** Out-of-sample and holdout were never read |
| Data | Screen year 2024-01-02..2024-12-31 (245 sessions): Tier 0 on the saved Strategy 01 and 02 trades of all 50 stocks, Tier 1 on the 10 screen stocks (AXISBANK, BHARTIARTL, ETERNAL, HINDALCO, ITC, M&M, ONGC, SHRIRAMFIN, TECHM, WIPRO) |
| Code | `python-engine/app/backtest/diagnostics/screen.py`, `sim.py` (`fill_and_run`), `scripts/run_screen.py`, with 14 new tests; no detector, ruleset or replay behaviour changed |

Hypothetical, simulated results only (TRD-06 BT-06). Aggregates only; raw output stays outside the repository. Edge = strategy minus the matched random-entry control (5 seeds per trade), in R, common exit (target 2.5R, session exit 15:15), 0.05% slippage, `nse-intraday-assumed-0` charges (the Groww schedule is shown for the strategy).

## 1. Result in one paragraph

None of the 13 possibilities has an entry edge over random entries at the pre-registered bar. Stop-distance filters on the parked strategies raise gross R to about zero (-0.02 to +0.02) and the gross edge over the control to +0.015 to +0.053R, but every 99% interval includes zero and net stays negative (-0.07 to -0.13R). The simplest breakout entries (M1 opening-range breakout, M2 previous-day-high break) do **worse than random entries** with the same stop distances in all six variants, by 0.10 to 0.15R with the 99% interval below zero. M3 (failed opening-range breakdown) shows no difference except at the wide-stop filters, where there are only 100 and 39 trades. Nothing was promoted.

## 2. Screen results (2024)

| Variant | Trades | Gross: strategy / control | Gross edge [99% interval] | Net: strategy / control | Net, Groww schedule (strategy) |
|---|---|---|---|---|---|
| T0-S01@>=0.75% | 1,188 | -0.006 / -0.046 | +0.040 [-0.040, +0.117] | -0.115 / -0.150 | -0.139 |
| T0-S01@>=1.00% | 509 | +0.019 / +0.004 | +0.015 [-0.099, +0.130] | -0.066 / -0.078 | -0.106 |
| T0-S02@>=0.75% | 1,464 | -0.022 / -0.075 | +0.053 [-0.010, +0.114] | -0.131 / -0.179 | -0.155 |
| T0-S02@>=1.00% | 578 | -0.007 / -0.040 | +0.032 [-0.070, +0.135] | -0.094 / -0.122 | -0.133 |
| M1@none | 1,021 | -0.047 / +0.103 | -0.150 [-0.201, -0.100] | -0.137 / +0.017 | -0.173 |
| M1@>=0.75% | 935 | -0.021 / +0.115 | -0.136 [-0.188, -0.085] | -0.105 / +0.034 | -0.145 |
| M1@>=1.00% | 714 | +0.001 / +0.128 | -0.128 [-0.186, -0.070] | -0.075 / +0.055 | -0.120 |
| M2@none | 443 | -0.056 / +0.061 | -0.117 [-0.191, -0.042] | -0.143 / -0.023 | -0.181 |
| M2@>=0.75% | 405 | -0.070 / +0.050 | -0.120 [-0.193, -0.052] | -0.151 / -0.028 | -0.193 |
| M2@>=1.00% | 329 | -0.029 / +0.074 | -0.103 [-0.172, -0.035] | -0.103 / +0.003 | -0.150 |
| M3@none | 569 | -0.239 / -0.260 | +0.021 [-0.123, +0.166] | -0.396 / -0.410 | -0.401 |
| M3@>=0.75% | 100 | +0.067 / -0.015 | +0.082 [-0.190, +0.358] | -0.039 / -0.116 | -0.064 |
| M3@>=1.00% | 39 | +0.189 / +0.013 | +0.176 [-0.163, +0.599] | +0.104 / -0.068 | +0.065 |

Promotion needs at least 100 trades, average gross R above 0, an edge of at least +0.05R and a 99% interval above zero ([protocol §5](fast-screening-protocol.md#5-statistics-and-the-promotion-rule-fixed-now)). The nearest was T0-S02@>=0.75% (edge +0.053R, interval -0.010 to +0.114, gross average -0.022R, so also failing the gross-above-zero condition). M3@>=1.00% has the best net (+0.104R) on only 39 trades.

## 3. Readings

- **Stop filters help friction, not the edge.** Both strategies' gross R moves from about -0.15 (all trades) to about zero at stops of 0.75% to 1.0% or more, as the diagnosis predicted, and their edge over the control is positive but small and not distinguishable from zero. Net remains negative (-0.07 to -0.13R).
- **Buying the breakout close underperforms random entry.** M1 and M2 lose to matched random entries in all three stop filters (-0.10 to -0.15R gross, 99% intervals below zero), on the same stocks and days. The random controls on these 10 stocks are positive in 2024 (+0.05 to +0.13R gross, wide stops and a rising period), so the strategies are worse than a positive baseline, not just near zero. This is a finding about entering at the close of a breakout bar with a structural stop and a 2.5R target; it is one year and ten stocks, and not tested on other days.
- **M3 is inconclusive where it looks best.** With no stop filter it equals its control (edge +0.021R, 569 trades, gross -0.24R: stops below 0.75% dominate). With wide-stop filters it has +0.07R and +0.19R gross but only 100 and 39 trades and intervals spanning zero.
- **Controls are not obviously biased:** control draws that could not be filled within 20 redraws: 5 of 2,845 for M3@none and up to 184 of 7,320 for T0-S02@>=0.75% (the fill rule rejects some narrow-stop controls); none for M1 and M2.

## 4. What the protocol says to do

Outcome row 1 of [protocol §6](fast-screening-protocol.md#6-what-each-outcome-means) applies (nothing promoted): none of the simplest long intraday entries, at any of these stop filters, beats random entries at this friction. The options left are those of the [diagnosis report](framework-diagnosis-report.md#8-what-the-plans-rules-say-and-what-is-for-the-owner): a longer holding period (new ADR), measuring real slippage, or pausing the strategies. A new idea is a new pre-registration; no variant may be added to this family.

## 5. Limitations

- One year, ten stocks for Tier 1; today's NIFTY 50 (`survivorship_bias_risk`); charges match Groww's published schedule today but 2024 rates and the 0.05% slippage are unverified.
- The 2024 year was seen in aggregate before (protocol §3), and the 10 screen stocks rose strongly in 2024, which lifts all long controls.
- Minimal entries are simplifications, so M1 and M2 are not a verdict on the full Strategy 09 and 10 specifications.
- 13 variants were tried; the 99% level was chosen for that reason. With intervals this wide a real small edge on a few trades could be missed.
