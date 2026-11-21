# 11 — Breakout & Retest

| Field | Value |
|---|---|
| Strategy id | `breakout_retest` |
| Roadmap position | 11 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `IMPLEMENTED` |
| Executable directions | Long |
| Ruleset version | None assigned yet (per-strategy rulesets are defined in the specification) |
| Specification approved | Not approved under the [development process](../development/strategy-development-process.md) |
| Starting position (roadmap) | Long implemented; historical performance requires investigation |
| Last verified | 2026-11-21 against `main` at `967da8e` |

This page follows the [strategy template](STRATEGY_TEMPLATE.md). The sections below record what exists today. The template sections 1-28 are added when Stage 1 starts; nothing is pre-filled with assumptions.

## Verified current state

- Specification: [TRD-04 §5](../trading/04_SETUP_DETECTION_RULES.md).
- Code: `python-engine/app/domain/setups/breakout_retest.py`. Long only; the short mirror is not implemented (module docstring). Anchors: previous-day high, opening-range high and active zones with at least two touches.
- Tests: `tests/trading/test_setups_retest.py` (5 tests).
- Backtests: none independent. 130 trades inside PRE-001 at −0.48R net, negative in both halves, but it supplied 74% of the combined run's trades while competing for two slots ordered by a non-predictive score.

## Open issues and dependencies

- The adverse record is not attributable to this strategy alone (slot limit, score ordering, shared exits). The investigation is the independent backtest with the isolation standards, not the existing numbers. It is the most expensive strategy to replay because of the zone builds.

## Next action

Wait for the Strategy 01 decision.

## Results

No independent backtest, in-sample, out-of-sample or walk-forward result exists for this strategy. See the [experiment registry](../research/experiment-registry.md) (any earlier figures above come from combined runs and are not evidence for this strategy alone).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md)
