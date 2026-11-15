# Backtesting Methodology

| Field | Value |
|---|---|
| Document ID | TRD-06 |
| Version | 0.1.0 |
| Status | Specification ready (cost values must be verified; universe-history source unresolved) |
| Owner | Quant / Trading Engine Lead |
| Last updated | 2026-11-15 |
| Related | [TRD-01](01_TRADING_METHODOLOGY.md) · [TRD-04](04_SETUP_DETECTION_RULES.md) · [TRD-05](05_RISK_MANAGEMENT_RULES.md) · [TRD-08](08_TRADING_ENGINE_VALIDATION.md) · [ENG-05 Ingestion](../engineering/05_DATA_INGESTION_SPECIFICATION.md) |

## 1. Purpose

Defines how a ruleset version is replayed over history to produce trade-level and portfolio-level results that are free of look-ahead and, as far as data allows, survivorship bias. Backtests are the **only** mechanism for promoting a parameter from `HYPOTHESIS` to `VALIDATED` (TRD-01 MP-09).

## 2. Principles

| ID | Principle |
|---|---|
| BT-01 | **Bar-by-bar replay.** The engine is invoked as if running live at each bar `t`, seeing only bars `0..t`. Implementation may use an incremental state machine, but its output must equal a fresh run on the truncated series (verified by TV-NLA tests, TRD-08). |
| BT-02 | **Signal at close `t`, act at open `t+1`.** No decision uses bar `t+1` information other than its open price for the fill. |
| BT-03 | **Same code path.** Backtests call the same pure functions as live analysis (`structure`, `zones`, `setups`, `risk`). No backtest-only re-implementation of rules. |
| BT-04 | **Conservative ambiguity resolution.** Where OHLC data cannot resolve intrabar order, assume the outcome worse for the trader. |
| BT-05 | **Reproducible.** A backtest run records ruleset version, engine version, cost schedule version, universe definition, data source and a hash of the input candle set. |
| BT-06 | **Results are not advice.** Every result screen carries "Hypothetical, simulated results. Past performance does not indicate future results." |

## 3. Historical data requirements

| Requirement | Value |
|---|---|
| Timeframe | Daily OHLCV |
| Warm-up | `analysis.lookback_bars` (250) + `analysis.min_bars` before the first tradable date |
| Minimum test span | 3 years of tradable dates (recommended ≥ 8 for regime coverage) |
| Price basis | Split/bonus-adjusted for analysis; adjustment factors retained for fill conversion (§7) |
| Calendar | NSE trading calendar; missing sessions are flagged by ingestion (ENG-05 §7) |
| Delisted instruments | Required for survivorship-free results (§8) |
| Data source | Must be recorded per run; personal-mode data is usable only by the owning tenant ([ADR-011](../adr/ADR-011-DATA-MODES-AND-TENANT-ISOLATION.md)) |

> **ASSUMPTION:** Kite Connect historical API returns daily candles for currently listed instruments with a per-request date-range limit. It is not assumed to cover delisted symbols. Verify limits against current Kite documentation during M2.

## 4. Execution model

### 4.1 Entry

1. At close of bar `c` a setup reaches `ENTRY_CONFIRMED` (TRD-04).
2. Portfolio checks run at close `c` using positions known at that time (max positions, heat, capital; TRD-05 §3, §8).
3. At open `O[c+1]` the gap rules of TRD-05 §7 apply. Fill price = `O[c+1] × (1 + slippage)`.
4. If several entries are confirmed at the same close, they are processed in order of PAQS descending, then symbol ascending.

### 4.2 Exits

Stop and target are treated as resting orders from the fill bar onward.

| Situation on bar `j ≥ c+1` | Exit |
|---|---|
| `O[j] ≤ stop` (gap through stop) | At `O[j]`, reason `STOP_GAP` |
| `O[j] ≥ target` (gap above target) | At `O[j]`, reason `TARGET_GAP` |
| `L[j] ≤ stop` and `H[j] ≥ target` (**same-candle collision**) | At `stop`, reason `STOP_COLLISION` (BT-04) |
| `L[j] ≤ stop` | At `stop`, reason `STOP` |
| `H[j] ≥ target` | At `target`, reason `TARGET` |
| Structure exit: bearish CHoCH at close `j` while open and `exit.structure_exit_enabled` | At `O[j+1]`, reason `STRUCTURE_EXIT` |
| End of test data | At `C[last]`, reason `END_OF_DATA` (flagged, excluded from win-rate by default) |

On the **fill bar** `c+1`, after filling at the open, the bar's own low/high are checked against stop/target with the same rules (stop first).

Stop exits apply adverse slippage: `exit = stop × (1 − slippage)`. Target exits receive no positive slippage.

> `exit.structure_exit_enabled` (default `true`, not user-overridable) is registered in TRD-01 §6. **HYPOTHESIS.**

### 4.3 Position sizing

Per TRD-05 using the simulated equity at close `c` as `capital` (compounding) or fixed starting capital (`sizing_mode = FIXED`, default for comparability). Both modes are recorded.

## 5. Transaction costs and slippage

Costs are applied per side through a **dated cost schedule** (`cost_schedule_version`), because Indian statutory charges change over time.

| Charge (NSE equity delivery) | Initial modelled value | Applies to |
|---|---|---|
| Brokerage | ₹0 (Zerodha equity delivery, configurable for other brokers) | both sides |
| STT | 0.1% of turnover | buy and sell |
| Exchange transaction charge | 0.00297% of turnover | both sides |
| SEBI turnover fee | ₹10 per crore (0.0001%) | both sides |
| Stamp duty | 0.015% of turnover | buy only |
| GST | 18% on (brokerage + exchange charge + SEBI fee) | both sides |
| DP charge | ₹15.34 per scrip per sell day (incl. GST) | sell only |
| Slippage | 0.10% adverse per side (`backtest.slippage_pct`) | entry and stop exits |

> **ASSUMPTION — MUST VERIFY:** the statutory values above reflect the author's understanding and may be outdated. They must be checked against current exchange/broker schedules before any result is presented, and historical schedules should be used for historical periods where available (OQ-BT-02). Slippage 0.10% is a hypothesis.

`net_pnl = gross_pnl − Σ charges`. R-multiples are reported both gross and net: `R = net_pnl / initial_risk_amount`.

## 6. Gaps

Gap handling at entry: TRD-05 §7. Gap handling at exit: §4.2. All skipped entries are counted by reason and reported (a strategy with many `SKIPPED_GAP_UP` events has an execution-feasibility problem that the headline metrics hide).

## 7. Corporate actions

| Action | Treatment |
|---|---|
| Split / bonus | Analysis uses back-adjusted prices (`adj = raw × cumulative_factor`). Open positions spanning the ex-date: quantity × ratio, prices ÷ ratio, P&L unchanged. |
| Dividends | Not adjusted in prices. Cash dividends ignored in 0.1.0 (understates returns slightly; documented). |
| Rights, mergers, demergers | Instrument excluded from trading for the window `[ex_date − 5, ex_date + 5]` bars; open position force-closed at the last close before ex-date (`CORPORATE_ACTION_EXIT`). |
| Symbol change | Instruments are keyed by internal id + ISIN, not trading symbol. |

Corporate action data source is **unresolved** (OQ-BT-03); Kite instrument dumps do not provide a full history.

## 8. Survivorship bias and historical universe

- The tradable universe on date `d` = instruments that were NIFTY 500 members on `d` per `universe_memberships` (effective-dated, see [ARC-03](../architecture/03_DATABASE_DESIGN.md)).
- A symbol enters the tradable set on its inclusion effective date and leaves on its exclusion date; open positions are allowed to run to exit after exclusion.
- Using today's constituent list for past dates is **forbidden**. If point-in-time membership is unavailable for part of the period, the run is flagged `survivorship_bias_risk = true` and the UI shows a warning banner.
- Delisted constituents must have candles; if missing, the run is flagged likewise.

> **UNRESOLVED (OQ-BT-01):** source of historical NIFTY 500 constituents (NSE Indices reconstitution notices are public but not in machine-readable history; licensed vendors provide it). Required before M10.

## 9. Out-of-sample protocol

| Segment | Use | Example split for 2016-01 to 2026-10 |
|---|---|---|
| In-sample (IS) | Parameter exploration | 2016-01-01 → 2021-12-31 |
| Out-of-sample (OOS) | One-shot validation of the frozen parameter set | 2022-01-01 → 2024-12-31 |
| Holdout | Final check before promoting to `VALIDATED`; touched once per ruleset version | 2025-01-01 → latest |

Rules: parameters frozen before OOS; a ruleset whose OOS expectancy (net R) is ≤ 0 cannot be promoted; every tried parameter set is logged (`backtest_runs` with `purpose = EXPLORATION`) to make multiple-testing visible. Walk-forward (rolling 3-year IS / 1-year OOS) is recommended from M10.

## 10. Performance metrics

| Metric | Formula |
|---|---|
| Trades | Count of filled trades (excl. `END_OF_DATA` unless toggled) |
| Win rate | `wins / trades` where win = net P&L > 0 |
| Average R (expectancy) | `mean(net R)` |
| Profit factor | `Σ positive net P&L / |Σ negative net P&L|` |
| Max drawdown | Max peak-to-trough decline of the daily equity curve (%, ₹) |
| CAGR | `(equity_end / equity_start)^(365 / days) − 1` |
| Sharpe (daily) | `mean(daily returns) / stdev(daily returns) × √252`, risk-free = 0 (documented simplification) |
| Exposure | % of days with ≥ 1 open position |
| Avg holding period | Mean bars held |
| Skips by reason | Counts of `SKIPPED_*` |
| Cost drag | `Σ charges / Σ gross |P&L|` |
| Breakdown | Per setup type, per year, per structure state at entry |

Metrics with fewer than 30 trades are shown with a "low sample" warning.

## 11. Outputs

`backtest_runs` (config, versions, status, metrics JSON, flags) and `backtest_trades` (every simulated trade including skipped entries with reason, entry/exit, costs, R). Equity curve stored as a compact daily series in the run row (`equity_curve` JSONB) — recomputable, not authoritative.

## 12. Open questions

| ID | Question |
|---|---|
| OQ-BT-01 | Source of point-in-time NIFTY 500 membership and delisted price history. |
| OQ-BT-02 | Source and maintenance of historical statutory charge schedules. |
| OQ-BT-03 | Corporate-action data source. |
| OQ-BT-04 | Should cash dividends be credited in 0.1.x? |
| OQ-BT-05 | Promotion thresholds (proposed in TRD-08 §6). |
