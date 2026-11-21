# 06 — Supply & Demand Trading

| Field | Value |
|---|---|
| Strategy id | `supply_demand` |
| Roadmap position | 06 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `NOT_STARTED` |
| Executable directions | None |
| Ruleset version | None assigned yet (per-strategy rulesets are defined in the specification) |
| Specification approved | Not approved under the [development process](../development/strategy-development-process.md) |
| Starting position (roadmap) | Zone engine exists, requires trade setup |
| Last verified | 2026-11-21 against `main` at `967da8e` |

This page follows the [strategy template](STRATEGY_TEMPLATE.md). The sections below record what exists today. The template sections 1-28 are added when Stage 1 starts; nothing is pre-filled with assumptions.

## Verified current state

- Specification: none. The trading documents define support and resistance zones from clustered swing pivots; they contain no supply or demand (base and impulse) definition.
- Code: only the S/R zone engine listed under Strategy 05.
- Tests and backtests: none.

## Open issues and dependencies

- Needs a definition that is genuinely different from Strategy 05, otherwise the two are the same strategy and the roadmap entry should be revisited with the owner.

## Next action

Wait for the Strategy 01 decision, then write the specification.

## Results

No independent backtest, in-sample, out-of-sample or walk-forward result exists for this strategy. See the [experiment registry](../research/experiment-registry.md) (any earlier figures above come from combined runs and are not evidence for this strategy alone).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md)
