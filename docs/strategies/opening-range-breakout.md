# 09 — Opening Range Breakout

| Field | Value |
|---|---|
| Strategy id | `opening_range_breakout` |
| Roadmap position | 09 of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `IMPLEMENTED` |
| Executable directions | Long |
| Ruleset version | None assigned yet (per-strategy rulesets are defined in the specification) |
| Specification approved | Not approved under the [development process](../development/strategy-development-process.md) |
| Starting position (roadmap) | Long implemented; short side requires completion |
| Last verified | 2026-11-21 against `main` at `967da8e` |

This page follows the [strategy template](STRATEGY_TEMPLATE.md). The sections below record what exists today. The template sections 1-28 are added when Stage 1 starts; nothing is pre-filled with assumptions.

## Verified current state

- Specification: [TRD-04 §3](../trading/04_SETUP_DETECTION_RULES.md).
- Code: `python-engine/app/domain/setups/opening_range.py`. Long is executable. The short setup (`SetupDirection.SHORT`) is built but informational; four independent gates stop it being executed (`signal.py`, `levels.py`, `risk/request.py`, `backtest/replay.py`; [audit §D.1](../research/adaptive-strategy-validation/RESEARCH_READINESS.md)). The opening range is the first 15 minutes, width 0.3-2.0%.
- Tests: `tests/trading/test_setups_session.py` (11 tests shared with Strategy 10).
- Backtests: none independent. 13 trades inside the combined run PRE-001 (+0.10R, too few to read).

## Open issues and dependencies

- Completing the short side needs short entry, exit, sizing and replay support (D-4, D-9). The target ladder uses the previous-day high as a candidate, so it is exposed to the previous-day-level data issue (L-5). Session hours matter (L-4).

## Next action

Wait for the Strategy 01 decision.

## Results

No independent backtest, in-sample, out-of-sample or walk-forward result exists for this strategy. See the [experiment registry](../research/experiment-registry.md) (any earlier figures above come from combined runs and are not evidence for this strategy alone).

## Related

[Roadmap and tracker](../development/strategy-development-roadmap.md) · [Process](../development/strategy-development-process.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md)
