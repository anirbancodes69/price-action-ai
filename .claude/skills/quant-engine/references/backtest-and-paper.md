# Backtesting and paper-trade simulation checklist

Load this only for work in `app/backtest/`, `app/paper/`, `domain/execution.py` or `backtest_runs`/`paper_trades`. Authority: [TRD-06](../../../../docs/trading/06_BACKTESTING_METHODOLOGY.md), [TRD-07](../../../../docs/trading/07_PAPER_TRADING_SPECIFICATION.md), [TRD-05 §7](../../../../docs/trading/05_RISK_MANAGEMENT_RULES.md#71-entry-gap-rule-next-5m-bar). Nothing here is implemented yet (milestone I8 for backtesting; paper processing with I6). Intraday rules: ADR-014.

## Must hold

| Requirement | Section |
|---|---|
| Bar-by-bar replay. Incremental state must equal a fresh run on the truncated series | TRD-06 BT-01, TV-NLA |
| Signal at 5m close `t`, fill at the next 5m open. Nothing else from `t+1` is used for the decision; 15m context only from closed 15m bars | BT-02, TRD-02 §9 |
| Same domain code path as live analysis | BT-03 |
| Conservative ambiguity: when OHLC cannot resolve intrabar order, assume the worse outcome | BT-04 |
| Same-candle stop and target collision exits at the stop (`STOP_COLLISION`). On the fill bar, check the stop first | TRD-06 §4.2 |
| Gap through stop or above target exits at the open. Entry gaps follow the TRD-05 §7.1 skip rules and count skips by reason | TRD-06 §4.2, §6 |
| Session-bounded: account limits (daily loss, losing streak, open positions, open risk) apply per simulated session; session-end exit; nothing carried overnight | TRD-06 BT-07, TRD-05 §8 |
| Adverse slippage on entries and stop exits. No positive slippage on targets | TRD-06 §4.2, §5 |
| Transaction costs come from a **dated, versioned cost schedule**. Values are unverified (OQ-BT-02) and must be checked before results are shown | TRD-06 §5 |
| Simultaneous entries are ordered by PAQS descending, then symbol ascending. Portfolio checks use only positions known at close `c` | TRD-06 §4.1 |
| Universe in session `d` = point-in-time NIFTY 50 membership from `universe_memberships`. Today's list for past sessions is forbidden where history exists; otherwise set `survivorship_bias_risk = true` | TRD-06 §8 |
| Corporate actions: intraday bars are unadjusted; skip instrument-sessions whose lookback contains a split/bonus | TRD-06 §7 |
| Validation: IS / OOS / holdout by sessions, walk-forward windows, forward paper log. Parameters frozen before OOS. Log every tried parameter set | TRD-06 §9 |
| Reproducibility record: ruleset version, engine version, cost schedule version, universe, data source, input-candle hash | BT-05 |
| PERSONAL-mode data is usable only by the owning tenant | ADR-011 |
| Every result surface says results are hypothetical | BT-06 |
| Proposed plans, paper trades and actual trades are separate entities and tables | TRD-07 §2, C-11 |

## Required tests

TRD-08 §3.6 (gaps, collisions, session end, costs), §3.6a (paper processing), §3.7 (universe and survivorship), §3.8 (no look-ahead). Add a reproducibility test: the same run inputs produce identical trades, metrics and hash.
