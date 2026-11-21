# 05 — Support & Resistance Reversal

| Field | Value |
|---|---|
| Strategy id | `support_resistance_reversal` |
| Roadmap position | 05 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `NOT_STARTED` |
| Executable directions | None |
| Ruleset version | None assigned yet (per-strategy rulesets are defined in the specification) |
| Specification approved | Not approved under the [development process](../development/strategy-development-process.md) |
| Starting position (roadmap) | Zone detection exists, requires trade setup |
| Last verified | 2026-11-21 against `main` at `967da8e` |

This page follows the [strategy template](STRATEGY_TEMPLATE.md). The sections below record what exists today. The template sections 1-28 are added when Stage 1 starts; nothing is pre-filled with assumptions.

## Verified current state

- Specification: zones are specified in [TRD-03](../trading/03_SUPPORT_RESISTANCE_RULES.md). No reversal setup is specified. The earlier `SUPPORT_REJECTION` setup belonged to the retired `pa-core` ruleset.
- Code: zone engine in `app/domain/zone_build.py`, `zone_break.py`, `zone_strength.py`, `zones.py`. No reversal setup. The ruleset parameter `setup.rejection_min_wick_ratio` is present but no code reads it.
- Tests: zone tests only. No setup tests or backtests.

## Open issues and dependencies

- Needs a rejection definition (the unused wick-ratio parameter is a possible starting point, not a decision) and its own entry and stop rules. Must differ from Strategy 06.

## Next action

Wait for the Strategy 01 decision, then write the specification.

## Results

No independent backtest, in-sample, out-of-sample or walk-forward result exists for this strategy. See the [experiment registry](../research/experiment-registry.md) (any earlier figures above come from combined runs and are not evidence for this strategy alone).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md)
