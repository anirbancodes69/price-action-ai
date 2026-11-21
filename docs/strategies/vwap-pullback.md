# 12 — VWAP Pullback

| Field | Value |
|---|---|
| Strategy id | `vwap_pullback` |
| Roadmap position | 12 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `DEFERRED` |
| Executable directions | None |
| Ruleset version | None assigned yet (per-strategy rulesets are defined in the specification) |
| Specification approved | Not approved under the [development process](../development/strategy-development-process.md) |
| Starting position (roadmap) | Deferred pending methodology approval |
| Last verified | 2026-11-21 against `main` at `967da8e` |

This page follows the [strategy template](STRATEGY_TEMPLATE.md). The sections below record what exists today. The template sections 1-28 are added when Stage 1 starts; nothing is pre-filled with assumptions.

## Verified current state

- Specification: none.
- Methodology: [TRD-01 MP-01](../trading/01_TRADING_METHODOLOGY.md) allows only OHLCV of confirmed candles and no derived indicators. VWAP is volume-weighted and derived, so this strategy is outside the current methodology.
- Code, tests and backtests: none.

## Open issues and dependencies

- Needs an owner decision to change the methodology, recorded as a superseding ADR or an amended MP-01. Until then, no VWAP or indicator may appear in any other strategy.

## Next action

None until the methodology decision is made.

## Results

No independent backtest, in-sample, out-of-sample or walk-forward result exists for this strategy. See the [experiment registry](../research/experiment-registry.md) (any earlier figures above come from combined runs and are not evidence for this strategy alone).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md)
