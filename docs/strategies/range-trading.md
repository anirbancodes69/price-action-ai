# 07 — Range Trading / Mean Reversion

| Field | Value |
|---|---|
| Strategy id | `range_trading` |
| Roadmap position | 07 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `NOT_STARTED` |
| Executable directions | None |
| Ruleset version | None assigned yet (per-strategy rulesets are defined in the specification) |
| Specification approved | Not approved under the [development process](../development/strategy-development-process.md) |
| Starting position (roadmap) | Range classification exists, requires trade setup |
| Last verified | 2026-11-21 against `main` at `967da8e` |

This page follows the [strategy template](STRATEGY_TEMPLATE.md). The sections below record what exists today. The template sections 1-28 are added when Stage 1 starts; nothing is pre-filled with assumptions.

## Verified current state

- Specification: none. [TRD-02 §5.2](../trading/02_MARKET_STRUCTURE_RULES.md) defines the structure state `SIDEWAYS`; [TRD-04 OQ-SD-01](../trading/04_SETUP_DETECTION_RULES.md) asks whether a range setup type should exist.
- Code: `StructureState.SIDEWAYS` in `app/domain/structure.py`. There is no range box, boundary detection or mean-reversion rule. "Range classification" in the roadmap therefore means the structure state only.
- Tests and backtests: none.

## Open issues and dependencies

- Needs a range definition (boundaries, minimum touches, duration), entry at the boundaries, a target at the opposite side or the midpoint, and a failure rule when the range breaks. Mean reversion is a different hypothesis from the project's breakout setups.

## Next action

Wait for the Strategy 01 decision, then write the specification.

## Results

No independent backtest, in-sample, out-of-sample or walk-forward result exists for this strategy. See the [experiment registry](../research/experiment-registry.md) (any earlier figures above come from combined runs and are not evidence for this strategy alone).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md)
