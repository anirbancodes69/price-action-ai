# 02 — Failed Breakout

| Field | Value |
|---|---|
| Strategy id | `failed_breakout` |
| Roadmap position | 02 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `FUNCTIONAL_TESTING` (Stage 2 merged in PR #74; Stage 3 tests written and green 2026-11-22, PR pending; no registry entry yet, so not `BACKTESTING`) |
| Executable directions | Long (disabled in `0.1.0`-`0.3.0`; enabled only in the research ruleset `0.4.0`) |
| Ruleset version | `pa-intraday 0.4.0` for research runs (`0.3.0` plus `setup.failed_breakout_enabled` and `setup.failed_break_max_bars`); `0.1.0`-`0.3.0` unchanged; the live scanner stays on `0.1.0` |
| Specification approved | **Approved by the owner, 2026-11-22** (P-1..P-5 as written, §26) |
| Last updated | 2026-11-22 |

Sections 1-16 are the **specification** (what the strategy must do). Section 17 records what the **code does today**. The authoritative rule text is [TRD-04 §7A](../trading/04_SETUP_DETECTION_RULES.md); the vectors are TV-SET-29..35 ([TRD-08](../trading/08_TRADING_ENGINE_VALIDATION.md)). No performance claim exists for this strategy.

## 1. Strategy overview

Price closes below a level where buyers are expected to defend (a swing low, equal lows, a support zone, the previous-day low or the opening-range low). That close looks like acceptance below the level, a confirmed breakdown. Within a few bars price closes back above the level. The strategy buys that failure: the breakdown was a trap, and the sellers who entered on it are now on the wrong side.

This is the *failed breakdown*, the long-side mirror of the failed breakout of a high. The failed breakout of a high is bearish, so it is not executable under long-only actionability (ADR-014); see §8.

## 2. Strategy objective

A successful trade enters after the reclaim is confirmed by a close above the reclaim bar's high, holds above the breakdown low, and reaches the first overhead target that offers at least `risk.min_rr` (2.0) before the session-end exit. The stop is structural (the breakdown low), so a resumed breakdown costs about 1R.

## 3. Trading hypothesis

A close below a known support level, followed within `N` five-minute bars by a close back above it, means the breakdown found no follow-through. Sellers who entered on the break are trapped above their stops-to-be, and buyers who defended the level were right, so price tends to rotate up to the next overhead level more often than the 1:2 payoff needs.

The hypothesis is contradicted if, on the out-of-sample segment, net expectancy per trade is not positive in both experiments 4a and 4b, or gross expectancy is not positive, or the result depends on one period, one anchor type or one regime, per [validation criteria](../research/validation-criteria.md) §3 (the approved D-2 thresholds, unchanged after seeing results).

Known risk, stated before any run: Strategy 01 trades the wick version of the same idea on the same levels and lost in-sample (net -0.33R, gross -0.16R, every slice negative; [S01 §21](liquidity-sweep-reversal.md#21-in-sample-results)). This strategy requires a *close* beyond the level and a *close* back, so the two never trade the same event, but the same weakness (reclaim entries at support in this universe and period) may apply. The first 4a in-sample result decides whether this survives; there is no tuning round before it.

## 4. Market conditions

- Applies from the first session bar (the opening range must exist for `OR_LOW`) until the entry cutoff (`session.entry_cutoff_minutes_before_close`, 45 minutes before close).
- No regime filter and no 15m context filter: regime is reported, not used (D-5, standards §2).
- Stands aside when no level is broken by a close and reclaimed by a close within `N` bars, when the level was already broken by an earlier close, and after the cutoff.

## 5. Instruments

NIFTY 50 cash equities (the stored bars). Corporate-action exclusions and the survivorship flag follow the [data limitations](../research/research-data-limitations.md). The special sessions listed in `app/backtest/exclusions.py` are excluded (D-7).

## 6. Timeframes

Setup and trigger: 5m closed bars. Levels: 5m and 15m confirmed swing lows (15m only through its confirmation time, no look-ahead), 5m `EQUAL_LOWS` pools, support zones, `PDL` (daily bars, context only), `OR_LOW`. These are the same neutral facts Strategy 01 uses (P-3).

## 7. Bullish setup

`sbuf = structure.break_buffer_pct_5m / 100`, `bb = setup.breakout_buffer_pct / 100`, `sb = risk.stop_buffer_pct / 100`, `N = setup.failed_break_max_bars` (proposal P-2: 6). Bars `b`, `r`, `t` are 5m indexes in the current session.

1. **Level `Y`** is one of: confirmed 5m swing low; confirmed 15m swing low; `EQUAL_LOWS` pool; `Z.low` of an `ACTIVE` support zone (role `SUPPORT` at the close of bar `b − 1`); `PDL`; `OR_LOW`. `Y` is known before bar `b`.
2. **Unbroken:** no 5m close below `Y × (1 − sbuf)` since the level formed and before bar `b`.
3. **Breakdown bar `b`:** `C[b] < Y × (1 − sbuf)`. A wick below `Y` that closes at or above `Y × (1 − sbuf)` is not a breakdown (that is Strategy 01's event, and the two are disjoint by this close test).
4. **Failure (reclaim bar `r`):** the first bar `r` with `b < r ≤ b + N` and `C[r] ≥ Y`. If no such bar exists by `b + N`, the candidate is dropped.
5. `break_low = min(L[b..r])`. Detection bar = `r`. `trigger_price = H[r]`. Status `AWAITING_CONFIRMATION`.
6. **One setup per breakdown:** if one close breaks several levels, the level reclaimed **first** is used (the smallest `r`); among levels reclaimed on the same bar, the highest `Y`, then the anchor order `PDL, OR_LOW, EQUAL_LOWS, ZONE, SWING_LOW_5M, SWING_LOW_15M`. A bar after `r` never changes the choice (G-4). A level (anchor, price) is used once per session.

## 8. Bearish setup

`Not specified`. The mirror is the failed breakout of a high (close above a resistance level, then a close back below). It is bearish, not executable under long-only actionability, and not built. It is reported as `UNSUPPORTED`, not as zero (standards §5.2). Short research is governed by D-4 (deferred); if D-4 is approved later, the mirror gets its own specification round.

## 9. Entry rules

Reference entry while waiting: `trigger_price`. On confirmation at bar `c`, `entry = C[c]`; simulated fill at `O[c+1]` subject to `risk.max_entry_gap_pct` and TRD-05 §7 (BT-02). `r` and `c` must end by the entry cutoff.

## 10. Confirmation rules

A 5m close `> trigger_price × (1 + bb)` at a bar after `r`, within `setup.expiry_bars` (12) of `r`. Own rule only. If one bar both invalidates and confirms it, it is invalidated (SD-01).

## 11. Stop-loss rules

`stop = break_low × (1 − sb)`, rounded down to tick. The distance gates `risk.min_stop_distance_pct` (0.15) and `risk.max_stop_distance_pct` (2.0) apply (TRD-05 §4). Because `break_low` can be several bars deep, stops are wider than Strategy 01's; the gate rejects the too-wide ones (`STOP_TOO_WIDE`).

## 12. Target rules

The shared ladder of TRD-04 §8.3, first candidate with reward-to-risk ≥ `risk.min_rr` (2.0), in the order: `EQUAL_HIGHS` pool above entry, then `PDH`, `SESSION_HIGH`, `OR_HIGH`, then resistance zone lows, then the highest confirmed 15m swing high, then a measured move. No strategy-specific candidate is added in the first version (P-5). If none reaches `min_rr`, the candidate is `NO_TRADE` (`RR_BELOW_MINIMUM`) and is not traded in the isolated run. Targets round down to tick.

## 13. Invalidation rules

- Before confirmation: any close after `r` below `Y × (1 − sbuf)` → `INVALIDATED` (`BREAK_RESUMED`); a close `< break_low` is covered by the same rule; `age > setup.expiry_bars` → `EXPIRED` (`AGED_OUT`); entry cutoff → `EXPIRED` (`SESSION_CUTOFF`).
- After entry: the stop; the target; the session-end exit (`session.exit_minutes_before_close`, 15). The bearish-CHoCH structure exit is not part of the strategy (off in the isolated runs, as in S01).
- No `HTF_AGAINST` invalidation.

## 14. Configuration parameters

| Key | Default | Range to test | Used by | Source |
|---|---|---|---|---|
| `setup.failed_breakout_enabled` | false (new, P-4) | n/a | enable flag | this page |
| `setup.failed_break_max_bars` (`N`) | 6 (new, P-2; a hypothesis, not tuned from data) | 3, 6, 9 | reclaim window | this page |
| `structure.break_buffer_pct_5m` (`sbuf`) | 0.05 | ±25%, ±50% | breakdown depth, unbroken test | TRD-02 |
| `structure.equal_level_tolerance_pct` | 0.1 | ±25%, ±50% | `EQUAL_LOWS` / `EQUAL_HIGHS` | TRD-03 §6 |
| `pivot.*`, `zone.*`, `session.opening_range_minutes` | see ruleset | not tuned in the first round | levels | TRD-02, TRD-03 |
| `setup.breakout_buffer_pct` (`bb`) | 0.05 | ±25%, ±50% | confirmation | TRD-04 §2 |
| `setup.expiry_bars` | 12 | 6, 12, 18 | expiry | SD-02 |
| `risk.stop_buffer_pct` | 0.05 | ±25%, ±50% | stop | TRD-05 §4 |
| `risk.min_stop_distance_pct` / `max_` | 0.15 / 2.0 | ±25%, ±50% | distance gate | TRD-05 §4 |
| `risk.min_rr` | 2.0 | 1.5, 2.0, 2.5 | target gate | TRD-05 |
| `session.entry_cutoff_minutes_before_close` | 45 | not tuned | cutoff | TRD-01 §4.1 |

The authoritative registry stays in [TRD-01 §6](../trading/01_TRADING_METHODOLOGY.md#6-ruleset-parameter-registry-authoritative). Variation is exploratory on in-sample data only, and every variant is logged.

## 15. Dependencies

Shared facts, used by name: 5m and 15m confirmed swing pivots, `EQUAL_LOWS` / `EQUAL_HIGHS` pools, support/resistance zones, `PDL`, `PDH`, `OR_LOW`, `OR_HIGH`, `SESSION_HIGH`, tick size, session calendar. Shared mechanics: the setup lifecycle (`replay_simple`), the next-open fill simulator, costs, risk sizing, and the single-strategy run mode built for Strategy 01.

Dependency on another strategy: **None.** It does not use Strategy 01 sweep signals, ORB, PDH break or breakout-retest signals, nor BOS/CHoCH as entry conditions. The `FAILED_BREAKOUT` end reason inside Breakout-Retest is a different thing and is not reused. Isolation hazards to remove in the run mode: the all-detectors `analyse()` path, `choose_signal` ranking, the PAQS gate, the shared structure exit, and setup-specific branches inside the shared `trade_levels()`.

## 16. Edge cases

- **Opening gap:** a gap down below `Y` that closes below `Y × (1 − sbuf)` on the first bar is a breakdown bar; the reclaim must still come from later closes.
- **Same bar breaks and reclaims:** not possible by definition (`C[b]` is below, `C[r]` is at or above, `r > b`).
- **Two levels broken by one close:** one setup, the level reclaimed first, ties the highest (rule 6). The other level is not traded: its first break was this bar, so it cannot start a second breakdown.
- **Missing candles / data gaps:** a session with a missing-bar issue for that symbol is excluded and logged (standards §7).
- **Special sessions:** excluded (D-7).
- **Cutoff:** no setup is detected or confirmed by a bar ending after the cutoff.
- **Zero risk:** `entry ≤ stop` is rejected by the shared level check.
- **Corporate actions:** a symbol-session near an adjustment is excluded per the data limitations.
- **Overlap with Strategy 01:** the close test makes the events disjoint. A level that failed this way is no longer "unbroken" for Strategy 01 either; the two never run together, so this is documentation, not interaction.

## 17. Implementation details (code today)

Module `python-engine/app/domain/setups/failed_breakdown.py` (`detect_failed_breakdown`, Stage 2, T-I143). Setup type `FAILED_BREAKDOWN_RECLAIM` (the name `FAILED_BREAKOUT` stays only the Breakout-Retest end reason).

| Concept | Code |
|---|---|
| `evaluate()` | `detect_failed_breakdown(ctx)`: levels from `support_levels` / `zone_levels` (`setups/support_levels.py`), breakdown test `first_break == b`, reclaim `_reclaim`, emits `Setup` |
| `validate()` | `replay_simple(..., invalid_close=("BREAK_RESUMED", Y × (1 − sbuf), True), htf_blocks=False)` |
| `get_entry()` | `entry_reference()` in `levels.py` |
| `get_exit()` | `trade_levels()` in `levels.py` (shared ladder, no strategy-specific candidate, P-5); `risk/exits.py` |
| `get_invalidation()` | `BREAK_RESUMED`, `AGED_OUT`, `SESSION_CUTOFF` |
| `get_metadata()` | `Setup` fields `swept_level` (the level `Y`), `sweep_low` (`break_low`), `breakdown_index`, `anchor` |

- **Shared level facts.** The level construction that Strategy 01 used (`Level`, `first_break`, `support_levels`, `zone_levels`, `ANCHOR_ORDER`) moved unchanged from `liquidity_sweep.py` into the neutral `setups/support_levels.py`, so neither strategy imports the other. Strategy 01's tests, the golden outputs and its real-bar isolation proof are unchanged.
- **Ruleset** `pa-intraday 0.4.0` ([changelog](../../python-engine/rulesets/CHANGELOG.md)); the type is not yet in the database `setup_type` CHECK constraints or the API enum, so `0.4.0` must not be activated for the scanner before a schema and contract change.
- **Run mode.** `strategy_detectors("failed_breakout")`; the Strategy 01 run mode is reused unchanged: `scripts/run_backtest.py --ruleset pa-intraday@0.4.0 --strategy failed_breakout --experiment 4a|4b`. Scoring gives this setup no points (outside the isolated runs).
- Limits: long only; PAQS points are not defined.

## 18. Functional test coverage

Stage 2 tests (`tests/trading/test_setups_failed_breakdown.py`, 17 tests, hand-computed, TV-SET-29..35): disabled before `0.4.0` and registered; breakdown by close, reclaim by close, confirmation; awaiting confirmation; a wick is not a breakdown (and is a sweep for Strategy 01); reclaim at the window edge and one bar later; window read from the ruleset; no reclaim; a level used once and a re-break is not a new breakdown; `BREAK_RESUMED`; expiry; reclaim after the cutoff; breakdown after the cutoff; stop at `break_low` and the ladder; determinism. Real-bar isolation proof (`scripts/check_strategy_isolation.py --strategy failed_breakout --ruleset pa-intraday@0.4.0`): 0 differences over 8,640 analyses (6 sessions, 20 symbols).

**Stage 3 (2026-11-22):** `tests/trading/test_setups_failed_breakdown_stage3.py` (27 tests) and `tests/backtest/test_strategy_run_failed_breakout.py` (6 tests), all hand-computed.

| Process §4 area | Covered by |
|---|---|
| Setups | one test per anchor (`OR_LOW`, 5m swing low, `EQUAL_LOWS`, zone, 15m swing low, `PDL` from Stage 2); inactive or non-support zone gives none; 15m swing low only from its confirmation; bearish form: not supported (§8), no test |
| Several levels, one close | earliest reclaim wins, the highest wins on the same bar, anchor order for the same price |
| Levels | stop at `break_low` with tick rounding; minimum and maximum stop distance at the boundary; target ladder; `RR_BELOW_MINIMUM` flagged |
| Lifecycle | `BREAK_RESUMED` at and below the buffer; a wick below the break low does not invalidate; expiry at 12 / 13 bars; entry cutoff at the boundary; a level used once |
| Data | opening gap below `PDL` on the first session bar; previous-session bars ignored; missing candle not filled; short and duplicate input give no signal |
| Boundaries | close exactly at, and just below, `Y × (1 − sbuf)`; reclaim at and just below `Y`; confirmation at and above the trigger buffer; window `N` and `N + 1` (Stage 2) |
| Look-ahead | a setup found at bar *k* equals the one from the day cut at *k*, on a two-level fixture (fails on the first implementation, G-4) |
| Replay | bar-by-bar confirmations equal the full run |
| Isolation | alone equals the strategy's own candidates of the combined run, bar by bar, with no score; the run is flagged and trades only this type; real-bar proof: 0 differences over 8,640 analyses (6 sessions, 20 symbols) |
| Run mode | 4a and 4b records and flags; 4b slot limit; ruleset `0.4.0` differs from `0.3.0` only in the two new keys |

Not covered: shorts (unsupported by design); a live-scanner or database path (the type is not in the CHECK constraints yet).

## 19. Independent backtest configuration

`Not run`. Same as Strategy 01: single-strategy run mode, experiment 4a then 4b, data 2024-01-01..2026-11-19 with 1D-bar levels and special sessions excluded, costs unverified until D-6, regimes by `context_15m`, 60/20/20 split. The 4a in-sample run is pre-registered in the [registry §1.2](../research/experiment-registry.md#12-pre-registration-strategy-02-experiment-4a-in-sample-registered-2026-11-22-before-any-chunk-ran) (2026-11-22) before it starts.

## 20. Historical performance
`Not run`.

## 21. In-sample results
`Not run`.

## 22. Out-of-sample results
`Not run`.

## 23. Walk-forward results
`Not run`.

## 24. Robustness analysis
`Not run`. Variants tried: none.

## 25. Known limitations

Data limits L-1.. in [research data limitations](../research/research-data-limitations.md) (survivorship, no 1m data so a bar touching stop and target counts as the stop, unverified costs). Strategy limits: long only; stops use the breakdown low and can be wide; the failure window `N` is a single hypothesis value; the close-based breakdown cannot separate a real trap from a slow rotation.

## 26. Outstanding issues

| ID | Item | Proposal for the owner |
|---|---|---|
| P-1 (approved 2026-11-22) | Definition | Long-side *failed breakdown* (close below support, then close back above), disjoint from Strategy 01 by the close test. The failed breakout of a high is bearish: not executable, reported `UNSUPPORTED` (D-4 deferred) |
| P-2 (approved 2026-11-22) | Reclaim window `N` | One new parameter, `setup.failed_break_max_bars`, default 6 bars (30 minutes), fixed before any result. Sensitivity 3 / 6 / 9 only at Stage 5 |
| P-3 (approved 2026-11-22) | Levels | The same six anchors as Strategy 01, so results compare cleanly. No anchor selection from Strategy 01's results |
| P-4 (approved 2026-11-22) | Ruleset | `pa-intraday 0.4.0` = `0.3.0` plus `setup.failed_breakout_enabled` (false by default; the live scanner is unchanged) and `setup.failed_break_max_bars`. The ruleset registry (TRD-01 §6) and the ruleset changelog are updated in the Stage 2 PR |
| P-5 (approved 2026-11-22) | Exits and target | Stop at `break_low`, shared target ladder with no strategy-specific candidate, exits stop / target / session end |

| G-4 (Stage 3 finding, 2026-11-22) | Rule 6 read literally ("the highest `Y` that is reclaimed") | The first implementation chose the highest level reclaimed anywhere in the window, so a bar after `r` could replace a setup already detected (look-ahead; found by the Stage 3 look-ahead test). Fixed before any backtest: the earliest reclaim wins, ties the highest. Rule 6 above is reworded to say so. No result existed, so no parameter or outcome changed. **For the owner's information; no new approval is requested unless you want the highest-first reading instead (it cannot be run without look-ahead).** |

## 27. Acceptance decision

Not decided. Status `SPECIFICATION_APPROVED`. The checklist ([process §5](../development/strategy-development-process.md#5-acceptance-checklist)) has nothing ticked.

## 28. Future improvements

None proposed. Anything not in §7-§13 is out of scope until this strategy has a validation result.

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md) · [Strategy 01 (parked)](liquidity-sweep-reversal.md) · [TRD-04](../trading/04_SETUP_DETECTION_RULES.md)
