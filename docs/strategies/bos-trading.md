# 08 — BOS Trading

| Field | Value |
|---|---|
| Strategy id | `bos_trading` |
| Roadmap position | 08 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `NOT_STARTED` |
| Executable directions | None |
| Ruleset version | None assigned yet (per-strategy rulesets are defined in the specification) |
| Specification approved | Not approved under the [development process](../development/strategy-development-process.md) |
| Starting position (roadmap) | Structure detection exists, requires independent trade setup |
| Last verified | 2026-11-21 against `main` at `967da8e` |

This page follows the [strategy template](STRATEGY_TEMPLATE.md). The sections below record what exists today. The template sections 1-28 are added when Stage 1 starts; nothing is pre-filled with assumptions.

## Verified current state

- Specification: BOS events are specified in [TRD-02](../trading/02_MARKET_STRUCTURE_RULES.md). No trade setup is specified.
- Code: BOS events in `app/domain/structure.py` (`EventType.BOS`) drive the structure state and are an input to the draft `TREND_CONTINUATION` rule; no BOS setup exists.
- Tests: structure tests only.

## Open issues and dependencies

- Must be specified independently of Strategy 03, which also starts from a BOS.

## Next action

Wait for the Strategy 01 decision, then write the specification.

## Results

No independent backtest, in-sample, out-of-sample or walk-forward result exists for this strategy. See the [experiment registry](../research/experiment-registry.md) (any earlier figures above come from combined runs and are not evidence for this strategy alone).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md)
