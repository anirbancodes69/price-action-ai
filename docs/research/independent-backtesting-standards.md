# Independent Backtesting Standards

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Status | Current ([ADR-018](../adr/ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md)). Extends, and does not replace, [TRD-06](../trading/06_BACKTESTING_METHODOLOGY.md) (BT-01..BT-07) |
| Date | 2026-11-21 |
| Related | [Process](../development/strategy-development-process.md) · [Validation criteria](validation-criteria.md) · [Data limitations](research-data-limitations.md) · [Experiment registry](experiment-registry.md) |

**Build independently. Test independently. Backtest independently. Validate independently.**

## 1. Scope

These standards govern every backtest used to judge an individual strategy. TRD-06 still defines the replay mechanics (closed bars, next-open fills, conservative collisions, session-bounded accounts). This document adds isolation, the two-experiment structure, reporting and run records.

## 2. Isolation rules

Individual backtests run **exactly one strategy**.

### 2.1 Forbidden

In an individual strategy backtest, do not:

1. use another strategy to confirm an entry;
2. use another strategy to suppress an entry;
3. use another strategy to filter trades;
4. use another strategy to improve the win rate;
5. combine trades from different strategies;
6. apply confluence scoring;
7. use adaptive strategy selection or strategy-priority selection;
8. use a shared signal-generation layer that changes an individual strategy's decisions.

### 2.2 Allowed shared infrastructure

Historical data, candle processing and validation, the session calendar, instrument metadata, swing highs and lows, neutral structure calculations (pivots, labels, BOS and CHoCH events as data), data-quality checks, transaction costs, execution simulation, generic risk calculations and reporting.

**Test for sharing.** Shared code may compute a fact (a swing, a structure event, a zone, a session level). It may not decide a trade. If a strategy uses a fact as part of its own entry, stop, target or invalidation, the specification must say so by name. For example, a neutral swing-high detector can be shared, but another strategy's BOS confirmation condition cannot be imported into Liquidity Sweep.

### 2.3 Per-strategy artefacts

Each strategy has its own: backtest configuration, strategy identifier, ruleset version, trade log, equity curve, performance metrics, in-sample report, out-of-sample report, walk-forward report and validation decision. A later combined result never overwrites them.

## 3. Single-strategy run mode

The current engine does not provide isolation by itself (list in [future architecture §3](../development/future-architecture.md#3-gap-between-todays-engine-and-the-target)). Before a strategy's first backtest, the research harness must provide a run mode with these properties, **without changing the behaviour of the live scanner or of other strategies**:

| Requirement | Current hazard to remove |
|---|---|
| Only the strategy's own detector runs | `analyse()` runs every detector |
| Candidates are taken directly, not through primary-signal selection | `choose_signal` ranks across setup types |
| The cross-strategy score does not gate entries | `score.watch_threshold` produces `LOW_SCORE` |
| The 15m context filter is used only if the specification lists it as the strategy's own rule | SD-05 is applied inside every setup |
| Exits are the strategy's own (stop, target, invalidation, session end); a structure exit is used only if specified | The replay exits on a bearish CHoCH for all positions |
| Stop and target come from the strategy's specification | `trade_levels()` is shared with setup-specific branches |

**Isolation proof (required test).** For a strategy S, the candidate list of the single-strategy run must equal the S-only candidates produced when all detectors run together, for the same bars. Record this test in the strategy page.

If the harness cannot yet do this, the experiment is labelled `NOT_ISOLATED` and is not valid evidence for the strategy.

## 4. The two experiments

Both use identical data, exclusions, costs, slippage and execution assumptions, and both are recorded separately.

### 4a. Trade-level quality (independent of portfolio constraints)

Purpose: judge the strategy's entries and exits, without letting position limits or ranking decide which trades exist.

- Every valid candidate becomes a simulated trade, subject only to the strategy's own rules (one per anchor per session, session cutoff) and one open trade per symbol.
- No maximum-positions limit, no daily-loss or streak limit, no capital limit, no score or alphabetical ordering.
- Results in R (net of costs and gross), with a fixed notional or fixed risk unit documented in the run record.

### 4b. Risk and position-sizing model

Purpose: judge the strategy under the project's actual limits (TRD-05).

- Same candidates, now through `calculate_risk` and the account limits: ₹ position cap, risk per trade, open risk, daily loss, loss streak, maximum open positions.
- With one strategy there is no cross-strategy ranking, but several candidates can still compete for slots. The tie-break rule must be documented and deterministic. An alphabetical symbol order is not acceptable as an implicit tie-break; use the candidate time then a seeded or documented rule, and report its effect by re-running with a second rule.
- Record the skipped candidates and the reason (TRD-06 already records skips).

## 5. Execution, costs and reporting

### 5.1 Execution assumptions (shared by all strategies)

- Signal at the close of bar *t*; fill at the open of *t+1* (BT-02). A candidate is not filled if the open gaps through the stop or beyond the gap limit.
- A bar touching both stop and target counts as the stop (BT-04). With no 1m data this is a conservative bound.
- Costs follow the [cost schedule](../trading/06_BACKTESTING_METHODOLOGY.md); costs and slippage are **unverified** (OQ-BT-02) until the owner verifies them, and every report says so.
- **Adverse slippage must be applied consistently to every exit.** Today it is applied to entries and stops only (audit R-2). Until the shared simulator is corrected, the run record states which exits carry slippage.
- The same schedule and slippage apply to every strategy being compared. A strategy report must state the schedule version.
- End-of-data trades are reported, and trade statistics must reconcile with the equity curve (audit R-8).

### 5.2 Metrics (per strategy, per experiment)

Total trades; long trades; short trades; win rate; gross P&L; net P&L; profit factor; expectancy in R (gross and net); average winning trade; average losing trade; maximum drawdown; maximum consecutive wins and losses; average holding period; performance by instrument; by year; by market regime; and transaction-cost impact (total cost, cost per trade, cost as a share of risk).

- A direction the infrastructure does not support is reported as `UNSUPPORTED`, not as zero.
- A timeframe that is not available (1m) is reported as unavailable.
- Market regimes are defined from price action only, **before** the results are viewed, and recorded in the strategy page. The recorded 15m structure state at signal time (`context_15m`) is the interim regime key.
- Report sample sizes beside every ratio. A cell below the minimum count in the [validation criteria](validation-criteria.md) is shown but not interpreted.

### 5.3 Run record

Every run is entered in the [experiment registry](experiment-registry.md) with:

| Field | Content |
|---|---|
| `experiment_id`, date | Unique id, date run |
| `strategy_id`, ruleset version | From the strategy page |
| Experiment type | `4a`, `4b`, in-sample, out-of-sample, walk-forward window, sensitivity, other |
| Purpose | `EXPLORATION`, `VALIDATION`, `HOLDOUT` (TRD-06 §9) |
| Configuration | All parameters, overrides, sizing mode, capital, tie-break rule |
| Code | Git commit of the engine and of the harness |
| Data | Source, universe definition, first and last session, session count, input hash |
| Exclusions | Sessions and instrument-sessions excluded, each with the reason |
| Costs and slippage | Schedule version, slippage and which exits carry it |
| Data-quality issues | Missing bars, gaps and anomalies affecting the run |
| Flags | `survivorship_bias_risk`, `short_history`, `costs_unverified`, `calendar_unverified`, `NOT_ISOLATED`, `UNSUPPORTED_DIRECTION` |
| Result summary | Metrics of §5.2; link to the full report |

The earlier practice of running variants from an unrecorded temporary script is not acceptable: the script or its configuration must be reproducible from the repository (or stored with the report).

## 6. Future combination research

Only after the individual strategies have completed validation may separate research begin:

- **A. Individual strategy results** are the mandatory baseline.
- **B. Fixed strategy combinations** are optional future research.
- **C. Adaptive strategy selection** is future research.

Combined results are reported separately and compared against the individual baselines on comparable data, costs, risk assumptions and periods. A combined system cannot make an individually unprofitable strategy `RESEARCH_VALIDATED`. Combined and adaptive experiments need their own specification before any code is written ([future architecture](../development/future-architecture.md)).

## 7. Data and chronology rules

1. Never randomly shuffle chronological market data.
2. Never tune parameters against the final out-of-sample or holdout segment.
3. Never silently fill missing historical data.
4. Never use incomplete sessions to calculate daily levels.
5. Exclude or correctly model special sessions; record corporate-action exclusions.
6. Do not describe biased results as unbiased evidence ([data limitations](research-data-limitations.md)).
