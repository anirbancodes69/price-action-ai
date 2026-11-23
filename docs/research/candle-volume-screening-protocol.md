# Candle and Volume Screening Protocol (Daily)

| Field | Value |
|---|---|
| Version | 1.0 |
| Status | **Approved by the owner's instruction to run it, 2026-11-23**, together with the acceptance of [ADR-020](../adr/ADR-020-VOLUME-AND-CANDLE-FACTORS-IN-RESEARCH.md) that the volume variants need. Binding: a change is a new, separately logged pre-registration. Implementation clarifications are in §10.1 (written before the run) |
| Task | T-I148 |
| Authority | [ADR-019](../adr/ADR-019-DAILY-TIMEFRAME-RESEARCH-TRACK.md) (accepted); ADR-020 (proposed) |
| Related | [Daily screening protocol](daily-screening-protocol.md) and [report](daily-screening-report.md) (conventions) · [Gate 0 report](gate0-daily-diagnosis-report.md) · [Validation criteria](validation-criteria.md) · [Experiment registry §8](experiment-registry.md#8-candle-and-volume-screening-experiments) |

Hypothetical, simulated results only (TRD-06 BT-06). Aggregates only in the repository; raw output stays outside it.

## 1. Purpose

The owner asked on 2026-11-23 to test candle type (colour, hammer, doji, engulfing) and volume as entry and exit factors. This protocol tests them on **daily bars** (the lower-friction scope, [ADR-019](../adr/ADR-019-DAILY-TIMEFRAME-RESEARCH-TRACK.md)) with exact, fixed definitions, against matched random-entry controls, on in-sample days only. A pattern that passes is a hypothesis with evidence, not a validated strategy. Candle patterns have a weak published record after costs, so the plan expects most variants to fail; the point is a fair, reproducible test.

## 2. Data and segments (fixed now)

Same as the [daily screening protocol §2](daily-screening-protocol.md#2-data-and-segments-fixed-now): data version 2026-11-23, today's NIFTY 50, the Gate 0 exclusions and series cuts, in-sample only (2015-01-01..2022-02-15), **screen** 2015-01-01..2018-07-24 (881 sessions), **confirmation** 2018-07-25..2022-02-15 (880 sessions, run only for promoted variants). Out-of-sample and holdout prices are not loaded. Volume is read from the stored daily bars.

**Prior exposure:** the price-only daily screen already covered the screen segment (no variant passed), and Gate 0 baselines covered the whole in-sample segment. No candle-pattern or volume rule has been tested on any of it.

**Volume audit (DV-0), run first and reported:** the provider adjusts prices for splits and bonuses but volume may not be adjusted, which would make a relative-volume filter fire on split days. DV-0 lists every session whose volume is at least 4 times or at most a quarter of the mean of the previous 20 sessions, and every one whose ratio is near 1/2, 1/3, 1/4, 1/5 or 1/10 or 2, 3, 4, 5 or 10. Each is explained from public records or flagged; a stock-session whose volume is not comparable (for example a split day and the next 20 sessions) is excluded from the volume filter and counted. If unadjusted volume is widespread, the volume variants are not run and the report says so.

## 3. Common conventions (fixed now, from the daily screening protocol §3)

Signal at the close of session *s*, fill at the open of *s*+1 plus 0.05% adverse slippage (skipped when the open is at or below the stop or more than 1% above the signal close); risk unit ₹500, quantity planned from the signal close and never increased at the fill, position cap ₹50,000, one open position per stock; Groww delivery charges; R against the planned risk; 20-session time stop; stop gaps exit at the open. **Stop for every variant: the lowest low of the signal session and the previous 4 sessions, `× (1 − 0.05%)`, rounded down to the tick; a signal whose stop is not 4% to 10% below the signal close is not traded and is counted.** (Daily candle ranges are usually 1% to 3%, so a stop at the pattern's own low would almost never be wide enough; the 5-session low is the fixed choice.)

## 4. Definitions (fixed now; `range = high − low`, only sessions with `range > 0`)

| Term | Definition |
|---|---|
| Green, red | green: close above open; red: close below open |
| Body, wicks | body `= |close − open|`; lower wick `= min(open, close) − low`; upper wick `= high − max(open, close)` |
| **Hammer (H)** | lower wick at least 60% of the range, body at most 30% of the range, upper wick at most 10% of the range (any colour). Signal session = the hammer |
| **Bullish engulfing (E)** | the previous session is red, the signal session is green, `open ≤ previous close` and `close ≥ previous open` (its body covers the previous body), previous body above zero |
| **Doji then green (D)** | the previous session is a doji (body at most 10% of its range) and the signal session is green with a close above the doji's high |
| **Context S (at support)** | the signal session's low is at or below `1.01 ×` the lowest low of the previous 20 sessions (it touches or undercuts the 20-session low; for D the doji's low is tested) |
| **Volume filter V** | the signal session's volume is at least **1.5 times** the mean volume of the previous 20 sessions (mean above zero) |

## 5. The family of possibilities (fixed now; N = 12)

No variant is added, removed or re-tuned after any result. A new idea is a new pre-registration.

Each variant is a pattern (H, E or D) × a context (**A** anywhere, **S** at support) × a volume setting (none, or **V**):

`H-A, H-AV, H-S, H-SV, E-A, E-AV, E-S, E-SV, D-A, D-AV, D-S, D-SV`

The "anywhere" variants show whether the context carries the result; the V variants show whether volume does. The volume variants run only if the owner has accepted ADR-020 and DV-0 passes.

## 6. Control, statistics and promotion (fixed now)

Exactly as the [daily screening protocol §5](daily-screening-protocol.md#5-the-control-and-statistics-fixed-now): 5 month-matched random-entry controls per trade at the same planned stop distance, month-block bootstrap (10,000 resamples, seed 1), edge on the planned-risk basis. **Promotion** needs at least 100 trades, average gross R above 0, an edge of at least +0.05R and a 99% interval above zero (N = 12). **Confirmation** (promoted variants only, frozen as written, confirmation segment) needs at least 100 trades, an edge of at least +0.05R with a 95% interval above zero and the same sign in each half; slippage 0%, 0.05%, 0.10% reported. Out-of-sample is not authorised by this protocol.

## 7. Exit study (descriptive, not a pass or fail)

For every variant with at least 100 screen trades, the **same entries** are re-simulated with a **candle exit**: the stop above and the 20-session time stop stay, and the trade also exits at the close (adverse slippage 0.05%) of the first session after the fill session that is either a bearish engulfing (red, `open ≥ previous close`, `close ≤ previous open`, previous session green) or closes below the previous session's low. The report shows the paired difference in average R (candle exit minus time stop) with a month-block interval. **No promotion or ranking depends on it**: it tells the owner whether a candle exit looks worth a pre-registered test on a promoted entry.

## 8. What each outcome means

| Outcome | Reading | Next step (owner decides) |
|---|---|---|
| Nothing promoted | Hammer, engulfing and doji, with or without support and volume, do not beat random entries at these stops on 2015 to mid 2018 | Other pre-registered ideas, momentum and a wider universe, or pausing |
| Promoted but not confirmed | Screen false positives; with 12 variants a few are expected by chance | Recorded; no further work on them |
| Confirmed | A pattern rule with a small, repeatable edge over random on in-sample days | The owner decides on the out-of-sample test and the strategy process; no live use |

## 9. Implementation (after approval and, for volume, ADR-020 acceptance)

- `DayBar` gains a `volume` field (default 0, so existing code and tests are unchanged); the daily loader reads it; a volume audit (DV-0).
- Candle and volume feature functions and the three pattern detectors as pure functions of closed daily bars (no look-ahead, one signal per session), with unit tests for each definition and boundary; an optional candle exit in the daily simulator, with tests.
- Runner `scripts/run_candle_screen.py`: DV-0, screen, promote, confirm, exit study. Raw output outside the repository; one registry row per variant ([§8](experiment-registry.md#8-candle-and-volume-screening-experiments)); a report with aggregates only. No detector, ruleset or replay behaviour changes; the engine suite stays green.

## 10. Results

Run 2026-11-23: no variant promoted; confirmation did not run. See the [report](candle-volume-screening-report.md).

## 10.1 Implementation clarifications (written before the run, no variant changed)

1. **Volume audit (DV-0) rule.** The protocol said the volume variants are not run if unadjusted volume is widespread. A spot check before the run was mixed: median volume 20 sessions after against 20 before was 2.33 for HDFC Bank's 2019-09-19 2:1 split (consistent with unadjusted volume, though that stock's control date also showed 1.94) and 1.05 for Reliance's 2017-09-07 1:1 bonus (consistent with adjusted volume). Volume adjustment cannot be established, and a crude detector would flag nearly every stock, so the variants **always run**, with a conservative exclusion: a session is non-comparable (no volume-filter signal) when it lies from a split-like volume level shift to 20 sessions after it. A level shift is a change of at least 1.8 times (or at most 1/1.8) between the medians of the 20 sessions after and before; it is split-like when that ratio is within 8% of 2, 3, 4, 5, 10 or their inverses. This over-excludes genuine volume shifts; the share of excluded sessions and the shifts are reported.
2. **Pattern sessions.** The signal session and the stop (5-session low) are as in §3 and §4; for the doji pattern the context S and the pattern are evaluated on the doji session (the previous session), and the volume filter on the signal session.
3. **Exit study.** Uses the same fill and entries; the candle exit needs at least one session after the fill session, so the earliest exit is the second held session. Variants with fewer than 100 paired trades are not shown.
4. **Reuse.** Trade filtering, fills, one-position rule, controls, promotion and confirmation reuse the daily screening runner unchanged (`trades_from_signals`), verified to give identical output for the price-only screen after the refactor.

## 11. Limits

- Survivorship (today's NIFTY 50 over 2015 to 2022), costs unverified, slippage an assumption, a largely rising screen period, 12 variants tried (hence the 99% interval).
- The 4% to 10% stop range excludes most daily candle signals by design (as in the price-only screen), so trade counts may be small and intervals wide.
- Daily volume is exchange-reported, may include block or special trades, and its adjustment for corporate actions is unverified until DV-0.
- Pattern thresholds (60%, 30%, 10%, 1.5 times) are single fixed choices, not optimised; other definitions of a hammer or a doji could give different results.
