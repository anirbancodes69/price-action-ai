# 03 — Trend Following / Pullback

| Field | Value |
|---|---|
| Strategy id | `trend_following_pullback` |
| Roadmap position | 03 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `SPECIFICATION_IN_PROGRESS` |
| Executable directions | None |
| Ruleset version | None assigned yet (per-strategy rulesets are defined in the specification) |
| Specification approved | Not approved under the [development process](../development/strategy-development-process.md) |
| Starting position (roadmap) | Specified, requires implementation |
| Last verified | 2026-11-21 against `main` at `967da8e` |

This page follows the [strategy template](STRATEGY_TEMPLATE.md). The sections below record what exists today. The template sections 1-28 are added when Stage 1 starts; nothing is pre-filled with assumptions.

## Verified current state

- Specification: a draft in [TRD-04 §6](../trading/04_SETUP_DETECTION_RULES.md) (`TREND_CONTINUATION`, long, marked "after validation"): 15m `BULLISH`, a 5m bullish BOS, a pullback, a confirmed higher low, a close above the trigger. Not approved under the new process; no short mirror. The earlier `pa-core` `TREND_PULLBACK` is retired.
- Code: none. `SetupType` has no such member.
- Tests and backtests: none.

## Open issues and dependencies

- The draft starts from a 5m BOS, which overlaps Strategy 08 (BOS Trading). The two must be specified so that neither depends on the other.

## Next action

Wait for the Strategy 01 decision, then review and approve the specification.

## Results

No independent backtest, in-sample, out-of-sample or walk-forward result exists for this strategy. See the [experiment registry](../research/experiment-registry.md) (any earlier figures above come from combined runs and are not evidence for this strategy alone).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md)
