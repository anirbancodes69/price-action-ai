# 01 — Liquidity Sweep / Reversal

| Field | Value |
|---|---|
| Strategy id | `liquidity_sweep_reversal` |
| Roadmap position | 01 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `DEFERRED` (parked by the owner 2026-11-22 after a negative 4a in-sample result, §21 and §27; improvement rounds used: 0 of 3). Specification `SPECIFICATION_APPROVED`; run mode built |
| Executable directions | Long |
| Ruleset version | `pa-intraday 0.3.0` for research runs (`0.2.0` plus the structure exit off, P-4); `0.2.0` enables the setup; the live scanner stays on `0.1.0` |
| Specification approved | **Approved by the owner, 2026-11-21** (P-1..P-4 as written, §26) |
| Last updated | 2026-11-22 |

Sections 1-16 are the **specification** (what the strategy must do). Section 17 records what the **code does today**; §26 lists where they differ. The authoritative rule text stays in [TRD-04 §7](../trading/04_SETUP_DETECTION_RULES.md); this page adds the isolation statements and the pieces TRD-04 leaves open. The only performance evidence is the in-sample 4a result in §21.

## 1. Strategy overview

Price runs below an obvious level where long stops are likely to sit (a swing low, equal lows, a support zone, the previous-day low or the opening-range low) with a wick, then closes back above it. The strategy buys the reclaim: the structure that looked broken to the downside was a stop run, not acceptance below the level.

## 2. Strategy objective

A successful trade enters after the reclaim is confirmed by a close above the reclaim bar's high, holds above the sweep low, and reaches the first overhead target that offers at least `risk.min_rr` (2.0) before the session-end exit. The stop is structural (the sweep low), so a failed reclaim costs about 1R.

## 3. Trading hypothesis

After a wick below a known liquidity level that closes back above it within one bar (or two), the stops below the level have been taken and sellers have not been able to hold price under it, so price tends to rotate up to the next liquidity (equal highs, session or zone highs) more often than the 1:2 payoff needs.

The hypothesis is contradicted if, on the out-of-sample segment, net expectancy per trade is not positive in both experiments 4a and 4b, or gross expectancy is not positive, or the result depends on one period, one anchor type or one regime, per [validation criteria](../research/validation-criteria.md) §3. Thresholds are the approved D-2 values and are not changed after seeing results.

## 4. Market conditions

- Applies from the first bar after the opening range exists (for `OR_LOW`) or from the first session bar (other anchors) until the entry cutoff (`session.entry_cutoff_minutes_before_close`, 45 minutes before close).
- No regime filter. The 15m context filter (SD-05) is **not** part of this strategy: a bearish 15m state does not block it (TRD-04 §7). Regime is reported, not used (D-5).
- Stands aside when no level is swept and reclaimed, when the level was already broken by a close below `Y × (1 − sbuf)`, and after the cutoff.

## 5. Instruments

NIFTY 50 cash equities (same universe as the stored bars). Corporate-action exclusions and the survivorship flag follow the [data limitations](../research/research-data-limitations.md). The four short special sessions in the 2024-2025 history are excluded (D-7).

## 6. Timeframes

Setup and trigger: 5m closed bars. Levels: 5m and 15m confirmed swing lows (15m only through its confirmation time, no look-ahead), 5m `EQUAL_LOWS` pools, support zones built from 5m and 15m pivots, `PDL` (daily bars, context only), `OR_LOW` (first `session.opening_range_minutes`).

## 7. Bullish setup

`sbuf = structure.break_buffer_pct_5m / 100`, `sb = risk.stop_buffer_pct / 100`, `bb = setup.breakout_buffer_pct / 100`. Bars `w`, `t` are 5m indexes in the current session.

1. **Level `Y`** is one of: confirmed unbroken 5m swing low; confirmed unbroken 15m swing low; `EQUAL_LOWS` pool; `Z.low` of an `ACTIVE` support zone (role `SUPPORT` at the close of bar `w − 1`); `PDL`; `OR_LOW`. `Y` is known before bar `w`.
2. **Unbroken:** no 5m close below `Y × (1 − sbuf)` since the level formed and before bar `w`.
3. **Sweep:** `L[w] < Y × (1 − sbuf)`.
4. **Reclaim**, either:
   - same bar: `C[w] ≥ Y`; or
   - two-bar: `C[w] < Y`, `C[w] ≥ Y × (1 − sbuf)`, `C[w+1] ≥ Y` and `L[w+1] ≥ L[w] × (1 − sbuf)`.
5. A close of `w` below `Y × (1 − sbuf)` is a structural break and cancels the candidate for `w`.
6. Detection bar `r` = the reclaim bar (`w` or `w+1`). `sweep_low = min(L[w], L[w+1])` for a two-bar reclaim, else `L[w]`. `trigger_price = H[r]`. Status `AWAITING_CONFIRMATION`.
7. **One setup per sweep bar:** the highest `Y` reclaimed on it; ties by anchor order `PDL, OR_LOW, EQUAL_LOWS, ZONE, SWING_LOW_5M, SWING_LOW_15M`. A level (anchor, price) is used once per session (SD-04).

## 8. Bearish setup

`Not specified`. The mirror (sweep of highs and rejection) is not built and not executable. Reported as `UNSUPPORTED` in metrics, not as zero (standards §5.2). Short research is governed by D-4 (deferred).

## 9. Entry rules

Reference entry while waiting: `trigger_price`. On confirmation at bar `c`, `entry = C[c]` (SD-07); simulated fill at `O[c+1]` subject to `risk.max_entry_gap_pct` and TRD-05 §7 (BT-02). The confirmation applies to the next bar's open only (SD-03). `r` and `c` must end by the entry cutoff (SD-08).

## 10. Confirmation rules

A 5m close `> trigger_price × (1 + bb)` at a bar after `r`, within `setup.expiry_bars` (12) of `r`. Own rule only; no other strategy or indicator confirms it. If one bar both invalidates and confirms it is invalidated (SD-01).

## 11. Stop-loss rules

`stop = sweep_low × (1 − sb)`, rounded down to tick. Distance checks `risk.min_stop_distance_pct` (0.15) and `risk.max_stop_distance_pct` (2.0) apply (TRD-05 §4). Shared infrastructure: the `stop_price` helper and the distance check; the stop base is this strategy's own.

## 12. Target rules

Ladder per TRD-04 §8.3: the first candidate with reward-to-risk ≥ `risk.min_rr` (2.0) wins. Candidates in order: (1) strategy-specific: an `EQUAL_HIGHS` pool above entry, nearest first; (2) `PDH`, `SESSION_HIGH`, `OR_HIGH` above entry; (3) resistance zone lows above entry; (4) highest confirmed 15m swing high above entry; (5) measured move from the last completed 5m swing leg. These are neutral facts used by name in this strategy's exit. If none reaches `min_rr`, the target is the nearest candidate, `rr_below_min` is set and the candidate is `NO_TRADE` (`RR_BELOW_MINIMUM`): it is **not** traded in the isolated run. Targets round down to tick.

## 13. Invalidation rules

- Before confirmation: a close `< sweep_low` → `INVALIDATED` (`SWEEP_FAILED`); `age > setup.expiry_bars` → `EXPIRED` (`AGED_OUT`); entry cutoff → `EXPIRED` (`SESSION_CUTOFF`).
- After entry: the stop; the target; the session-end exit (`session.exit_minutes_before_close`, 15). **A bearish 5m CHoCH structure exit is not part of this strategy** (proposal P-3); the structure exit is switched off in the isolated runs, and a run with it is logged as a separate variant.
- No `HTF_AGAINST` invalidation (SD-05 exception). No CHoCH invalidation before entry (OQ-SD-08).

## 14. Configuration parameters

| Key | Default (`pa-intraday 0.2.0`) | Range to test | Used by | Source |
|---|---|---|---|---|
| `setup.liquidity_sweep_enabled` | true | n/a | enable flag | TRD-01 App. B |
| `structure.break_buffer_pct_5m` (`sbuf`) | 0.05 | ±25%, ±50% | sweep depth, unbroken test, reclaim | TRD-02 |
| `structure.equal_level_tolerance_pct` | 0.1 | ±25%, ±50% | `EQUAL_LOWS` / `EQUAL_HIGHS` | TRD-03 §6 |
| `pivot.left_bars_5m` / `right_bars_5m`; `_15m` | 2 / 2 | not tuned in the first round | swing-low levels | TRD-02 |
| `zone.*` | see ruleset | not tuned in the first round | zone levels | TRD-03 |
| `session.opening_range_minutes` | 15 | not tuned | `OR_LOW` | TRD-03 §8 |
| `setup.breakout_buffer_pct` (`bb`) | 0.05 | ±25%, ±50% | confirmation | TRD-04 §2 |
| `setup.expiry_bars` | 12 | 6, 12, 18 | expiry | SD-02 |
| `risk.stop_buffer_pct` | 0.05 | ±25%, ±50% | stop | TRD-05 §4 |
| `risk.min_stop_distance_pct` / `max_` | 0.15 / 2.0 | ±25%, ±50% | distance gate | TRD-05 §4 |
| `risk.min_rr` | 2.0 | 1.5, 2.0, 2.5 | target gate | TRD-05 |
| `session.entry_cutoff_minutes_before_close` | 45 | not tuned | cutoff | TRD-01 §4.1 |

The authoritative registry stays in [TRD-01 §6](../trading/01_TRADING_METHODOLOGY.md#6-ruleset-parameter-registry-authoritative). Variation is exploratory on in-sample data only, and every variant is logged.

## 15. Dependencies

Shared facts, used by name: 5m and 15m confirmed swing pivots, `EQUAL_LOWS` / `EQUAL_HIGHS` pools, support/resistance zones (`zone_build`), `PDL`, `PDH`, `OR_LOW`, `OR_HIGH`, `SESSION_HIGH`, tick size, session calendar. Shared mechanics: the common setup lifecycle (`replay_simple`), the next-open fill simulator, costs, risk sizing.

Dependency on another strategy: **None.** The strategy does not use ORB, PDH break or breakout-retest signals, nor BOS/CHoCH events as entry conditions. Isolation hazards to remove in the run mode (D-8): the all-detectors `analyse()` path, `choose_signal` ranking, the PAQS `LOW_SCORE` gate, the shared bearish-CHoCH exit, and the setup-specific branches inside the shared `trade_levels()`.

## 16. Edge cases

- **Opening gap / first bar:** a gap down through `Y` on the first session bar with a reclaim is a valid sweep of `PDL` (tested). The code starts at `max(first, 1)`; with stored data the session is always preceded by lookback bars, so `first ≥ 1`.
- **Missing candles / data gaps:** the strategy does not fill gaps; a session with a missing-bar issue for that symbol is excluded and logged (standards §7).
- **Special sessions:** the four short sessions are excluded.
- **Same price from two anchors:** one setup per sweep bar, tie by anchor order. A deeper low on the reclaim bar counts as its own same-bar sweep (OQ-SD-08).
- **Duplicate signals:** (anchor, price) used once per session. A different anchor at the same price is a separate level (see G-3).
- **Cutoff:** no setup is detected or confirmed by a bar ending after the cutoff.
- **Zero risk:** `entry ≤ stop` is rejected by the shared level check.
- **Corporate actions:** a symbol-session near an adjustment is excluded per the data limitations.

## 17. Implementation details (code today)

Module `python-engine/app/domain/setups/liquidity_sweep.py` (`detect_liquidity_sweep`), merged in PR #66 (T-I141).

| Concept | Code |
|---|---|
| `evaluate()` | `detect_liquidity_sweep(ctx)`: builds the levels (`_levels`, `_zone_levels`), tests `_reclaim`, emits `Setup` |
| `validate()` | `replay_simple(..., invalid_close=("SWEEP_FAILED", sweep_low, True), htf_blocks=False)` |
| `get_entry()` | `entry_reference()` in `levels.py` |
| `get_exit()` | `trade_levels()` in `levels.py` (sweep branch adds `EQUAL_HIGHS`); `risk/exits.py` |
| `get_invalidation()` | `SWEEP_FAILED`, `AGED_OUT`, `SESSION_CUTOFF` |
| `get_metadata()` | `Setup` fields `swept_level`, `sweep_low`, `same_bar_reclaim`, `anchor` |

Limits: long only; PAQS gives the anchors `PDL`, `OR_LOW`, `EQUAL_LOWS` and swing lows no key-level points (OQ-SD-07, outside isolated runs).

**Stage 2 (built 2026-11-21, T-I142):** the single-strategy run mode.

- `analyse(..., detectors=strategy_detectors("liquidity_sweep_reversal"), isolated=True)` runs only `detect_liquidity_sweep`, leaves `paqs` empty and uses `choose_signal(score_gate=False)`. The defaults (`detectors=None`, `isolated=False`) are the live behaviour and are tested equal.
- Registry: `app/domain/strategies.py`. Run: `app/backtest/strategy_run.py` and `scripts/run_backtest.py --ruleset pa-intraday@0.3.0 --strategy liquidity_sweep_reversal --experiment 4a|4b [--tie-break-seed N]`.
- 4a: `unlimited_profile` lifts the position, open-risk, daily-loss, streak, value and capital limits; the size is the fixed risk unit (0.5% of the capital per trade, ₹500 on ₹1,00,000). One open trade per symbol. The shared fill rules still apply: a gap that degrades the reward-to-risk below the minimum (`SKIPPED_RR_DEGRADED`), the cutoff and the maximum entry gap.
- 4b: project limits (TRD-05); candidates closing on the same bar compete in the order of `sha256(seed | session date | symbol)`. A second seed is the required second tie-break run.
- Run record carries `strategy_id` and `experiment`; flags `costs_unverified` and `UNSUPPORTED_DIRECTION:SHORT`. A combined run is flagged `NOT_ISOLATED`.
- Exits in an isolated run: stop, target, session end (the structure exit is off in `0.3.0`). `trade_levels()` stays shared and its sweep branch is this strategy's own ladder (§12).
- Selection when two sweep setups confirm on the same bar of one symbol: the one detected last, then detection order (`choose_signal`, stable sort).

## 18. Functional test coverage

Run on 2026-11-21: 13 tests in `python-engine/tests/trading/test_setups_sweep.py` (TV-SET-19..28, cutoff, no-look-ahead) and 24 in `python-engine/tests/trading/test_setups_sweep_stage3.py`; 11 run-mode tests in `python-engine/tests/backtest/test_strategy_run.py`. The full engine suite, ruff and mypy (`app`) pass.

| Stage 3 area | Tests |
|---|---|
| Setups valid / invalid, bullish | TV-SET-20..22; one test per anchor: `PDL` (TV-SET-20), `OR_LOW`, `SWING_LOW_5M`, `EQUAL_LOWS`, `ZONE` (active support zone only: an inside or flipped zone gives none), `SWING_LOW_15M` (not usable before its 15m confirmation) |
| Bearish | n/a (unsupported; reported `UNSUPPORTED_DIRECTION:SHORT`) |
| Levels | TV-SET-26, 27; stop tick rounding and the minimum (0.15%) and maximum (2.0%) stop distance at, above and below the limit (5 cases) |
| Lifecycle | `SWEEP_FAILED` at and below the sweep low; expiry at age 12 (live) and 13 (`AGED_OUT`); entry cutoff at the boundary (345 and 346 minutes); a level used once per session; tie between two anchors at one price |
| Data | gap open below `PDL` on the first session bar; previous-session bars never form a setup; a missing candle is not filled; invalid input (duplicate bar) and short history give no signal |
| Boundaries | sweep depth (TV-SET-23); reclaim close at `Y` and just below; two-bar low limit at and below; confirmation at and above `trigger × (1 + bb)` |
| Look-ahead | truncated-data tests (two fixtures); 15m level unusable before its confirmation |
| Replay | bar-by-bar fresh runs confirm on the same bar as the full-day run |
| Isolation proof | synthetic (`test_strategy_run.py`) and **real bars**: `python-engine/scripts/check_strategy_isolation.py --strategy liquidity_sweep_reversal --sessions 3 --symbols 10 --to <date>`, 2026-11-21, `pa-intraday 0.3.0`, 10 NIFTY 50 symbols, every 5m bar: sessions ending 2026-11-19, 2026-07-15, 2025-09-26 and 2024-06-28, 3 sessions each (8,910 analyses, 22,538 setups): **0 differences** between the single-strategy setups and levels and the sweep part of the combined run. The proof covers the detection and level step; the replay, sizing and exits of the run mode are covered by the 11 run-mode tests |

Not covered: the exact-tick boundary on `OR_LOW` and `PDL` set from the daily bars (the loader derives `PDL` from the previous session's 5m bars; data limitation L-4), and any intrabar order (no 1m data).

## 19. Independent backtest configuration

Run mode built (§17). 4a in-sample done (§21); 4b, out-of-sample, holdout and walk-forward are `Not run`. Per [standards §3-§5](../research/independent-backtesting-standards.md): a single-strategy run mode (only this detector, candidates taken directly, no PAQS gate, no 15m filter, exits stop / target / session end), experiment 4a (every candidate traded, no slot limits) then 4b (`calculate_risk` and account limits with a documented tie-break and a second tie-break rerun). Data 2024-01-01..2026-11-19 with daily bars from 2024 (D-7), special sessions excluded, costs unverified until D-6. Regimes by the recorded 15m structure state at signal time (`context_15m`), fixed before any result.

## 20. Historical performance
`Not run`.

## 21. In-sample results

Experiment 4a (every candidate traded, fixed ₹500 risk unit, no account limits), `pa-intraday 0.3.0`, 2024-01-02..2025-09-23, 427 sessions (3 special sessions excluded), run 2026-11-21 from code `da8b0af` in 7 chunks and merged. Pre-registration and result: [registry §1.1](../research/experiment-registry.md). Raw output is kept outside the repository.

| Measure | Value |
|---|---|
| Trades | 11,363 |
| Win rate | 32.5% |
| Average R, gross / net | -0.16 / -0.33 |
| Profit factor | 0.54 |
| Net P&L (at ₹500 risk unit) | -₹18,42,560 |
| Cost drag | 15.5% of gross P&L |
| Exits | STOP 5,778; SESSION_END 4,638; TARGET 927; STOP_GAP 16; TARGET_GAP 3; STOP_COLLISION 1 |
| Skips | SKIPPED_RR_DEGRADED 7,556; ALREADY_IN_POSITION 3,627; SKIPPED_SESSION_CUTOFF 311; STOP_TOO_WIDE 89; RR_BELOW_MINIMUM 50 |

Net average R by slice (all negative): anchor EQUAL_LOWS -0.37, OR_LOW -0.34, PDL -0.24, SWING_LOW_15M -0.35, SWING_LOW_5M -0.33, ZONE -0.28; 15m context BEARISH -0.31, BULLISH -0.37, TRANSITION -0.32; every half hour from 09:00 (-0.15) to 14:30 (-0.33); all 21 months (best 2025-04 -0.19, worst 2025-09 -0.47).

Reading: the gross average R is negative, so costs (unverified, D-6) worsen the result but do not cause it. No slice is positive, so no regime filter would rescue it without a rule change. Drawdown percentage is not meaningful in 4a (no capital limit). Flags: `survivorship_bias_risk`, `costs_unverified`, `UNSUPPORTED_DIRECTION:SHORT`. G-3 (setups sharing a swept price): 64 trades, 0.6%, measured 2026-11-22 (§26). In-sample only: out-of-sample and holdout are untouched, 4b not run, no parameter changed.

## 22. Out-of-sample results
`Not run`.

## 23. Walk-forward results
`Not run`.

## 24. Robustness analysis
`Not run`. Variants tried: none.

## 25. Known limitations

Data limits L-1.. in [research data limitations](../research/research-data-limitations.md) (survivorship, no 1m data so a bar touching stop and target counts as the stop, unverified costs, `PDL` / `OR_LOW` depend on reliable daily levels and session hours L-4, L-5). Strategy limits: long only; wick-through-and-reclaim inside a 5m bar cannot be separated from a stop run that continues, because intrabar order is unknown.

## 26. Outstanding issues

| ID | Item | Decision / state |
|---|---|---|
| P-1 (approved 2026-11-21) | OQ-SD-08 (implementation choices where TRD-04 §7 is silent) | Adopt the listed choices as the specification: one setup per sweep bar for the highest level reclaimed (ties by anchor order), a level used once per session, zone level = `Z.low` of an `ACTIVE` support zone at `w − 1`, a close of `w` below `Y × (1 − sbuf)` rules out the two-bar reclaim, a deeper low on the reclaim bar is its own sweep, no CHoCH invalidation |
| P-2 (approved 2026-11-21) | OQ-SD-07 (PAQS points for non-zone anchors) | Leave open. Scoring is excluded from isolated runs (D-5), so it cannot affect validation. Decide only if the strategy later ranks live scanner results |
| P-3 (approved 2026-11-21) | Exit set | Stop, target and session-end only. The bearish-CHoCH structure exit is not part of the strategy; a run with it is logged as a variant |
| P-4 (approved 2026-11-21) | Strategy-only ruleset | Done as `pa-intraday 0.3.0`: `0.2.0` plus `exit.structure_exit_enabled=false`. Isolation of the detector comes from the run mode, not from the ruleset (the other setups have no enable flag). The live scanner stays on `0.1.0` |
| G-1 | Spec vs code | No difference found by reading or by the Stage 3 tests |
| G-3 | Same price through two anchors | A level is used once per (anchor, price), so a price that is both a swing low and an `EQUAL_LOWS` level can give two setups on two different sweep bars (tested, `test_tie_between_equal_lows_and_swing_low_at_the_same_price_takes_the_anchor_order`). TRD-04 SD-04 and OQ-SD-08 allow it. Not changed: it would alter which trades exist. **Measured on the 4a in-sample result (2026-11-22):** 32 (session, symbol, swept price) groups have two trades, 64 trades of 11,363 (0.6%); none has three. Pairs: SWING_LOW_5M with SWING_LOW_15M 9, EQUAL_LOWS with SWING_LOW_5M 8, EQUAL_LOWS with SWING_LOW_15M 5, other combinations 10. The 64 trades average -0.60R net against -0.33R for the rest; the 32 later trades of each pair average +0.08R net. Too few trades to move the aggregate (-0.33R either way), so no change is justified |
| G-2 | Adverse slippage on exits (audit R-2) | Run records state which exits carry slippage until the shared simulator is corrected |

## 27. Acceptance decision

**Parked, 2026-11-22 (owner decision).** Status `DEFERRED`; not `VALIDATION_FAILED`, because the full criteria were not evaluated: only the in-sample 4a run exists. Evidence: net average R -0.33 (gross -0.16), profit factor 0.54, negative in every anchor, 15m context, half hour and month (§21). Root cause is not established; costs and the G-3 shared-price effect (0.6% of trades) are ruled out as the cause. Rationale: no slice to filter on, and tuning on the same in-sample data risks overfitting ([process §6](../development/strategy-development-process.md#6-when-validation-fails)). What is preserved: the detector, the run mode, ruleset `pa-intraday 0.3.0`, the registry entries and §21. Not run: 4b, out-of-sample, holdout, walk-forward, Stage 5 (the out-of-sample and holdout data were never touched). Improvement rounds used: 0 of 3 ([criteria §5](../research/validation-criteria.md#5-improvement-rounds)). Reopening needs a stated hypothesis, a new ruleset version and data not used to choose the change, and it is a fresh owner decision. The checklist ([process §5](../development/strategy-development-process.md#5-acceptance-checklist)) is not ticked.

## 28. Future improvements

None adopted. Proposals only after validation: a short mirror (needs D-4 and a superseding ADR for actionability); a volume-free displacement measure for the reclaim (hypothesis: a larger reclaim body separates real sweeps from stop-run continuations; must be a new ruleset version and a new experiment).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md) · [Experiment registry](../research/experiment-registry.md)
