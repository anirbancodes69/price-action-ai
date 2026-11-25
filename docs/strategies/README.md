# Strategies

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Date | 2026-11-21 |
| Decision | [ADR-018](../adr/ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md) |

One page per strategy in the library. The master tracker, with each stage's status, lives in **one place**: [strategy development roadmap §5](../development/strategy-development-roadmap.md#5-master-strategy-tracker). Do not copy status into other documents; link to it.

## Rule that governs everything here

**Build independently. Test independently. Backtest independently. Validate independently.** A strategy's trades come from its own rules only. No other strategy confirms, suppresses, filters, ranks or combines them. Neutral infrastructure (candles, swings, structure, zones as data, costs, execution, generic risk) is shared. Details: [independent backtesting standards §2](../research/independent-backtesting-standards.md#2-isolation-rules).

## Pages

| # | Strategy | Page | Acceptance status |
|---|---|---|---|
| 01 | Liquidity Sweep / Reversal | [liquidity-sweep-reversal.md](liquidity-sweep-reversal.md) | `DEFERRED` (parked 2026-11-22) |
| 02 | Failed Breakout | [failed-breakout.md](failed-breakout.md) | `DEFERRED` |
| 03 | Trend Following / Pullback | [trend-following-pullback.md](trend-following-pullback.md) | `SPECIFICATION_IN_PROGRESS` |
| 04 | CHoCH Reversal | [choch-reversal.md](choch-reversal.md) | `NOT_STARTED` |
| 05 | Support & Resistance Reversal | [support-resistance-reversal.md](support-resistance-reversal.md) | `NOT_STARTED` |
| 06 | Supply & Demand Trading | [supply-demand.md](supply-demand.md) | `NOT_STARTED` |
| 07 | Range Trading / Mean Reversion | [range-trading.md](range-trading.md) | `NOT_STARTED` |
| 08 | BOS Trading | [bos-trading.md](bos-trading.md) | `NOT_STARTED` |
| 09 | Opening Range Breakout | [opening-range-breakout.md](opening-range-breakout.md) | `SPECIFICATION_APPROVED` (2026-11-23, B0 frozen; code `IMPLEMENTED`, long) |
| 10 | Previous Day High/Low Breakout | [previous-day-high-low-breakout.md](previous-day-high-low-breakout.md) | `IMPLEMENTED` (long) |
| 11 | Breakout & Retest | [breakout-retest.md](breakout-retest.md) | `IMPLEMENTED` (long) |
| 12 | VWAP Pullback | [vwap-pullback.md](vwap-pullback.md) | `DEFERRED` |

`IMPLEMENTED` means code exists on `main`. It does not mean functionally tested, backtested, validated or ready for paper trading.

## Where the rules live

The strategy pages hold the per-strategy specification and results. The trading rules that are already authoritative stay where they are and are linked from the pages: [TRD-01 methodology and parameter registry](../trading/01_TRADING_METHODOLOGY.md), [TRD-02 structure](../trading/02_MARKET_STRUCTURE_RULES.md), [TRD-03 zones](../trading/03_SUPPORT_RESISTANCE_RULES.md), [TRD-04 setups](../trading/04_SETUP_DETECTION_RULES.md), [TRD-05 risk](../trading/05_RISK_MANAGEMENT_RULES.md), [TRD-06 backtesting](../trading/06_BACKTESTING_METHODOLOGY.md), [TRD-08 test vectors](../trading/08_TRADING_ENGINE_VALIDATION.md). When a strategy's specification is approved, the matching TRD section is updated in the same change so that there is one authoritative home per rule.

## How to add or change a strategy page

Use the [template](STRATEGY_TEMPLATE.md) and the [development process](../development/strategy-development-process.md). Change a status only with evidence, and update the tracker in the same change.
