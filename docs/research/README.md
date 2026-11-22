# Research

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Date | 2026-11-21 |

How PriceAction AI strategies are researched and validated. The method is fixed by [ADR-018](../adr/ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md): **build, test, backtest and validate every strategy independently, one at a time.** Strategy mixing is prohibited during individual research.

| Document | Content |
|---|---|
| [Independent backtesting standards](independent-backtesting-standards.md) | Isolation rules, single-strategy run mode, the two experiments, metrics, run records, future combination research |
| [Validation criteria](validation-criteria.md) | Robustness requirements and the proposed thresholds for `RESEARCH_VALIDATED` and `PAPER_TRADING_READY` |
| [Research data limitations](research-data-limitations.md) | Known data and infrastructure limits, required handling and flags |
| [Framework diagnosis plan](framework-diagnosis-plan.md) | Pre-registered tests of why every rule set loses before costs (2026-11-22) |
| [Framework diagnosis report](framework-diagnosis-report.md) | Results of the diagnosis: friction, not the entries or the machinery, explains the loss (2026-11-22) |
| [Gate 0 plan (daily)](gate0-daily-diagnosis-plan.md) | Draft pre-registration: framework diagnosis on daily data under delivery costs, before any daily strategy (ADR-019, 2026-11-23, not approved) |
| [Gate 0 report (daily)](gate0-daily-diagnosis-report.md) | Result: daily baseline about zero net at wide stops, friction 0.30R to 0.12R, data defects handled (2026-11-23) |
| [Fast screening protocol](fast-screening-protocol.md) | Approved pre-registration: a fixed family of 13 variants screened cheaply against random-entry controls, then confirmed on other days (2026-11-23) |
| [Fast screening report](fast-screening-report.md) | Screen result: no variant promoted; breakout entries worse than random (2026-11-23) |
| [Experiment registry](experiment-registry.md) | Every experiment, including failed variants and the pre-framework combined runs |
| [Research readiness audit](adaptive-strategy-validation/RESEARCH_READINESS.md) | Evidence behind the limitations (2026-11-21) |
| [Backtest logs](../trading/backtests/) | Full reports of individual runs |
| [TRD-06 Backtesting methodology](../trading/06_BACKTESTING_METHODOLOGY.md) | Replay mechanics (BT-01..BT-07), costs, metrics, splits |

Where the research documents and TRD-06 overlap, TRD-06 owns the replay mechanics and the research documents own isolation, validation and recording. For the development process see [strategy development process](../development/strategy-development-process.md); for status see the [master tracker](../development/strategy-development-roadmap.md#5-master-strategy-tracker).

Everything on this page concerns hypothetical, simulated results. Past performance does not indicate future results (TRD-06 BT-06).
