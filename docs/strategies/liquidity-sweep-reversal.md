# 01 — Liquidity Sweep / Reversal

| Field | Value |
|---|---|
| Strategy id | `liquidity_sweep_reversal` |
| Roadmap position | 01 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `IMPLEMENTED` |
| Executable directions | Long |
| Ruleset version | None assigned yet (per-strategy rulesets are defined in the specification) |
| Specification approved | Not approved under the [development process](../development/strategy-development-process.md) |
| Starting position (roadmap) | Implemented (long), requires validation |
| Last verified | 2026-11-21 against `main` at `967da8e` |

This page follows the [strategy template](STRATEGY_TEMPLATE.md). The sections below record what exists today. The template sections 1-28 are added when Stage 1 starts; nothing is pre-filled with assumptions.

## Verified current state

- Specification: [TRD-04 §7](../trading/04_SETUP_DETECTION_RULES.md) (`LIQUIDITY_SWEEP_REVERSAL`), with open questions OQ-SD-07 (scoring of non-zone anchors) and OQ-SD-08 (implementation choices). Test vectors TV-SET-19..28 in [TRD-08](../trading/08_TRADING_ENGINE_VALIDATION.md).
- Code: `python-engine/app/domain/setups/liquidity_sweep.py`, merged in PR #66 (T-I141). Enabled only by `setup.liquidity_sweep_enabled` in ruleset `pa-intraday 0.2.0`; `0.1.0` does not contain the key, so the setup is off there. Long only. Levels: unbroken 5m and 15m swing lows, `EQUAL_LOWS` pools, support zones, PDL, OR low. Same-bar and two-bar reclaim; invalidation `SWEEP_FAILED`.
- Tests: 13 tests in `python-engine/tests/trading/test_setups_sweep.py`, including a no-look-ahead test on truncated data. They have not been checked against the full Stage 3 list.
- Backtests: none. No run of ruleset 0.2.0 exists in the [registry](../research/experiment-registry.md); the only real-bar use was a one-day smoke check (T-I141).

## Open issues and dependencies

- Isolation hazards for this strategy: `htf_blocks=False` already removes the 15m context filter for it (SD-05 exception, the score penalises instead); the shared `trade_levels()` supplies its target ladder; the shared score and primary-signal selection would decide whether its candidate becomes a signal.
- Short side is not implemented or executable anywhere in the stack.
- Data: the `PDL` and `OR_LOW` anchors depend on reliable previous-day levels and session hours ([limitations](../research/research-data-limitations.md) L-4, L-5).

## Next action

**Audit, complete, test and independently validate** (the next authorised task). Start with the Stage 1 specification review: resolve OQ-SD-07 and OQ-SD-08, decide D-5 (context filter and score in isolated runs), have the specification approved, then build the single-strategy run mode (D-8) before any backtest.

## Results

No independent backtest, in-sample, out-of-sample or walk-forward result exists for this strategy. See the [experiment registry](../research/experiment-registry.md) (any earlier figures above come from combined runs and are not evidence for this strategy alone).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md)
