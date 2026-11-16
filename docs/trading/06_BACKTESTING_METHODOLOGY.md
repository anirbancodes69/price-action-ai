# Backtesting Methodology

| Field | Value |
|---|---|
| Document ID | TRD-06 |
| Version | 0.2.0 |
| Status | Specification ready for intraday (ADR-014, `pa-intraday 0.1.0`); cost values must be verified; intraday history depth unverified |
| Owner | Quant / Trading Engine Lead |
| Last updated | 2026-11-17 |
| Related | [TRD-01](01_TRADING_METHODOLOGY.md) · [TRD-04](04_SETUP_DETECTION_RULES.md) · [TRD-05](05_RISK_MANAGEMENT_RULES.md) · [TRD-08](08_TRADING_ENGINE_VALIDATION.md) · [ENG-05 §12 Intraday ingestion](../engineering/05_DATA_INGESTION_SPECIFICATION.md#12-intraday-ingestion-adr-015) |

## 1. Purpose

Defines how a ruleset version is replayed over intraday history to produce trade-level, session-level and portfolio-level results that are free of look-ahead. Backtests, together with forward paper logging (TRD-07), are the **only** mechanism for promoting a parameter from `HYPOTHESIS` to `VALIDATED` (TRD-01 MP-09). A backtest never shows that a strategy is profitable; it shows how the rules would have behaved on the data available, under stated assumptions.

## 2. Principles

| ID | Principle |
|---|---|
| BT-01 | **Bar-by-bar replay.** The engine is invoked as if running live at each 5m close `t`, seeing only bars that ended at or before `t` (5m, 15m and daily). Implementation may use an incremental state machine, but its output must equal a fresh run on the truncated series (TV-NLA tests, TRD-08). |
| BT-02 | **Signal at 5m close `t`, act at the open of the next 5m bar.** No decision uses information from bar `t+1` other than its open price for the fill. |
| BT-03 | **Same code path.** Backtests call the same pure functions as live analysis (`structure`, `zones`, `setups`, `risk`, `execution`). No backtest-only re-implementation of rules. |
| BT-04 | **Conservative ambiguity resolution.** Where 5m OHLC cannot resolve the intrabar order, assume the outcome worse for the trader. |
| BT-05 | **Reproducible.** A run records ruleset version, engine version, cost schedule version, universe definition, data source, timeframes and the content hashes of the input bars. |
| BT-06 | **Results are not advice.** Every result screen carries "Hypothetical, simulated results. Past performance does not indicate future results." |
| BT-07 | **Session-bounded.** The account limits of TRD-05 §8 and the session-end exit apply in the simulation exactly as live. No position is carried overnight. |

## 3. Historical data requirements

| Requirement | Value |
|---|---|
| Timeframes | 5m bars (primary) and 15m bars (context), provider-native; daily bars for previous-day levels |
| Warm-up | `analysis.lookback_sessions` sessions plus `analysis.min_bars_5m` / `analysis.min_bars_15m` before the first tradable session |
| Minimum test span | 120 sessions (about six months), recommended ≥ 500 sessions (about two years) to cover different market regimes. The available depth depends on the provider (OQ-BT-06) |
| Price basis | Unadjusted intraday bars (TRD-01 §4). Instrument-sessions whose lookback contains a split or bonus are excluded from trading |
| Calendar | NSE sessions from `market_calendar`; sessions with incomplete bars are flagged per instrument (ENG-05 §12) |
| Universe | NIFTY 50, point-in-time where membership history is available (§8) |
| Data source | Recorded per run; personal-mode data is usable only by the owning tenant ([ADR-011](../adr/ADR-011-DATA-MODES-AND-TENANT-ISOLATION.md)) |

> **ASSUMPTION:** broker historical APIs limit intraday history per request and overall. Whether two years of 5m and 15m bars for NIFTY 50 can be obtained is **unverified** (OQ-INT-01, OQ-BT-06). Results on shorter history carry a `short_history` flag.

## 4. Execution model

### 4.1 Entry

1. At the close of 5m bar `c`, a setup reaches `ENTRY_CONFIRMED` (TRD-04).
2. Account checks run at close `c` with the state known at that time (TRD-05 §8: session, daily loss, losing streak, open positions; sizing quantities of TRD-05 §3).
3. At the open of bar `c+1` the entry gap rule of TRD-05 §7.1 applies. Fill price = `O[c+1] × (1 + slippage)`.
4. If several entries are confirmed at the same close, they are processed in order of PAQS descending, then symbol ascending; each later one sees the account state including the earlier fills.

### 4.2 Exits

Stop and target are treated as resting orders from the fill bar onward.

| Situation on 5m bar `j ≥ c+1` | Exit |
|---|---|
| `O[j] ≤ stop` (gap through stop) | At `O[j]`, reason `STOP_GAP` |
| `O[j] ≥ target` (gap above target) | At `O[j]`, reason `TARGET_GAP` |
| `L[j] ≤ stop` and `H[j] ≥ target` (**same-bar collision**) | At `stop`, reason `STOP_COLLISION` (BT-04) |
| `L[j] ≤ stop` | At `stop`, reason `STOP` |
| `H[j] ≥ target` | At `target`, reason `TARGET` |
| Structure exit: bearish 5m CHoCH at close `j` while open and `exit.structure_exit_enabled` | At `O[j+1]`, reason `STRUCTURE_EXIT` |
| Session end: bar `j` starts at `session.exit_minutes_before_close` before the close | At `O[j]`, reason `SESSION_END` |
| Data ends inside a session | At the last available close, reason `END_OF_DATA` (flagged, excluded from win rate by default) |

On the **fill bar** `c+1`, after filling at the open, the bar's own low and high are checked against stop and target with the same rules (stop first).

Stop exits apply adverse slippage: `exit = stop × (1 − slippage)`; gap exits fill at the open with adverse slippage as well. Target exits receive no positive slippage.

> 5m bars hide the path inside the bar, so collisions are resolved against the trader. With 1m data the order could be resolved more precisely (OQ-BT-07); until then results are a conservative bound for collision-heavy setups.

### 4.3 Position sizing

Per TRD-05 §3 with the account state of the simulated session. Capital is the fixed starting capital (`sizing_mode = FIXED`, default, for comparability) or the simulated equity at the start of the session (`COMPOUNDING`). Both modes are recorded.

## 5. Transaction costs and slippage

Costs are applied per side through a **dated cost schedule** (`cost_schedule_version`), because Indian statutory charges change over time. The schedule below is for **NSE equity intraday** (positions closed the same day).

| Charge (NSE equity intraday) | Initial modelled value | Applies to |
|---|---|---|
| Brokerage | `min(₹20, 0.03% of order value)` per executed order (typical discount-broker intraday pricing; configurable per broker) | both sides |
| STT | 0.025% of turnover | sell only |
| Exchange transaction charge | 0.00297% of turnover | both sides |
| SEBI turnover fee | ₹10 per crore (0.0001%) | both sides |
| Stamp duty | 0.003% of turnover | buy only |
| GST | 18% on (brokerage + exchange charge + SEBI fee) | both sides |
| DP charge | none (no delivery) | — |
| Slippage | 0.05% adverse per side (`backtest.slippage_pct`) | entry, stop and gap exits |

> **ASSUMPTION — MUST VERIFY:** these values are the author's understanding and may be wrong or outdated. They must be checked against current exchange and broker schedules before any result is presented, and historical schedules should be used for historical periods where available (OQ-BT-02). Slippage 0.05% is a hypothesis.

**Illustration** (the TRD-05 §3.1 trade, 33 shares, buy at ₹1,498.10, sell at the ₹1,529.00 target, assumed schedule): brokerage ₹14.83 + ₹15.14, STT ₹12.61, exchange ₹2.97, SEBI ₹0.10, stamp ₹1.48, GST ₹5.95 → **₹53.08**. Gross P&L ₹1,019.70 (2.40 R) becomes net ₹966.62 (2.28 R) before slippage. On a stopped-out trade the same costs add to the loss.

`net_pnl = gross_pnl − Σ charges`. R-multiples are reported gross and net: `R = net_pnl / initial_risk_amount`.

## 6. Skips and gaps

Entry gaps: TRD-05 §7.1. Exit gaps: §4.2. Every skipped entry is counted by reason (`SKIPPED_GAP_UP`, `SKIPPED_GAP_BELOW_STOP`, `SKIPPED_RR_DEGRADED`, `SKIPPED_SESSION_CUTOFF`, `ACCOUNT_LIMIT`, `MAX_POSITIONS_REACHED`) and reported. A strategy with many skips has an execution-feasibility problem that the headline metrics hide.

## 7. Corporate actions

| Action | Treatment |
|---|---|
| Split / bonus | Intraday bars are unadjusted; an instrument is not traded in sessions whose lookback window contains the ex-date. No position spans an ex-date (no overnight holding). |
| Dividends | Irrelevant intraday (no position held over the record date). |
| Rights, mergers, demergers, symbol change | Instrument excluded for `[ex_date − 5, ex_date + 5]` sessions. Instruments are keyed by internal id + ISIN, not trading symbol. |

Corporate action data source is **unresolved** (OQ-BT-03).

## 8. Survivorship bias and historical universe

- The tradable universe in session `d` = instruments that were NIFTY 50 members on `d` per `universe_memberships` (effective-dated, [ARC-03](../architecture/03_DATABASE_DESIGN.md)).
- Using today's constituent list for past sessions is **forbidden** where membership history exists. If point-in-time membership is unavailable for part of the period, the run is flagged `survivorship_bias_risk = true` and the UI shows a warning banner.
- NIFTY 50 changes rarely, so the bias is smaller than for NIFTY 500, but it is still recorded.

> **UNRESOLVED (OQ-BT-01):** a machine-readable source of historical NIFTY 50 constituents.

## 9. Validation protocol

| Segment | Use | Example split for 500 sessions |
|---|---|---|
| In-sample (IS) | Parameter exploration | first 300 sessions |
| Out-of-sample (OOS) | One-shot validation of the frozen parameter set | next 100 sessions |
| Holdout | Final check before promoting to `VALIDATED`; touched once per ruleset version | last 100 sessions |
| Forward paper log | Live, unseen data (TRD-07) | from the start of I6 |

Rules: parameters are frozen before OOS; a ruleset whose OOS expectancy (net R) is ≤ 0 cannot be promoted; every tried parameter set is logged (`backtest_runs` with `purpose = EXPLORATION`) to make multiple testing visible. **Walk-forward** analysis (rolling 120-session IS / 40-session OOS windows) is run for every candidate ruleset once history allows; a parameter set must be positive in most OOS windows, not only in aggregate.

## 10. Performance metrics

| Metric | Formula |
|---|---|
| Trades | Count of filled trades (excl. `END_OF_DATA` unless toggled) |
| Win rate | `wins / trades` where win = net P&L > 0 |
| Average R (expectancy) | `mean(net R)` |
| Profit factor | `Σ positive net P&L / |Σ negative net P&L|` |
| Max drawdown | Max peak-to-trough decline of the end-of-session equity curve (%, ₹) |
| Session P&L distribution | Mean, median, worst session; % of sessions that hit the daily loss limit; % with a losing-streak block |
| Sharpe (daily) | `mean(session returns) / stdev(session returns) × √252`, risk-free = 0 (documented simplification) |
| Exposure | % of session time with ≥ 1 open position |
| Average time in trade | Mean minutes from fill to exit |
| Exit mix | Shares of `STOP`, `TARGET`, `STOP_COLLISION`, `SESSION_END`, `STRUCTURE_EXIT`, gaps |
| Skips by reason | Counts of §6 reasons |
| Cost drag | `Σ charges / Σ gross |P&L|`; net R minus gross R |
| Breakdown | Per setup type, per time of day (half-hour buckets), per 15m context state, per month |

Metrics with fewer than 30 trades or 60 sessions are shown with a "low sample" warning.

## 11. Outputs

`backtest_runs` (config, versions, status, metrics JSON, flags) and `backtest_trades` (every simulated trade including skipped entries with reason, signal/entry/exit timestamps, costs, R). The equity curve is stored as a compact end-of-session series in the run row (`equity_curve` JSONB) — recomputable, not authoritative.

## 12. Open questions

| ID | Question |
|---|---|
| OQ-BT-01 | Source of point-in-time NIFTY 50 membership history. |
| OQ-BT-02 | Source and maintenance of current and historical intraday charge schedules (per broker). |
| OQ-BT-03 | Corporate-action data source. |
| OQ-BT-04 | Resolved: dividends are irrelevant for intraday positions. |
| OQ-BT-05 | Promotion thresholds (proposed in TRD-08 §6). |
| OQ-BT-06 | How much 5m/15m history can the provider supply for NIFTY 50 (depth, per-request limits, gaps)? Determines the achievable test span. |
| OQ-BT-07 | Use 1m bars to resolve same-bar stop/target collisions instead of the conservative rule? |
