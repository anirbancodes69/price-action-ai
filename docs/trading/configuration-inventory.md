# Configuration Inventory

| Item | Value |
|---|---|
| Status | Audited 2026-11-23 against `pa-intraday 0.1.0`..`0.4.0` (Phase 1 P3) |
| Method | Every ruleset key was searched for in `python-engine/app` (literal key, or the built key for `pivot.*` and `structure.break_buffer_pct_*`). Tests keep the result honest: `test_every_key_is_read_by_code_or_declared_dormant`, `test_dormant_keys_are_really_unread` |

## 1. Parameters with no effect (verified)

No parameter was deleted: a released ruleset is immutable. **D-2 approved 2026-11-23:** all three are retired in `pa-intraday 0.5.0` (RESEARCH, output identical to `0.1.0`, tested); released files are unchanged and their hashes are pinned.

| Key | Value | Verdict | Evidence | Needed |
|---|---|---|---|---|
| `score.min_display` | 0 | **Obsolete.** A display floor of 0 hides nothing, so wiring it would change no result | No code, API field or UI reads it; TRD-04 §9 (daily design) is the only definition | Drop in the next ruleset version, or define the display filter |
| `setup.rejection_min_wick_ratio` | 0.5 | **Obsolete.** It belonged to the daily support-rejection setup, which does not exist in the intraday design | No detector reads it; the setup type is retired (`SUPPORT_REJECTION`) | Drop in the next ruleset version |
| `zone.max_width_pct` | 0.5 | **Implementation defect, low impact.** TRD-03 §3 says it is a guard that rejects malformed parameter sets; the guard was never written | No code reads it. Widths are bounded by construction (`cluster_tolerance_pct` 0.15 and `min_width_pct` 0.05 are below 0.5) | Phase 1 added the missing check as a test (`test_zone_width_parameters_are_consistent`); a runtime guard changes no output |

## 2. Parameters that are read

All other keys are read: `analysis.*`, `backtest.slippage_pct`, `exit.*`, `pivot.*`, `risk.*`, `score.watch_threshold`, `session.*`, `setup.*` (including the two research flags and `failed_break_max_bars`), `structure.*`, `zone.*`. The `risk.default_*` keys are read in `RiskProfile.from_params` and in Laravel's `RiskProfileResolver`. `score.watch_threshold` (60) is the minimum PAQS for a signal.

## 3. Hardcoded trading parameters (outside the ruleset)

These are bound to a score or code version (TRD-04 §10 and the specs) and are not registry keys. Changing one changes outputs, so it needs a score or ruleset version.

| Where | Constant | Value |
|---|---|---|
| `setups/scoring.py` | PAQS anchor and confluence points `PDH_ANCHOR_PTS`, `OR_HIGH_ANCHOR_PTS`, `CONFLUENCE_PTS`, `LEVEL_CAP` | 16, 14, 4, 20 |
| `setups/scoring.py` | `TOP_FRACTION`, `OR_WIDTH_OK`, `OR_CONFIRM_WITHIN_BARS`, `PDH_OPEN_GAP_PCT`, `RETEST_WITHIN_BARS`, `SWEEP_MAX_DEPTH_PCT`, `SWEEP_ZONE_MIN_TOUCHES` | 0.7, 0.50 to 1.50, 24, 0.30, 3, 0.30, 2 |
| `setups/scoring.py` `rr_points` | R:R thresholds for points | 2.5 and the ruleset minimum |
| `liquidity.py` | `MIN_BAR_GAP` | 3 bars |
| `zone_strength.py` | `REACTION_BARS` | 6 |
| `risk/request.py` | `MIN_CAPITAL` | 10,000 |
| `backtest/run.py` | `MIN_SESSIONS` | 120 |
| `backtest/costs.py` | `CostSchedule` (brokerage, STT, exchange, SEBI, stamp, GST) | unverified (OQ-BT-02); Groww-published variant exists |
| Laravel `config/trading.php` | `TRADING_CAPITAL_DEFAULT` | 100000 (matches the planning value) |

## 4. Duplicated parameters

| Duplicate | Where | Risk |
|---|---|---|
| Slippage 0.05% | `backtest.slippage_pct` (ruleset) and `SLIPPAGE_PCT` in `diagnostics/daily.py` | Research-only copy; diverges silently if the ruleset changes |
| Pivot width 2 | `pivot.*` (ruleset) and `PIVOT` in `diagnostics/daily_screen.py` | Same |
| Opening range 15 minutes | `session.opening_range_minutes` and `OR_BARS = 3` in `diagnostics/screen.py` | Same |
| Setup-type lists | engine enum, OpenAPI, Laravel validators, frontend map | Fixed in Phase 1 ([api-strategy-contract](../architecture/api-strategy-contract.md)) |
| Risk-per-trade bounds | TRD-01 range 0.1 to 2.0; `RiskProfileController` 0.1 to 2.0; but `RiskCalculateRequest` and `TradePlanRequest` accept up to 5 | **Conflict, see below** |

## 5. Conflicting defaults and ranges

| Item | Conflict | Status |
|---|---|---|
| Per-request `risk_per_trade_pct` | The registry caps risk per trade at 2.0%, the stored profile enforces it, but the two per-request overrides in Laravel allow up to 5% | **D-3 approved 2026-11-23**: reject above 2% (2% is a technical ceiling, default 0.5%). Implemented 2026-11-23: Laravel `lte:2`, engine schema and `calculate_risk` (`RISK_PCT_ABOVE_CEILING`), OpenAPI description |
| Ruleset registry in TRD-01 | Appendix A documents `pa-core` (retired) values that differ from `pa-intraday` (for example `zone.cluster_tolerance_pct` 0.50 vs 0.15). They are struck through and labelled retired, so not a live conflict | Documented |
| `exit.structure_exit_enabled` | true in 0.1.0 and 0.2.0, false in 0.3.0 and 0.4.0 | Deliberate ([ruleset-comparison](ruleset-comparison.md)) |

## 6. Behaviour tests

Configuration behaviour is pinned by: ruleset roles and differences (`tests/test_ruleset_integrity.py`), risk defaults applied end to end (`tests/trading/test_risk_defaults.py`), per-flag detector behaviour (`test_setups_sweep*.py`, `test_setups_failed_breakdown*.py`) and the structure-exit flag in the monitor and replay (`test_position_monitor.py`, `test_replay.py`).
