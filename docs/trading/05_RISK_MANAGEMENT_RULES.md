# Risk Management Rules

| Field | Value |
|---|---|
| Document ID | TRD-05 |
| Version | 0.1.0 |
| Status | Specification ready (defaults are hypotheses) |
| Owner | Quant / Trading Engine Lead |
| Last updated | 2026-11-15 |
| Related | [TRD-01 Parameter Registry](01_TRADING_METHODOLOGY.md#6-ruleset-parameter-registry-authoritative) · [TRD-04 Levels](04_SETUP_DETECTION_RULES.md#8-levels) · [TRD-07 Paper Trading](07_PAPER_TRADING_SPECIFICATION.md) · [ARC-04 Risk API](../architecture/04_API_SPECIFICATION.md#81-risk) |

## 1. Purpose and principles

Defines deterministic position sizing and risk validation for trade plans, paper trades and backtests.

| ID | Principle |
|---|---|
| RM-01 | Risk calculations are pure functions in the Python engine (`risk` module). Laravel calls them; the frontend may show a **preview** but the persisted values always come from the engine. |
| RM-02 | Never computed, modified or suggested by an LLM. |
| RM-03 | Long only in MVP. Any request with `direction = SHORT` is rejected with `SHORT_NOT_SUPPORTED`. |
| RM-04 | Every plan must have a stop-loss below entry. No stop ⇒ no plan. |
| RM-05 | Rounding is always conservative: quantity down, stop down, target down, long entry up. |
| RM-06 | Monetary arithmetic uses `Decimal`; INR amounts are stored as `NUMERIC(14,2)`. |

## 2. Inputs

| Input | Source | Example |
|---|---|---|
| `capital` | User risk profile (`trading_capital`) or paper account capital | ₹10,00,000 |
| `risk_pct` | Risk profile (`risk_per_trade_pct`, default `risk.default_risk_per_trade_pct` = 1.0) | 1.0% |
| `entry`, `stop`, `target` | Analysis levels (TRD-04 §8) or user-edited plan values (validated) | 1,495.50 / 1,477.00 / 1,560.00 |
| `tick_size` | Instrument master (provider-sourced; never hard-coded) | 0.10 |
| `lot_size` | Instrument master (NSE EQ = 1) | 1 |
| `open_positions` | Paper or actual book (the two books are never mixed) | — |
| `max_open_positions` | Risk profile (default 5) | 5 |
| `max_heat_pct` | Risk profile (default 5.0) | 5.0% |
| `max_position_pct` | Risk profile (default `risk.default_max_position_pct` = 25.0) | 25% |

> `risk.default_max_position_pct` (25%, user-overridable, range 5–100) is registered in TRD-01 §6. **HYPOTHESIS.**

## 3. Position sizing algorithm

```
risk_budget        = capital × risk_pct / 100
risk_per_share     = entry − stop                                 (must be > 0)
qty_risk           = floor(risk_budget / risk_per_share)
qty_capital        = floor(available_capital / entry)
                     where available_capital = capital − Σ cost basis of open positions in this book
qty_position_cap   = floor(capital × max_position_pct / 100 / entry)
remaining_heat     = capital × max_heat_pct / 100 − open_heat
qty_heat           = floor(max(remaining_heat, 0) / risk_per_share)
qty                = min(qty_risk, qty_capital, qty_position_cap, qty_heat)
qty                = floor(qty / lot_size) × lot_size
actual_risk        = qty × risk_per_share
position_value     = qty × entry
binding_constraint = name of the term that produced the minimum
```

If `qty < 1` the plan is rejected with the reason of the binding constraint (`RISK_BUDGET_TOO_SMALL`, `INSUFFICIENT_CAPITAL`, `POSITION_CAP`, `PORTFOLIO_HEAT_EXCEEDED`).

### 3.1 Worked example (INR)

Capital ₹10,00,000; risk 1%; entry ₹1,495.50; stop ₹1,477.00; target ₹1,560.00; no open positions; max position 25%; heat 5%.

| Step | Calculation | Result |
|---|---|---|
| Risk budget | 10,00,000 × 1% | ₹10,000.00 |
| Risk per share | 1,495.50 − 1,477.00 | ₹18.50 |
| qty_risk | floor(10,000 / 18.50) | 540 |
| qty_capital | floor(10,00,000 / 1,495.50) | 668 |
| qty_position_cap | floor(2,50,000 / 1,495.50) | 167 |
| qty_heat | floor(50,000 / 18.50) | 2,702 |
| **qty** | min(...) | **167** (binding: `POSITION_CAP`) |
| Actual risk | 167 × 18.50 | ₹3,089.50 (0.31% of capital) |
| Position value | 167 × 1,495.50 | ₹2,49,748.50 |
| R:R | (1,560 − 1,495.50) / 18.50 | 3.49 |

The API returns all intermediate quantities so the UI can explain why the size is smaller than the risk budget allows.

### 3.2 Example with heat binding

Same trade, but four open positions with total open heat ₹47,500. `remaining_heat = 50,000 − 47,500 = 2,500`; `qty_heat = floor(2,500 / 18.50) = 135`. qty = 135 (binding: `PORTFOLIO_HEAT_EXCEEDED` is *not* raised because qty ≥ 1; binding constraint reported as `PORTFOLIO_HEAT`).

## 4. Stop-loss validation

| Rule | Condition | Error |
|---|---|---|
| Stop below entry | `stop < entry` | `STOP_NOT_BELOW_ENTRY` |
| Minimum distance | `entry − stop ≥ 2 × tick_size` | `STOP_TOO_TIGHT` |
| Maximum distance | `(entry − stop) / entry × 100 ≤ risk.max_stop_distance_pct` (10%) | `STOP_TOO_WIDE` |
| Structural stop override | User may move the stop **further away** than the engine stop (more conservative). Moving it **closer** than the engine stop is allowed but marks the plan `levels_overridden = true` and records the engine stop for comparison. | warning `STOP_TIGHTER_THAN_STRUCTURE` |

## 5. Risk/reward validation

```
rr = (target − entry) / (entry − stop)
```

- `target > entry` else `TARGET_NOT_ABOVE_ENTRY`.
- `rr ≥ effective_min_rr`, where `effective_min_rr = max(risk.min_rr, user.min_rr)` (default 2.0). Below ⇒ `RR_BELOW_MINIMUM` (hard error for plan creation from an engine setup; the user cannot lower the bar below the ruleset value).

Example: entry 412.30, stop 404.10, target 425.00 → rr = 12.70 / 8.20 = 1.55 → rejected.

## 6. Price and quantity rounding

| Value | Rounding |
|---|---|
| Entry (long) | Up to the next tick: `ceil(entry / tick) × tick` |
| Stop | Down: `floor(stop / tick) × tick` |
| Target | Down: `floor(target / tick) × tick` |
| Quantity | Down to whole lots |
| INR amounts | 2 decimals, `ROUND_HALF_UP` for display/storage of computed amounts |

> **ASSUMPTION:** NSE tick sizes vary by price band and have been revised by the exchange over time. Tick size is therefore read per instrument from the provider's instrument master (Kite instruments dump exposes `tick_size`) and snapshotted daily (`instrument_snapshots`). Backtests use the tick size effective on the simulated date where known; otherwise ₹0.05 is used and flagged. **Verify against current NSE circulars before go-live (OQ-RM-03).**

## 7. Entry gap rules

Applied when simulating a fill at the next session open `O` after `ENTRY_CONFIRMED` (paper trading and backtesting; also shown as guidance for manual execution).

| Case | Condition | Outcome |
|---|---|---|
| Normal | `stop < O ≤ entry_ref × (1 + risk.max_entry_gap_pct/100)` | Fill at `O` |
| Gap up too large | `O > entry_ref × (1 + 2.0/100)` | No fill — `SKIPPED_GAP_UP` |
| Gap through stop | `O ≤ stop` | No fill — `SKIPPED_GAP_BELOW_STOP` |
| RR degraded | Fill price `O` gives `(target − O)/(O − stop) < effective_min_rr` | No fill — `SKIPPED_RR_DEGRADED` |

On a fill, quantity is re-checked: `qty_fill = min(qty_plan, floor(risk_budget / (O − stop)))`. Quantity is **never increased** at fill.

Example: entry_ref ₹1,495.50 (confirmation close), max gap 2% → limit ₹1,525.41. Open ₹1,531.00 → skipped. Open ₹1,502.00 → fill; risk/share 25.00; rr (1,560 − 1,502)/25 = 2.32 ≥ 2.0 → filled; qty_fill = min(167, floor(10,000/25)=400) = 167.

## 8. Concurrent exposure and portfolio risk

```
open_heat = Σ over open positions: max(0, (entry_fill − current_stop)) × qty_open
```

(A stop trailed above entry contributes 0.)

| Rule | Default | Check |
|---|---|---|
| Max open positions | `risk.default_max_open_positions` = 5 | Open positions + `ENTRY_CONFIRMED` plans awaiting fill `<` max, else `MAX_POSITIONS_REACHED` |
| Max portfolio heat | `risk.default_max_portfolio_heat_pct` = 5.0% of capital | Enforced via `qty_heat` (§3) |
| Max position size | 25% of capital | Enforced via `qty_position_cap` |
| Sector concentration | *Not enforced in MVP* — displayed only | OQ-RM-02 |

Paper and actual books are evaluated separately. Planned (pending) plans are shown as *planned heat* on `/trade-plans` but do not consume heat until filled.

## 9. Capital constraints

- `capital` must be ≥ ₹10,000 (matches current onboarding/backtest validation in the frontend).
- No margin or leverage: `qty × entry ≤ available_capital` always.
- Transaction costs are excluded from `risk_budget` sizing in 0.1.0 but are included in paper/backtest P&L ([TRD-06 §5](06_BACKTESTING_METHODOLOGY.md)).

## 10. Outputs (risk calculation response)

`{qty, risk_budget, risk_per_share, actual_risk, actual_risk_pct, position_value, rr, binding_constraint, constraints: {qty_risk, qty_capital, qty_position_cap, qty_heat}, warnings[], errors[], rounding: {entry, stop, target}, ruleset_version}`. See [ARC-04](../architecture/04_API_SPECIFICATION.md#81-risk).

## 11. Open questions

| ID | Question |
|---|---|
| OQ-RM-01 | Should estimated round-trip costs be added to `risk_per_share` for sizing? |
| OQ-RM-02 | Add sector concentration limits? |
| OQ-RM-03 | Confirm NSE tick-size table and its history for backtests. |
| OQ-RM-04 | Frontend settings currently show defaults of 6 max positions and 2% portfolio heat; onboarding shows 5 positions. Canonical defaults here are 5 / 5% — confirm with product owner. |
