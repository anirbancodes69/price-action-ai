# Fast Screening Protocol

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Status | **Approved by the owner, 2026-11-23** (as drafted, including running minimal entries out of roadmap order). Binding: a change is a new, separately logged pre-registration. Implementation clarifications are in §7.1 |
| Owner request | 2026-11-23: test many possibilities quickly instead of full 50-stock, 427-session replays |
| Related | [Framework diagnosis report](framework-diagnosis-report.md) · [Validation criteria](validation-criteria.md) · [Independent backtesting standards](independent-backtesting-standards.md) · [Experiment registry §5](experiment-registry.md#5-fast-screening-experiments) · [ADR-018](../adr/ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md) |

Hypothetical, simulated results only (TRD-06 BT-06). Aggregates only in the repository; raw output stays outside it.

## 1. Purpose and what this is not

The [diagnosis](framework-diagnosis-report.md) found that neither parked strategy beats matched random entries and that friction costs about 0.3R per trade, falling as the stop widens. This protocol tests **a fixed, small list of possibilities** cheaply, so the owner can see whether any has an entry edge over random entries before more strategy work. It is a screen. A variant that passes is a hypothesis with evidence, not a validated strategy: it still goes through the [strategy process](../development/strategy-development-process.md) and the [validation criteria](validation-criteria.md).

## 2. Design (why not one stock)

Replay time scales with stocks times sessions (the full 50-stock, 427-session run took about 3.7 hours). The tiers below avoid the full analysis replay for screening: they use stored bars and saved trades, as the diagnosis did (about a minute).

One stock for one year would give about 120 trades per variant per strategy-detector, a noise of about 0.1R on an average, larger than the effects that matter (0.05 to 0.1R), and one stock's behaviour may not generalise. So the screen uses **10 stocks for the 2024 year**, and a variant is confirmed on **all 50 stocks over the later in-sample days**.

| Tier | Data | Cost | Purpose |
|---|---|---|---|
| 0 | Saved Strategy 01 and 02 4a trades, all 50 stocks; screen 2024, confirm 2025 | seconds | Stop-distance filters on existing trades |
| 1 | Minimal entries (§4.2) on the 10-stock screen set, 2024 | minutes | New simple entries against random controls |
| 2 | Variants promoted from Tier 0 or 1: all 50 stocks, 2025-01-01..2025-09-23 | minutes to an hour | Confirmation on days the screen did not use |
| 3 | Out-of-sample segment, once, frozen definition | owner approval | Blind test |

## 3. Data and sets (fixed now)

- **Screen year:** the first in-sample year, 2024-01-02..2024-12-31 (245 sessions). **Confirmation:** the rest of the in-sample segment, 2025-01-01..2025-09-23 (182 sessions). The out-of-sample (2025-09-24..2026-04-24) and holdout (2026-04-27..2026-11-19) segments are not used by Tiers 0 to 2.
- **Screen stocks (performance-blind rule):** positions 5, 10, 15, ..., 50 of today's NIFTY 50 sorted alphabetically (`--members-on 2026-11-19`): AXISBANK, BHARTIARTL, ETERNAL, HINDALCO, ITC, M&M, ONGC, SHRIRAMFIN, TECHM, WIPRO. No per-stock result was looked at to choose them.
- Same exclusions, previous-day levels from 1D bars (D-7), sizing (FIXED, ₹500 risk unit, no account limits), slippage (0.05% on entries and stop exits) and flags (`survivorship_bias_risk`, `costs_unverified`) as experiment 4a.
- Costs: `nse-intraday-assumed-0` is primary (comparable with all earlier results); the `GROWW_PUBLISHED` schedule is reported beside it.

**Prior exposure, stated plainly.** The in-sample aggregates of both strategies over 2024 and 2025, and the stop-distance buckets (diagnosis DX-3), have already been seen, and the stop-distance idea came from them. So the 2024 screen is not blind to the overall shape. The confirmation segment is separated in time, but only the out-of-sample segment, untouched so far, is a blind test.

## 4. The family of possibilities (fixed now; N = 13)

No variant is added, removed or re-tuned after any result. A new idea is a new pre-registration.

### 4.1 Tier 0: stop-distance filters on the saved trades (N = 4)

| ID | Trades | Filter (stop distance as % of the fill price) |
|---|---|---|
| T0-1 | Strategy 01 | stop ≥ 0.75% |
| T0-2 | Strategy 01 | stop ≥ 1.00% |
| T0-3 | Strategy 02 | stop ≥ 0.75% |
| T0-4 | Strategy 02 | stop ≥ 1.00% |

The upper bound stays the ruleset's 2.0%. A promoted Tier 0 variant is a change to a parked strategy: it uses one of that strategy's three improvement rounds ([criteria §5](validation-criteria.md#5-improvement-rounds)) and needs the owner to reopen it, with a new ruleset version.

### 4.2 Tier 1: minimal entries (N = 9)

Three entries, each long, one signal per symbol per session, no 15m context, no score, no zones, no anchor choices. Buffer 0.05% (`bb`, `sb`) as in the ruleset; signal at the close of bar *t*, fill at the open of *t+1* by `simulate_entry` (cutoff, gap, R:R and slippage checks).

| Entry | Rule | Stop |
|---|---|---|
| M1 opening-range breakout | First 5m bar after the opening range (09:15 to 09:30) closing above `OR_HIGH × 1.0005`; range width 0.3% to 2.0% | `OR_LOW × (1 − sb)` |
| M2 previous-day-high break | Session opens below the previous day's high; first bar closing above `PDH × 1.0005` | lowest low of the session so far `× (1 − sb)` |
| M3 failed opening-range breakdown | First bar after the opening range closing below `OR_LOW × (1 − bb)`, then the first bar within 6 bars closing at or above `OR_LOW`; the signal is that reclaim bar's close | lowest low from the breakdown bar to the reclaim bar `× (1 − sb)` |

Each entry runs with three stop-distance filters: none, ≥ 0.75%, ≥ 1.00% (so 3 × 3 = 9 variants). Stops are rounded down to the tick. Exit for every variant: stop, target of 2.5R from the reference entry (the diagnosis's common target), or the session exit at 15:15; a bar touching both counts as a stop (BT-04).

### 4.3 The control

Matched random entry, as diagnosis DX-4: for each trade, 5 controls (seeds 1 to 5) on the same symbol and session, the same stop distance in %, a uniformly random 5m signal bar after the opening range and before the entry cutoff, the same fill rule, exit and charges; one position per symbol; a skipped fill is redrawn up to 20 times and the redraw count reported.

## 5. Statistics and the promotion rule (fixed now)

Session bootstrap as in the diagnosis (10,000 resamples, seed 1), applied to **strategy minus matched control**, in R. Reported for every variant, without exception: trades, average R gross and net (both schedules), the control's, the difference with its interval, and the redraw count.

**Promotion from Tier 0 or Tier 1 to Tier 2** needs all of:

1. at least 100 trades in the screen;
2. average gross R above 0;
3. gross difference to the control of at least **+0.05R**;
4. the **99%** interval of that difference excludes zero (a stricter level than 95% because 13 variants are tried; the family size is recorded with every result).

**Confirmation at Tier 2** (the variant's definition frozen as written, run on all 50 stocks, 2025-01-01..2025-09-23) needs all of: at least 100 trades; gross difference to the control of at least +0.05R with a 95% interval excluding zero; the same sign in each half of the confirmation segment (about 91 sessions each); average net R reported with the cost sensitivity of [validation criteria §1](validation-criteria.md#1-a-strategy-must-not-pass-on-one-profitable-backtest) (slippage 0%, 0.05%, 0.10%). A variant that fails is recorded as a screen false positive, with the count.

**Tier 3 (out-of-sample)** is not authorised by this protocol. A variant that confirms goes to the owner, who decides whether to freeze it and spend the out-of-sample segment (touched once, never tuned against) and whether it becomes a strategy-library entry under ADR-018.

## 6. What each outcome means

| Outcome | Reading | Next step (owner decides) |
|---|---|---|
| Nothing is promoted | None of the simplest long intraday entries, at any of the stop filters, beats random entries at this friction | The remaining options of the diagnosis report: longer holding period (new ADR), measure real slippage, or pause the strategies |
| Promoted but not confirmed | Screen false positives; with 13 variants a few are expected by chance | Recorded; no further work on them |
| Confirmed | An entry rule with a small, repeatable edge over random on in-sample days | The owner decides on the out-of-sample test and the strategy process; no live use |
| Tier 0 variant confirmed | A stop-distance filter lifts a parked strategy over its control | Owner decides whether to reopen it (one of three rounds, new ruleset version) |

A positive gross edge does not make a strategy profitable: net average R must still clear the [validation criteria](validation-criteria.md) (more than 0.10R after costs on the out-of-sample segment).

## 7. Implementation (after approval)

- Minimal entry detectors as pure functions on bars in `python-engine/app/backtest/diagnostics/`, with unit tests (signals use closed bars only; no look-ahead; one signal per session; boundaries), reusing the diagnosis helpers (`sim.py`, `stats.py`).
- Runner `scripts/run_screen.py`; raw output in the research directory outside the repository; the engine suite stays green and no detector, ruleset or replay behaviour changes.
- One registry row per variant and per tier ([registry §5](experiment-registry.md#5-fast-screening-experiments)); results in a report, aggregates only.

### 7.1 Implementation clarifications (written before the run, no variant changed)

1. Minimal-entry signals are read only on bars that start at or after 09:30 (after the opening range) for M1, M2 and M3; M2 and M3 are therefore not evaluated inside the first 15 minutes.
2. Every Tier 1 variant also obeys the ruleset's stop limits (0.15% to 2.0% of the reference entry); the filter "none" means those limits only. Stop distance for the filter is measured on the reference entry; controls are matched on the stop distance of the filled trade (as in the diagnosis).
3. Stops are rounded down to the 0.05 tick. M2 is skipped on a session with a missing or inconsistent previous-day bar (D-7).
4. Tier 0 strategy results are the saved trades re-simulated with the common exit (target 2.5R from the fill price, as diagnosis DX-4), not the recorded exits.
5. The runner screens, promotes and confirms mechanically in one run; confirmation data (2025) is read only for promoted variants.

## 8. Results

Screen done 2026-11-23: no variant promoted; Tier 2 did not run. See the [report](fast-screening-report.md).

## 9. Limits

- Survivorship bias (today's NIFTY 50), costs and slippage unverified (D-6 partly: charges match Groww's published schedule), the 2024 year was seen in aggregate (§3).
- The minimal entries are simplifications, so a result is **not** a verdict on the full strategies in the library (Strategies 09 and 10 are specified separately). Running them out of roadmap order is a screening exercise, not strategy development; the owner's approval of this protocol covers that deviation from [ADR-018](../adr/ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md) ordering.
- The matched control shares the fill rule's R:R check, which removes narrow-stop controls more often; the redraw and missing counts are reported.
- One year and ten stocks is a screen: it can promote a false positive and miss a real but small edge. That is why confirmation uses different days and all 50 stocks.
