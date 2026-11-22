# Daily Screening Protocol (Ideas 1 to 4)

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Status | **Draft pre-registration, 2026-11-23. Not approved. Nothing has run.** It becomes binding when the owner approves it; after that a change is a new, separately logged pre-registration |
| Task | T-I147 |
| Authority | [ADR-019](../adr/ADR-019-DAILY-TIMEFRAME-RESEARCH-TRACK.md) (accepted); Gate 0 is done ([report](gate0-daily-diagnosis-report.md)) |
| Related | [Gate 0 plan](gate0-daily-diagnosis-plan.md) (conventions) · [Fast screening protocol](fast-screening-protocol.md) (the model for this one) · [Validation criteria](validation-criteria.md) · [Experiment registry §7](experiment-registry.md#7-daily-screening-experiments) |

Hypothetical, simulated results only (TRD-06 BT-06). Aggregates only in the repository; raw output stays outside it.

## 1. Purpose

Test four long-only, price-only daily entry ideas, chosen by the owner on 2026-11-23, against matched random-entry controls, on in-sample days only, before any further work. A variant that passes is a hypothesis with evidence, not a validated strategy: it still goes through [ADR-018](../adr/ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md) and the [validation criteria](validation-criteria.md). Gate 0 showed that random long entries with wide stops earn about zero net, so an idea must show its own edge: about +0.09R to +0.13R over its control to clear the validation bar (net above 0.10R).

## 2. Data and segments (fixed now)

- **Data version 2026-11-23** (one backfill run), today's NIFTY 50, the Gate 0 exclusions (four special sessions, one bad bar) and series cuts at the three unadjusted corporate actions (no signal, stop or holding window crosses a cut). `survivorship_bias_risk` and `costs_unverified` stay set.
- **In-sample only:** 1,761 sessions, 2015-01-01..2022-02-15. Out-of-sample and holdout prices are not loaded (the same guard as Gate 0).
- **Screen segment:** the first 881 sessions, 2015-01-01..2018-07-24. **Confirmation segment:** the last 880, 2018-07-25..2022-02-15. Both use all 50 stocks that have data in the segment (daily runs are fast, so the 10-stock subset of the intraday screen is not needed).
- **Prior exposure, stated plainly:** Gate 0 baselines (drift by year, random-entry grids) covered the whole in-sample segment, so the market's overall shape in both segments has been seen. No entry rule has been tested on any of this data.

## 3. Common conventions (fixed now, from the Gate 0 plan §4)

| Item | Rule |
|---|---|
| Signal and fill | Signal at the close of session *s*, fill at the open of *s*+1 plus 0.05% adverse slippage. Skipped when the open is at or below the stop or more than 1% above the signal close |
| Exit | Stop, or the time stop at the close of the 20th session from the fill session (adverse slippage 0.05%). **No target.** Gap through the stop exits at the open (adverse slippage). A stop and any other exit in one session: the stop |
| Stop distance | Every variant's structural stop must lie **4% to 10%** of the signal close; a signal outside that range is not traded and is counted. (4% is where friction falls to 0.19R; 10% caps absurd stops.) |
| Sizing and costs | Risk unit ₹500, quantity planned from the signal close and never increased at the fill, position cap ₹50,000, one open position per symbol (a signal while that stock's trade is open is skipped); Groww delivery charges as in Gate 0 |
| R basis | **R against the planned risk** (`qty × (signal close − stop)`) is primary (the owner is asked to approve this basis, Gate 0 report §7). R against the risk at the fill is reported beside it |
| Buffers | 0.05% below the stop level, as in the ruleset (`risk.stop_buffer_pct`), rounded down to the 0.05 tick |
| Pivots | Daily swing pivots use 2 sessions on each side (the ruleset's pivot parameters); a pivot is usable only from its confirmation session |

## 4. The family of possibilities (fixed now; N = 8)

No variant is added, removed or re-tuned after any result. A new idea is a new pre-registration.

| ID | Idea | Rule | Stop |
|---|---|---|---|
| P1a, P1b | **1. Trend pullback** | Uptrend by structure: the last two confirmed swing highs rise and the last two confirmed swing lows rise, the latest swing low precedes the latest swing high (price is pulling back from it), and the pullback low (lowest low since that swing high) is above the latest swing low (structure intact). The pullback depth from the swing high is at least **3% (P1a)** or **6% (P1b)**. Signal: the first session after the pullback low with a close above the previous session's high. One signal per swing high | The pullback low |
| B2a, B2b | **2. Breakout of a long range** | The first session whose close is above the highest high of the previous **50 (B2a)** or **100 (B2b)** sessions (the previous session's close was not above the highest high of its own previous N sessions) | The lowest low of the last 20 sessions, including the signal session |
| F3a, F3b | **3. Failed breakdown at support** | Level Y is the lowest low of the previous **20 (F3a)** or **50 (F3b)** sessions, known before the breakdown. Breakdown: the first session *b* with a close below `Y × (1 − 0.05%)`. Reclaim: the first session within 3 sessions after *b* with a close at or above Y; the signal is that session. Only the first breakdown is considered | The lowest low from *b* to the reclaim session |
| C4a, C4b | **4. Selling-climax reversal** | A session whose close is at least **4% (C4a)** or **6% (C4b)** below the previous close and in the top third of its own range (`(close − low) ≥ (2/3)(high − low)`, high above low) | The low of that session |

All four read only closed daily bars up to and including the signal session. No indicator is used.

## 5. The control and statistics (fixed now)

- **Control:** for each trade, 5 controls (seeds 1 to 5) on the same stock: a uniformly random signal session in the **same calendar month** as the trade's signal session (a month-matched control keeps the market regime), stop below the signal close at the **same percentage distance** as the matched trade, the same fill rule, exit, slippage and charges, the whole holding window inside the segment; a skipped fill is redrawn up to 20 times and the redraws reported. Controls are independent of each other (no one-position rule among them), as in Gate 0.
- **Edge** = the strategy's average R minus its controls' average R, in R (planned-risk basis, gross and net), with a month-block bootstrap interval (10,000 resamples, seed 1). Reported for every variant, including failures: trades, signals, stop-filtered count, fill-skipped count, average R gross and net (both bases), controls and redraws.
- **Promotion from the screen** needs all of: at least 100 trades; average gross R above 0; gross edge of at least **+0.05R**; the **99%** interval of the edge excludes zero (stricter than 95% because 8 variants are tried; the family size is recorded with every result).
- **Confirmation** (the variant frozen as written, run on the confirmation segment) needs all of: at least 100 trades; gross edge of at least +0.05R with a 95% interval excluding zero; the same (positive) sign in each half of the segment (about 440 sessions each). Average net R is reported with the slippage sensitivity 0%, 0.05% and 0.10%. A variant that fails is recorded as a screen false positive, with the count.
- **Out-of-sample** is not authorised by this protocol. A variant that confirms goes to the owner, who decides whether to freeze it and spend the out-of-sample segment (touched once, never tuned against) and whether it becomes a strategy-library entry under ADR-018. A positive edge is not profit: the validation bar is net above 0.10R after costs on out-of-sample data.

## 6. What each outcome means

| Outcome | Reading | Next step (owner decides) |
|---|---|---|
| Nothing promoted | None of the four ideas beats random entries at these stops on 2015 to 2018 | The remaining options: other pre-registered ideas, the intraday idea 6, or pause |
| Promoted but not confirmed | Screen false positives; with 8 variants a few are expected by chance | Recorded; no further work on them |
| Confirmed | An entry rule with a small, repeatable edge over random on in-sample days | The owner decides on the out-of-sample test and the strategy process; no live use |

## 7. Implementation (after approval)

- Detectors as pure functions of daily bars (closed bars only, no look-ahead, one signal per episode), with unit tests: pivots confirmed with their lag, trend and pullback conditions, first-breakout rule, breakdown and 3-session reclaim window, climax conditions, stop and range filters, series cuts, month-matched control sampling, promotion and confirmation rules. In `python-engine/app/backtest/diagnostics/`, reusing `daily.py`, `stats.py` and the delivery schedule.
- Runner `scripts/run_daily_screen.py`: screen, promote and confirm mechanically in one run; confirmation data is read only for promoted variants. Raw output outside the repository; one registry row per variant ([§7](experiment-registry.md#7-daily-screening-experiments)); a report with aggregates only. No detector, ruleset or replay behaviour changes; the engine suite stays green.

## 8. Limits

- Survivorship (today's NIFTY 50 over 2015 to 2022), costs unverified, slippage an assumption, a largely rising period, and 8 variants tried (hence the 99% interval).
- Intervals resample about 40 calendar months per segment, so they are wide: a real small edge can be missed, and a false one can pass the screen.
- Four ideas are simplified definitions; a result is not a verdict on every way of trading a pullback, a breakout, a failed breakdown or a climax.
- The 4% to 10% stop range makes this a swing-sized test: setups whose natural stop is narrower are excluded by design.
