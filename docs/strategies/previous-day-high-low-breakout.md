# 10 — Previous Day High/Low Breakout

| Field | Value |
|---|---|
| Strategy id | `previous_day_high_low_breakout` |
| Roadmap position | 10 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `IMPLEMENTED` |
| Executable directions | Long |
| Ruleset version | None assigned yet (per-strategy rulesets are defined in the specification) |
| Specification approved | Not approved under the [development process](../development/strategy-development-process.md) |
| Starting position (roadmap) | Long implemented; short side requires completion |
| Last verified | 2026-11-21 against `main` at `967da8e` |

This page follows the [strategy template](STRATEGY_TEMPLATE.md). The sections below record what exists today. The template sections 1-28 are added when Stage 1 starts; nothing is pre-filled with assumptions.

## Verified current state

- Specification: [TRD-04 §4 and §4.1](../trading/04_SETUP_DETECTION_RULES.md).
- Code: `python-engine/app/domain/setups/prev_day.py`. `PREV_DAY_HIGH_BREAK` is executable (long). `PREV_DAY_LOW_BREAK` is built but informational.
- Tests: `tests/trading/test_setups_session.py` (shared with Strategy 09).
- Backtests: none independent. 33 trades inside PRE-001 (−0.27R net); 89 inside PRE-003.

## Open issues and dependencies

- Depends on reliable previous-day high and low. The loader derives them from 5m bars, which are wrong in about 9% of sessions after 2026-08-03 (L-3, L-5); daily bars exist only from 2026-01-01. Short side as for Strategy 09.

## Next action

Wait for the Strategy 01 decision. Fix or avoid the previous-day-level data issue first (D-7).

## Results

No independent backtest, in-sample, out-of-sample or walk-forward result exists for this strategy. See the [experiment registry](../research/experiment-registry.md) (any earlier figures above come from combined runs and are not evidence for this strategy alone).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md)
