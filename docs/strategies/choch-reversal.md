# 04 — CHoCH Reversal

| Field | Value |
|---|---|
| Strategy id | `choch_reversal` |
| Roadmap position | 04 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `NOT_STARTED` |
| Executable directions | None |
| Ruleset version | None assigned yet (per-strategy rulesets are defined in the specification) |
| Specification approved | Not approved under the [development process](../development/strategy-development-process.md) |
| Starting position (roadmap) | Structure detection exists, requires independent trade setup |
| Last verified | 2026-11-21 against `main` at `967da8e` |

This page follows the [strategy template](STRATEGY_TEMPLATE.md). The sections below record what exists today. The template sections 1-28 are added when Stage 1 starts; nothing is pre-filled with assumptions.

## Verified current state

- Specification: structure events are specified in [TRD-02](../trading/02_MARKET_STRUCTURE_RULES.md). No trade setup is specified.
- Code: CHoCH events are detected in `python-engine/app/domain/structure.py` (`EventType.CHOCH`). They are used only as setup invalidation (`choch_against` in `setups/common.py`) and as the replay's structure exit.
- Tests: structure tests (`tests/trading/test_structure.py`) only. No setup tests or backtests.

## Open issues and dependencies

- Needs entry, confirmation, stop, target and invalidation rules of its own, and a decision on whether it trades in both directions (D-4).

## Next action

Wait for the Strategy 01 decision, then write the specification.

## Results

No independent backtest, in-sample, out-of-sample or walk-forward result exists for this strategy. See the [experiment registry](../research/experiment-registry.md) (any earlier figures above come from combined runs and are not evidence for this strategy alone).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md)
