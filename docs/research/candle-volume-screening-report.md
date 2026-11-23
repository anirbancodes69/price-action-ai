# Candle and Volume Screening Report (Daily)

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Date | 2026-11-23 |
| Protocol | [candle-volume-screening-protocol.md](candle-volume-screening-protocol.md) (family N = 12, fixed; clarifications in §10.1) · [ADR-020](../adr/ADR-020-VOLUME-AND-CANDLE-FACTORS-IN-RESEARCH.md) |
| Status | Screen, volume audit and exit study done. **No variant was promoted, so the confirmation step did not run, as the protocol says.** Out-of-sample and holdout prices were never loaded |
| Data | Data version 2026-11-23, today's NIFTY 50 (50 stocks), Gate 0 exclusions and series cuts. Screen segment 2015-01-01..2018-07-24 (881 sessions); the confirmation segment was not read for any entry |
| Code | `app/backtest/diagnostics/daily_candle.py` (patterns, volume filter, volume audit), `daily.py` (candle exit, `volume` on `DayBar`), `scripts/run_candle_screen.py`, with 11 new tests; no detector, ruleset or replay behaviour changed |

Hypothetical, simulated results only (TRD-06 BT-06). Aggregates only; raw output stays outside the repository. Edge = the strategy's average R minus its month-matched random-entry controls' (5 per trade), planned-risk basis, month-block bootstrap (10,000 resamples, seed 1); stop = the 5-session low, 4% to 10% below the close, 20-session time stop, no target, 0.05% slippage each side, Groww delivery charges.

## 1. Result in one paragraph

Hammer, bullish engulfing and doji-then-green candles, **bought anywhere without a volume filter, do worse than random entries** (H-A -0.17R, E-A -0.18R, D-A -0.14R; the engulfing and doji intervals are below zero). **Adding the volume filter does not help**: E-AV (-0.30R) and D-AV (-0.28R) are worse than E-A and D-A (H-AV is +0.12R on only 15 trades). The only positive edges appear when the pattern forms **at a 20-session low** (H-S +0.25R, E-S +0.22R, D-S +0.36R, D-SV +0.61R), but those variants have only 5 to 42 trades, far below the 100 needed, and every interval includes zero; D-S has the best figures (gross +0.23R, net +0.10R over 42 trades). Nothing was promoted. A candle exit instead of the time stop made no consistent difference.

## 2. Screen results

| Variant | Setting | Trades | Gross R: strategy / control | Gross edge [99% interval] | Net R: strategy / control |
|---|---|---|---|---|---|
| H-A | Hammer, anywhere | 120 | -0.039 / +0.135 | -0.174 [-0.415, +0.082] | -0.176 / -0.003 |
| H-AV | Hammer, anywhere + volume | 15 | -0.333 / -0.450 | +0.117 [-0.343, +0.761] | -0.469 / -0.588 |
| H-S | Hammer, at the 20-session low | 13 | -0.255 / -0.505 | +0.251 [-0.365, +1.184] | -0.386 / -0.637 |
| H-SV | Hammer, at the 20-session low + volume | 5 | -0.301 / -0.630 | +0.329 [-0.208, +1.535] | -0.444 / -0.772 |
| E-A | Bullish engulfing, anywhere | 381 | -0.074 / +0.103 | -0.178 [-0.313, -0.034] | -0.211 / -0.033 |
| E-AV | Bullish engulfing, anywhere + volume | 97 | -0.100 / +0.204 | -0.304 [-0.538, -0.057] | -0.231 / +0.072 |
| E-S | Bullish engulfing, at the 20-session low | 36 | -0.011 / -0.227 | +0.215 [-0.159, +0.693] | -0.152 / -0.367 |
| E-SV | Bullish engulfing, at the 20-session low + volume | 15 | -0.588 / -0.386 | -0.202 [-0.645, +0.196] | -0.727 / -0.526 |
| D-A | Doji then green, anywhere | 372 | -0.002 / +0.137 | -0.139 [-0.277, -0.003] | -0.136 / +0.004 |
| D-AV | Doji then green, anywhere + volume | 97 | +0.053 / +0.336 | -0.283 [-0.533, -0.004] | -0.077 / +0.206 |
| D-S | Doji then green, at the 20-session low | 42 | +0.235 / -0.128 | +0.362 [-0.170, +0.781] | +0.095 / -0.268 |
| D-SV | Doji then green, at the 20-session low + volume | 9 | +0.985 / +0.371 | +0.614 [-0.084, +1.183] | +0.846 / +0.232 |

Promotion needs at least 100 trades, average gross R above 0, an edge of at least +0.05R and a 99% interval above zero ([protocol §6](candle-volume-screening-protocol.md#6-control-statistics-and-promotion-fixed-now)). Net R is shown for strategy and control.

How many signals reached a trade:

| Variant | Signals | Stop outside 4% to 10% | One-position skip | Fill skipped | Trades |
|---|---|---|---|---|---|
| H-A | 514 | 375 | 9 | 10 | 120 |
| H-AV | 56 | 39 | 0 | 2 | 15 |
| H-S | 114 | 95 | 0 | 6 | 13 |
| H-SV | 28 | 21 | 0 | 2 | 5 |
| E-A | 1348 | 836 | 80 | 51 | 381 |
| E-AV | 208 | 88 | 2 | 21 | 97 |
| E-S | 197 | 148 | 0 | 13 | 36 |
| E-SV | 43 | 23 | 0 | 5 | 15 |
| D-A | 1033 | 544 | 68 | 49 | 372 |
| D-AV | 189 | 67 | 7 | 18 | 97 |
| D-S | 168 | 114 | 0 | 12 | 42 |
| D-SV | 24 | 11 | 0 | 4 | 9 |

## 3. DV-0: volume audit

- **Adjustment:** inconclusive. HDFC Bank's 2019-09-19 2:1 split shows median volume 2.33 times higher over the next 20 sessions (consistent with unadjusted volume, though that stock's control date showed 1.94), and Reliance's 2017-09-07 1:1 bonus shows 1.05 (consistent with adjusted volume). So volume is **not known to be adjusted** for corporate actions.
- **Handling (protocol §10.1):** the volume variants ran with a conservative exclusion. 48 of 50 stocks show at least one split-like volume level shift (most are probably genuine volume changes, which a crude detector cannot separate from unadjusted splits); 6,321 of 81,680 sessions (7.7%) were treated as non-comparable and gave no volume-filter signal; 3 sessions had zero volume.

## 4. Exit study (descriptive; no pass or fail)

Same entries, candle exit (bearish engulfing or a close below the previous low) against the 20-session time stop, variants with at least 100 paired trades:

| Variant | Trades | Gross R: time stop → candle exit | Difference [95% interval] | Net R: time stop → candle exit |
|---|---|---|---|---|
| E-A | 381 | -0.074 → -0.096 | -0.021 [-0.136, +0.097] | -0.211 → -0.232 |
| D-A | 372 | -0.002 → -0.089 | -0.087 [-0.243, +0.056] | -0.136 → -0.223 |
| H-A | 120 | -0.039 → +0.072 | +0.112 [-0.157, +0.349] | -0.176 → -0.064 |

The differences are small and their intervals include zero, with no consistent sign: the candle exit helped the hammer (+0.11R), and did not help the engulfing or doji entries.

## 5. Readings

- **Anywhere is worse than random.** Candle patterns without a context are weak entries, consistent with all earlier price-only results; the month-matched controls are positive in rising months, so the strategies earn about 0R while random entries earn +0.10R to +0.34R.
- **Volume adds nothing here.** The volume-filtered variants have fewer trades and the same or worse edges.
- **The "at support" context is where any signal is, and it is under-powered.** It matches the failed-breakdown result of the price-only screen (an edge over a falling-month control that did not become a positive absolute result). To judge it, a test needs far more signals: a **wider universe** (for example NIFTY 200) or a longer window, not a looser rule.
- **Do not read the small-sample positives.** D-S and D-SV have the best figures on 42 and 9 trades; with 12 variants tried, such a result is easy to find by chance.

## 6. What the protocol says to do

Outcome row 1 of [protocol §8](candle-volume-screening-protocol.md#8-what-each-outcome-means) applies (nothing promoted). A new test is a new pre-registration; no variant may be added to this family. The natural next test, if the owner wants one, is the same support-context patterns on a wider universe so that they reach 100 trades; it needs a backfill of more instruments.

## 7. Limitations

- One screen segment (2015 to mid 2018, largely rising), today's NIFTY 50 (`survivorship_bias_risk`), costs `costs_unverified`, slippage an assumption; 12 variants tried (hence the 99% interval).
- The 4% to 10% stop range and the support context leave few trades; intervals are wide.
- Volume adjustment for corporate actions is unverified; the exclusion is conservative and crude.
- Single fixed pattern definitions (60%, 30%, 10%, 1.5 times); other definitions could differ.
