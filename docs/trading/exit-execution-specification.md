# Exit Execution Specification

| Item | Value |
|---|---|
| Status | Implemented and tested (Phase 1 P1, 2026-11-23) |
| Authority | One function: `evaluate_bar_exit` in `python-engine/app/domain/risk/exits.py`. The backtest (`step_position`) and the live monitor (`monitor_position`) both call it. TRD-06 §4.2 and TRD-07 §7.1 describe the same rule and defer to this page where they differ |
| Scope | Long positions, closed 5m bars, stop and target as resting levels. No trailing stop, break-even or partial exit (out of scope for Phase 1) |

## 1. The rule

For a position with `stop` and `target` (either may be absent for a manual trade; an absent level is never hit) and a closed 5m bar `j` that starts at or after the fill, the first matching row wins:

| Order | Condition on bar `j` | Exit price (simulation) | Reason |
|---|---|---|---|
| 1 | `O[j] <= stop` (gap through the stop) | `O[j]`, plus adverse slippage in the backtest | `STOP` (`STOP_GAP` in the backtest) |
| 2 | `O[j] >= target` (gap through the target) | `O[j]` | `TARGET` (`TARGET_GAP`) |
| 3 | bar `j` starts at or after the session-exit time (`session.exit_minutes_before_close`) and `exit.session_end_exit_enabled` | `O[j]` | `SESSION_END` |
| 4 | a bearish 5m CHoCH closed on bar `j-1` and `exit.structure_exit_enabled` | `O[j]` | `STRUCTURE_EXIT` |
| 5 | `L[j] <= stop` | `stop` less adverse slippage | `STOP` (`STOP_COLLISION` when the same bar also reached the target) |
| 6 | `H[j] >= target` | `target`, no positive slippage | `TARGET` |

**Same-bar collision** (rows 5 and 6 both true, or a gap-down bar that also reaches the target): the stop wins (BT-04, conservative). A bar that opens at or above the target is a target gap even if its low is below the stop, because the open is the first price of the bar.

The fill bar is judged like any later bar (its low and high are after the fill at its open). A position that is still open after the last bar of the session closes at the last close (`END_OF_DATA` when the session was cut short).

## 2. Live monitor equivalence

The monitor reports a signal, not a fill, so it returns the reason and the bar, never a price.

| Aspect | Backtest | Live monitor | Equivalent? |
|---|---|---|---|
| Per-bar rule | `evaluate_bar_exit` | `evaluate_bar_exit` | Yes, same function |
| Bars considered | from the fill bar (starts at the fill) | bars starting at or after `entry_at` | Yes for a fill at a bar start. A manual trade entered mid-bar skips that bar, because the time of the fill inside it is unknown |
| Structure exit | pending after the CHoCH bar closes; executed at the next open | reported at the close of the CHoCH bar (`bar_end`) | Same decision. The live signal appears one bar edge earlier because it cannot see the next bar. The backtest can still turn the pending exit into a stop or target gap at that open (row 1 or 2 outranks row 4) |
| Session end | executed at the open of the first bar starting at the exit time | `SESSION_END` when a bar starts at that time, or once the latest bar has ended at or after it | Yes |
| Prices and slippage | modelled | none (decision support, ADR-010) | By design |

## 3. Discrepancies found by the Phase 1 audit (all fixed)

| ID | Finding | Fix | Regression test |
|---|---|---|---|
| P1-a | The monitor tested `low <= stop` first, so a bar that gapped up through the target but dipped below the stop reported `STOP`; the backtest recorded `TARGET_GAP` | The monitor calls `evaluate_bar_exit` | `test_p1_gap_up_through_the_target_with_a_low_below_the_stop_is_a_target_not_a_stop` |
| P1-b | A bar starting at the session-exit time that touched the stop reported `STOP` live and `SESSION_END` in the backtest | Same | `test_p1_a_bar_starting_at_the_session_exit_time_is_session_end_even_if_it_touches_the_stop` |
| P1-c | `evaluate_bar_exit` required both levels, so the monitor kept its own copy of the rule for trades without a stop or target | Both levels are optional in `evaluate_bar_exit` | `test_p1_a_missing_stop_or_target_is_never_hit` |
| P1-d | Nothing tied the two implementations together | A grid test compares `step_position` and `monitor_position` over 7 x 7 x 7 x 7 bar shapes | `test_p1_monitor_and_step_position_agree_on_the_exit_reason_bar_by_bar` |

Checked and found equivalent already: entry-bar treatment, collision rule (stop wins), gap at the open, structure-exit ordering behind the stop on the CHoCH bar.

## 4. Known simplifications (not changed, recorded for Phase 2)

- **D-4 implemented (T-I150, 2026-11-23):** `evaluate_bar_exit` gives the reference price and the slippage model (`app/backtest/slippage.py`) moves it adversely by the percentage of the execution type: entry, stop (incl. gap and collision), target (incl. gap), session end, structure. It is an assumption, never measured. The default for new runs is `adverse-all`; `legacy-stop-only` (entry and stop exits only, which flatters the other exits) is kept for reproducing earlier results and is what code gets when no model is passed. See TRD-06 §5.1. The legacy behaviour is pinned by `test_slippage_is_charged_on_stop_exits_only_characterisation` and `test_without_a_model_the_legacy_behaviour_is_unchanged`; the new one by `test_every_exit_type_fills_adversely_under_adverse_all`. The research simulators in `diagnostics/daily*.py` and `screen.py` keep their own legacy copies so published research reproduces (T-4).
- The live monitor's structure exit uses the CHoCH events of one full analysis of the stored bars; the backtest uses the analysis at each bar. They agree because pivots are usable only from their confirmation bar (no look-ahead, TRD-02), but no test compares the two on real bars yet.
- 5m bars cannot order the high and the low inside a bar (OQ-BT-07), so collisions always go against the trader.
