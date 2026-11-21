# 02 — Failed Breakout

| Field | Value |
|---|---|
| Strategy id | `failed_breakout` |
| Roadmap position | 02 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `NOT_STARTED` |
| Executable directions | None |
| Ruleset version | None assigned yet (per-strategy rulesets are defined in the specification) |
| Specification approved | Not approved under the [development process](../development/strategy-development-process.md) |
| Starting position (roadmap) | Partially detected, requires independent implementation |
| Last verified | 2026-11-21 against `main` at `967da8e` |

This page follows the [strategy template](STRATEGY_TEMPLATE.md). The sections below record what exists today. The template sections 1-28 are added when Stage 1 starts; nothing is pre-filled with assumptions.

## Verified current state

- Specification: none.
- Code: no setup type. The string `FAILED_BREAKOUT` exists only as an end reason inside Breakout-Retest (`python-engine/app/domain/setups/breakout_retest.py`, a close below the broken zone). `SWEEP_FAILED` in the sweep setup is a different invalidation. This is not a trade setup.
- Tests and backtests: none.

## Open issues and dependencies

- Needs its own definition of the breakout that fails, the reversal trigger, stop, target and the opposite-direction question. It must not reuse the Breakout-Retest code path as a filter.

## Next action

Wait for the Strategy 01 decision, then write the specification.

## Results

No independent backtest, in-sample, out-of-sample or walk-forward result exists for this strategy. See the [experiment registry](../research/experiment-registry.md) (any earlier figures above come from combined runs and are not evidence for this strategy alone).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md)
