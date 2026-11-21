# Validation Criteria

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Status | **Thresholds approved by the owner on 2026-11-21 (D-2); the survivorship rule (D-3) is confirmed at Strategy 01 Stage 5** (see the [roadmap](../development/strategy-development-roadmap.md#6-decisions-and-unresolved-dependencies)). Builds on [TRD-08 §6](../trading/08_TRADING_ENGINE_VALIDATION.md) (proposed, OQ-TRD-03) and [TRD-06 §9](../trading/06_BACKTESTING_METHODOLOGY.md) |
| Date | 2026-11-21 |
| Related | [Independent backtesting standards](independent-backtesting-standards.md) · [Process](../development/strategy-development-process.md) · [Data limitations](research-data-limitations.md) |

The thresholds below are **acceptance gates, not performance claims**. They are the starting values from TRD-08 §6 and are not tuned to any result. No strategy has been evaluated against them yet.

## 1. A strategy must not pass on one profitable backtest

Stage 5 needs all of the following for the strategy's own, isolated results.

| Requirement | Method |
|---|---|
| Chronological in-sample and out-of-sample | Split by session date in order (TRD-06 §9: 60% / 20% / 20% in-sample, out-of-sample, holdout). Parameters are explored in-sample only and frozen before the out-of-sample segment |
| Walk-forward | Rolling windows of 120 in-sample and 40 out-of-sample sessions, step 40 (`app/backtest/splits.py`). With about 712 usable sessions this gives about 14 windows |
| Stability across periods | Net expectancy by year, quarter and walk-forward window; no single period supplies the whole result |
| Regime analysis | Net expectancy by pre-registered price-action regime, with sample sizes |
| Parameter sensitivity | Each tunable parameter varied around its value (proposal: ±25% and ±50%); the result must not depend on a single sharp optimum |
| Cost sensitivity | Net result at 0.5×, 1× and 2× the assumed costs, and at slippage 0%, 0.05% and 0.10% |
| Sample size | See §3 |
| Overfitting | The number of variants tried is recorded; a tested variant that was chosen after viewing the same data is reported as selected, not validated |
| Selection bias | Survivorship and period-selection effects stated ([data limitations](research-data-limitations.md)) |
| Gross vs net | Both reported; a strategy whose gross expectancy is not positive cannot be rescued by cost assumptions |

## 2. Segments and the holdout

- In-sample: exploration. Every run is logged.
- Out-of-sample: one-shot validation of the frozen parameter set.
- Holdout: touched once per strategy ruleset version. A second look needs a new ruleset version and is recorded.
- Forward paper log (TRD-07): live, unseen data; required for `PAPER_TRADING_READY`.
- Never tune against the final out-of-sample or holdout segment.

## 3. `RESEARCH_VALIDATED` (proposed)

On the out-of-sample segment, for the strategy's isolated trade-level experiment (4a) **and** the risk-model experiment (4b), all of:

1. ≥ 100 filled trades over ≥ 60 sessions;
2. net expectancy > 0.10 R after the cost schedule in use (labelled `costs_unverified` while unverified);
3. net profit factor > 1.2;
4. maximum drawdown ≤ 2× the in-sample maximum drawdown;
5. positive net expectancy in most walk-forward out-of-sample windows (more than half);
6. positive gross expectancy, and net expectancy that survives 2× costs being no worse than −0.05 R (proposal; shows the result is not an artefact of the cost assumption);
7. no single instrument, month or regime contributes more than half of the net result (proposal);
8. the isolation proof passes (standards §3) and the run records are complete.

The strategy is also marked with every active data-limitation flag. `RESEARCH_VALIDATED` on the survivorship-biased universe means "met the criteria on biased data, an upper bound". It does not mean the strategy is expected to work live.

**Decision D-3** (recommendation agreed 2026-11-21, confirmed at Stage 5): the owner decides whether `RESEARCH_VALIDATED` is allowed with `survivorship_bias_risk` set. TRD-08 §6 item 7 as written requires it to be false, which is not attainable without a point-in-time membership source (OQ-BT-01).

## 4. `PAPER_TRADING_READY` (proposed)

In addition to §3:

1. `survivorship_bias_risk = false`, or the owner explicitly accepts the residual bias in writing;
2. `short_history = false` (at least 120 sessions, preferably 500; TRD-06 §3);
3. verified costs and slippage (OQ-BT-02);
4. a forward paper log of ≥ 40 sessions that does not contradict the out-of-sample result (net expectancy not below 0), per TRD-07;
5. owner approval.

## 5. Improvement rounds

After a failed or inconclusive validation the strategy may be improved ([process §6](../development/strategy-development-process.md#6-when-validation-fails)). Proposal: at most three improvement rounds per strategy before the owner reviews whether to continue or set `VALIDATION_FAILED`. Each round needs a stated hypothesis and is evaluated on data not used to pick the change.

## 6. What is not a validation

- A profitable run on the days the strategy was designed or tuned on.
- A combined-strategy result, however good ([standards §6](independent-backtesting-standards.md#6-future-combination-research)).
- A run flagged `NOT_ISOLATED`.
- A result whose costs were chosen after seeing it.
