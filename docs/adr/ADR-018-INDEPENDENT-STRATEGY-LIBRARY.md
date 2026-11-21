# ADR-018: Independent Strategy Library, Developed and Validated One Strategy at a Time

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-21 |
| Deciders | Product owner |
| Version | 1.0 |
| Related | [ADR-008](ADR-008-DETERMINISTIC-TRADING-ENGINE.md) · [ADR-014](ADR-014-PERSONAL-INTRADAY-WORKSTATION.md) · [TRD-01](../trading/01_TRADING_METHODOLOGY.md) · [TRD-04](../trading/04_SETUP_DETECTION_RULES.md) · [TRD-06](../trading/06_BACKTESTING_METHODOLOGY.md) · [Strategy roadmap](../development/strategy-development-roadmap.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) |

## Context

The engine has four setup types that are detected together, ranked by a shared score and selected one at a time per symbol (`app/domain/analyse.py`, `app/domain/setups/signal.py`). The first backtests ran them together under one position limit. Their results cannot be attributed to a single strategy: the combined run lost money, but which rule lost it, and whether it would win alone, is unknown ([research readiness audit](../research/adaptive-strategy-validation/RESEARCH_READINESS.md) §C.2 R-4). No strategy has shown an edge. The owner wants a library of twelve price-action strategies and, later, an adaptive selector. Building the selector on strategies whose individual quality is unknown would hide failures behind a combination.

## Decision

1. **Official roadmap.** Twelve strategies, in the fixed order of the [roadmap](../development/strategy-development-roadmap.md). The order changes only for a documented technical dependency and with owner approval.
2. **One strategy at a time.** Each strategy goes through the [lifecycle](../development/strategy-development-process.md) (specify, implement, test, backtest, validate, decide) and the owner reviews the outcome before the next one starts.
3. **Strict isolation.** A strategy generates its trades from its own rules only. Individual backtests run exactly one strategy; no other strategy confirms, suppresses, filters, ranks or combines its trades ([standards](../research/independent-backtesting-standards.md) §2). Neutral infrastructure (candles, swings, structure, zones as data, costs, execution, generic risk) is shared.
4. **Independent results.** Each strategy has its own identifier, ruleset version, trade log, equity curve, metrics, IS/OOS/walk-forward reports and decision. Combined results never replace them.
5. **Lifecycle statuses** are separate from each other: implemented is not tested, tested is not backtested, backtested is not validated, validated is not paper-trading ready.
6. **Combinations and adaptive selection are deferred** until the individual library has been validated. They are then reported separately against the individual baselines. A combination cannot make an individually failing strategy `RESEARCH_VALIDATED`.
7. **VWAP Pullback stays on the roadmap as `DEFERRED`.** [TRD-01 MP-01](../trading/01_TRADING_METHODOLOGY.md) (pure price action, no derived indicators) is unchanged. Building it needs a separate, explicit methodology decision (a superseding ADR or an amended MP-01). No other strategy may use VWAP or an indicator.

## Alternatives considered

| Option | Why not |
|---|---|
| Keep validating the combined ruleset (`pa-intraday`) | Attribution is impossible; slot limits and score ranking decide which trades exist. |
| Build the adaptive engine first | It would need strategy-level evidence that does not exist, and would hide individual failures. |
| Develop several strategies in parallel | Reviews and failures would interleave; shared-code changes could silently alter an earlier strategy's results. |

## Consequences

- The existing combined-run results stay on record but count as pre-framework exploration. They are not evidence for any individual strategy ([experiment registry](../research/experiment-registry.md)).
- The current engine's shared layers (primary-signal selection, the quality-score gate, the shared structure-exit, the slot-limited replay) are isolation hazards. Each strategy's task must provide a single-strategy run mode without changing the live engine's behaviour (standards §3).
- Short-side research is blocked by current infrastructure, and the current product decision is long-only actionability (ADR-014, constraint C-12). Simulating shorts for research, and any later change to actionability, need explicit owner decisions (roadmap §6).
- `pa-intraday` ruleset changes still follow TRD-01 and CLAUDE.md §4. Per-strategy rulesets and identifiers are defined in each strategy's specification.
- The validation thresholds of TRD-08 §6 are still proposals (OQ-TRD-03). The [validation criteria](../research/validation-criteria.md) adopt them as the starting point and list what the owner must confirm.
