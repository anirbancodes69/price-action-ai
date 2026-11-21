# Strategy Template

Copy this file's structure into the strategy's own page (`docs/strategies/<name>.md`) at Stage 1. Rules for filling it in:

- Write **only what is known**. Where something is not decided or not measured, write `Not decided` or `Not run`. Do not fill gaps with assumptions.
- Keep **specification** (what the strategy must do) apart from **implemented behaviour** (what the code does). Section 17 records the second; sections 1-16 the first. Where they differ, say so in section 26.
- Every rule is a comparison on named bars and parameters. Define terms; avoid "strong", "clear" or "obvious" unless defined.
- Parameters are named by ruleset key and default; the authoritative registry stays in [TRD-01 §6](../trading/01_TRADING_METHODOLOGY.md#6-ruleset-parameter-registry-authoritative).
- Isolation: list every shared fact the strategy uses (swing, structure event, zone, session level) and state whether the 15m context filter and any structure-based exit are part of **this** strategy's rules ([standards §2](../research/independent-backtesting-standards.md#2-isolation-rules)).
- Results come from the [experiment registry](../research/experiment-registry.md). Link them; do not retype results without the experiment id.

---

# `<NN>` — `<Strategy name>`

| Field | Value |
|---|---|
| Strategy id | `<snake_case id used in configs and reports>` |
| Roadmap position | `<NN>` of 12 ([roadmap](../development/strategy-development-roadmap.md)) |
| Acceptance status | `<status from the process document>` |
| Ruleset version | `<strategy ruleset version, or "none yet">` |
| Specification approved | `<date and approver, or "not approved">` |
| Last updated | `<date>` |

## 1. Strategy overview
What the strategy is, in a few sentences, in the project's price-action vocabulary.

## 2. Strategy objective
What a successful trade looks like and what the strategy is for.

## 3. Trading hypothesis
Why the pattern should have an edge, stated so that a backtest can contradict it. Include what result would count as the hypothesis failing.

## 4. Market conditions
When the strategy applies and when it must stand aside (regime, session phase, volatility described by price action only).

## 5. Instruments
Universe and any exclusions (for example corporate-action lookbacks).

## 6. Timeframes
Setup timeframe, context timeframe, daily inputs.

## 7. Bullish setup
Preconditions and the pattern, as numbered testable rules.

## 8. Bearish setup
The mirror, or `Not specified` / `Informational only`. State the executable status explicitly.

## 9. Entry rules
Trigger, reference price, fill convention (next-bar open, TRD-06 BT-02), entry window, cutoff.

## 10. Confirmation rules
What must close, and where, before the entry is confirmed. Confirmation comes from this strategy's own rules only.

## 11. Stop-loss rules
Structural stop, buffer, tick rounding, minimum and maximum distance.

## 12. Target rules
Target candidates and their order, minimum reward-to-risk, tick rounding.

## 13. Invalidation rules
Conditions that cancel the setup before and after entry, and the session-end rule.

## 14. Configuration parameters
| Key | Default | Range | Used by | Source |
|---|---|---|---|---|

## 15. Dependencies
Shared infrastructure used (named). Any dependency on another strategy is a defect: state `None`.

## 16. Edge cases
Gaps, missing candles, special sessions, duplicate signals, simultaneous anchors, tie-breaks, instruments near a corporate action.

## 17. Implementation details
Module, functions, ruleset version, how each concept in the [process](../development/strategy-development-process.md#21-strategy-interface) maps to code. State what the code does today, including limits.

## 18. Functional test coverage
Which tests cover each item of the [Stage 3 list](../development/strategy-development-process.md#4-functional-testing-standard-stage-3), with file names, and the isolation proof. Mark gaps.

## 19. Independent backtest configuration
Single-strategy run mode, both experiments (4a, 4b), costs, slippage, sizing, data range, exclusions, regime definitions fixed in advance.

## 20. Historical performance
Experiment ids and headline metrics for 4a and 4b (gross, net, R, trades, drawdown), with flags. `Not run` until it exists.

## 21. In-sample results
## 22. Out-of-sample results
## 23. Walk-forward results
Per segment, from the registry, with sample sizes.

## 24. Robustness analysis
Parameter, cost, period and regime sensitivity; overfitting and selection-bias discussion; variants tried.

## 25. Known limitations
Data limits ([list](../research/research-data-limitations.md)) and strategy limits.

## 26. Outstanding issues
Open questions (`OQ-*`), spec-versus-code differences, blockers.

## 27. Acceptance decision
Status, date, rationale, criteria met or failed ([criteria](../research/validation-criteria.md)), owner sign-off, and the [acceptance checklist](../development/strategy-development-process.md#5-acceptance-checklist).

## 28. Future improvements
Proposals only, each with a hypothesis. Nothing here is adopted until it has a ruleset version and an experiment.
