# Risk Management Rules

| Field | Value |
|---|---|
| Document ID | TRD-05 |
| Version | 0.2.0 |
| Status | Specification ready for intraday (ADR-014, `pa-intraday 0.1.0`); defaults are hypotheses (OQ-TRD-04) |
| Owner | Quant / Trading Engine Lead |
| Last updated | 2026-11-17 |
| Related | [TRD-01 Parameter Registry](01_TRADING_METHODOLOGY.md#6-ruleset-parameter-registry-authoritative) · [TRD-01 §4.1 Sessions](01_TRADING_METHODOLOGY.md#41-session-conventions) · [TRD-04 Levels](04_SETUP_DETECTION_RULES.md#8-levels) · [TRD-06 Backtesting](06_BACKTESTING_METHODOLOGY.md) · [TRD-07 Paper Trading](07_PAPER_TRADING_SPECIFICATION.md) · [ARC-04 Risk API](../architecture/04_API_SPECIFICATION.md#81-risk) |

## 1. Purpose and principles

Defines deterministic position sizing, per-trade validation and **account-level intraday limits** for trade plans, paper trades and backtests.

| ID | Principle |
|---|---|
| RM-01 | Risk calculations are pure functions in the Python engine (`risk` module). Laravel calls them; the frontend may show a **preview** but the persisted values always come from the engine. |
| RM-02 | Never computed, modified or suggested by an LLM. |
| RM-03 | Long only in the MVP. Any request with `direction = SHORT` is rejected with `SHORT_NOT_SUPPORTED` (C-12, ADR-014). |
| RM-04 | Every plan must have a stop-loss below entry. No stop ⇒ no plan. |
| RM-05 | Rounding is always conservative: quantity down, stop down, target down, long entry up. |
| RM-06 | Monetary arithmetic uses `Decimal`; INR amounts are stored as `NUMERIC(14,2)`. |
| RM-07 | **Account limits come first.** Before a plan is sized, the account-level limits of §8 are checked for the plan's book. A breached limit blocks the plan; it is not a warning. |
| RM-08 | **Intraday only.** Plans and positions belong to one session. No plan after the entry cutoff; every position is exited by the session-end exit (TRD-01 §4.1). |
| RM-09 | **A stop is not a guaranteed price.** Simulations exit at the stop with adverse slippage, or at the bar open when price gaps through it (§7.2). The UI says so wherever it shows "maximum loss". |
| RM-10 | Broker intraday leverage is never used for sizing: position value ≤ the user's own available capital. |

## 2. Inputs

| Input | Source | Example (owner's planning values, HYPOTHESIS) |
|---|---|---|
| `capital` | Risk profile `trading_capital`, or paper account capital | ₹1,00,000 |
| `risk_pct` | Risk profile `risk_per_trade_pct` (default `risk.default_risk_per_trade_pct`) | 0.5% (₹500) |
| `max_position_value` | Risk profile (default `risk.default_max_position_value`) | ₹50,000 |
| `daily_loss_limit` | Risk profile, % of capital (default `risk.default_daily_loss_limit_pct`) | 1.5% (₹1,500) — placeholder |
| `max_consecutive_losses` | Risk profile (default `risk.default_max_consecutive_losses`) | 3 — placeholder |
| `max_open_positions` | Risk profile (default `risk.default_max_open_positions`) | 2 — placeholder |
| `max_open_risk` | Risk profile, % of capital (default `risk.default_max_open_risk_pct`) | 1.0% (₹1,000) — placeholder |
| `entry`, `stop`, `target` | Analysis levels (TRD-04 §8) or user-edited plan values (validated) | 1,498.10 / 1,485.25 / 1,529.00 |
| `tick_size`, `lot_size` | Instrument master (provider-sourced; never hard-coded; NSE EQ lot = 1) | 0.05 / 1 |
| Account state | Derived for the plan's book and session (§8.1) | — |
| Session clock | `market_calendar` and the bar close of the request | — |

The "placeholder" values are engineering defaults pending the owner's confirmation (OQ-TRD-04). All values come from the registry in TRD-01 §6 and are user-overridable within its ranges.

## 3. Position sizing algorithm

```
risk_budget        = capital × risk_pct / 100
risk_per_share     = entry − stop                                         (must be > 0)
qty_risk           = floor(risk_budget / risk_per_share)
qty_capital        = floor(available_capital / entry)
                     where available_capital = capital − Σ cost basis of open positions in this book
qty_position_cap   = floor(max_position_value / entry)
remaining_open     = capital × max_open_risk_pct / 100 − open_risk
qty_open_risk      = floor(max(remaining_open, 0) / risk_per_share)
remaining_daily    = daily_loss_limit − day_loss_used                       (§8.1)
qty_daily_loss     = floor(max(remaining_daily, 0) / risk_per_share)
qty                = min(qty_risk, qty_capital, qty_position_cap, qty_open_risk, qty_daily_loss)
qty                = floor(qty / lot_size) × lot_size
actual_risk        = qty × risk_per_share
position_value     = qty × entry
binding_constraint = name of the term that produced the minimum
```

If `qty < 1` the plan is rejected with the reason of the binding constraint: `RISK_BUDGET_TOO_SMALL`, `INSUFFICIENT_CAPITAL`, `POSITION_CAP`, `OPEN_RISK_LIMIT_REACHED` or `DAILY_LOSS_LIMIT_REACHED`.

**Interaction of the cap and the risk budget.** With ₹500 risk and a ₹50,000 cap, the cap binds whenever the stop is closer than `risk_budget / max_position_value = 1%` of the entry. Many intraday stops are tighter than that, so the actual risk per trade is often **below** ₹500. That is intended (the cap limits exposure) and the API reports it through `binding_constraint`.

### 3.1 Worked example (INR)

The opening range breakout of TRD-04 §3: capital ₹1,00,000; risk 0.5%; entry ₹1,498.10; stop ₹1,485.25; target ₹1,529.00; cap ₹50,000; no open positions; no loss today; open-risk limit 1.0%; daily loss limit 1.5%.

| Step | Calculation | Result |
|---|---|---|
| Risk budget | 1,00,000 × 0.5% | ₹500.00 |
| Risk per share | 1,498.10 − 1,485.25 | ₹12.85 |
| qty_risk | floor(500 / 12.85) | 38 |
| qty_capital | floor(1,00,000 / 1,498.10) | 66 |
| qty_position_cap | floor(50,000 / 1,498.10) | 33 |
| qty_open_risk | floor(1,000 / 12.85) | 77 |
| qty_daily_loss | floor(1,500 / 12.85) | 116 |
| **qty** | min(...) | **33** (binding: `POSITION_CAP`) |
| Actual risk | 33 × 12.85 | ₹424.05 (0.42% of capital) |
| Position value | 33 × 1,498.10 | ₹49,437.30 |
| R:R | (1,529.00 − 1,498.10) / 12.85 | 2.40 |

The API returns every intermediate quantity so the UI can explain why the size is smaller than the risk budget allows.

### 3.2 Example with the daily loss limit binding

Same trade, but the book has already realised a net loss of ₹1,200 today and has no open position. `day_loss_used = 1,200`, `remaining_daily = 1,500 − 1,200 = 300`, `qty_daily_loss = floor(300 / 12.85) = 23`. qty = 23 (binding: `DAILY_LOSS`); actual risk 23 × 12.85 = ₹295.55, so a full stop-out keeps the day's loss within ₹1,500 before slippage and costs.

## 4. Stop-loss validation

| Rule | Condition | Error |
|---|---|---|
| Stop below entry | `stop < entry` | `STOP_NOT_BELOW_ENTRY` |
| Minimum distance | `entry − stop ≥ max(2 × tick_size, entry × risk.min_stop_distance_pct / 100)` (0.15%) | `STOP_TOO_TIGHT` |
| Maximum distance | `(entry − stop) / entry × 100 ≤ risk.max_stop_distance_pct` (2.0%) | `STOP_TOO_WIDE` |
| Structural stop override | The user may move the stop **further away** than the engine stop. Moving it **closer** is allowed (within the minimum distance) but marks the plan `levels_overridden = true` and records the engine stop for comparison. | warning `STOP_TIGHTER_THAN_STRUCTURE` |

The minimum distance exists because a stop inside normal 5m noise is likely to be hit by chance and slippage dominates it.

## 5. Risk/reward validation

```
rr = (target − entry) / (entry − stop)
```

- `target > entry` else `TARGET_NOT_ABOVE_ENTRY`.
- `rr ≥ effective_min_rr`, where `effective_min_rr = max(risk.min_rr, user.min_rr)` (default 2.0). Below ⇒ `RR_BELOW_MINIMUM` (hard error for plan creation from an engine setup; the user cannot lower the bar below the ruleset value).

Example: entry 412.30, stop 409.60, target 417.20 → rr = 4.90 / 2.70 = 1.81 → rejected.

## 6. Price and quantity rounding

| Value | Rounding |
|---|---|
| Entry (long) | Up to the next tick: `ceil(entry / tick) × tick` |
| Stop | Down: `floor(stop / tick) × tick` |
| Target | Down: `floor(target / tick) × tick` |
| Quantity | Down to whole lots |
| INR amounts | 2 decimals, `ROUND_HALF_UP` for display/storage of computed amounts |

> **ASSUMPTION:** NSE tick sizes vary by price band and have been revised over time. Tick size is read per instrument from the provider's instrument master and snapshotted (`instrument_snapshots`). **Verify against current NSE circulars before go-live (OQ-RM-03).**

## 7. Entry and exit execution rules

### 7.1 Entry gap rule (next 5m bar)

Applied when simulating a fill at the open `O` of the 5m bar after `ENTRY_CONFIRMED` (paper trading and backtesting; shown as guidance for manual execution).

| Case | Condition | Outcome |
|---|---|---|
| Normal | `stop < O ≤ entry_ref × (1 + risk.max_entry_gap_pct/100)` | Fill at `O` (plus slippage, TRD-06 §5) |
| Moved away | `O > entry_ref × (1 + risk.max_entry_gap_pct/100)` | No fill — `SKIPPED_GAP_UP` |
| Through stop | `O ≤ stop` | No fill — `SKIPPED_GAP_BELOW_STOP` |
| RR degraded | Fill price gives `(target − O)/(O − stop) < effective_min_rr` | No fill — `SKIPPED_RR_DEGRADED` |
| After cutoff | The fill bar starts at or after the entry cutoff | No fill — `SKIPPED_SESSION_CUTOFF` |

On a fill, quantity is re-checked: `qty_fill = min(qty_plan, floor(risk_budget / (O − stop)), floor(max_position_value / O))`, and the account limits are re-evaluated. Quantity is **never increased** at fill.

Example: entry_ref ₹1,498.10, max gap 0.30% → limit ₹1,502.59. Open ₹1,503.00 → skipped. Open ₹1,499.00 → risk/share 13.75; rr (1,529.00 − 1,499.00) / 13.75 = 2.18 ≥ 2.0 → filled; qty_fill = min(33, floor(500 / 13.75) = 36, floor(50,000 / 1,499.00) = 33) = 33.

### 7.2 Exit rules

| Exit | Rule |
|---|---|
| Stop | A bar whose low is ≤ the current stop exits at the stop with adverse slippage; if the bar **opens** at or below the stop, the exit is at the open (gap through the stop). |
| Target | A bar whose high is ≥ the target exits at the target (no positive slippage); if it opens at or above the target, at the open. |
| Same-bar collision | Stop and target in one bar → stop (TRD-06 BT-04). |
| Session end | At `session.exit_minutes_before_close` before the close (15:15 on a normal session), any open paper or backtest position exits at the open of the first 5m bar starting at that time (reason `SESSION_END`). For actual positions the app warns from the entry cutoff onwards; the owner exits on the broker platform. |
| Structure exit | If `exit.structure_exit_enabled` and a bearish 5m CHoCH closes while the position is open, exit at the next bar's open (reason `STRUCTURE_EXIT`). |

The broker's own automatic square-off time is not modelled; the session-end exit is set earlier on purpose (OQ-RM-06).

## 8. Account-level limits

Checked in this order before sizing (RM-07); the first failure is returned.

| Rule | Default (registry key) | Check | Error |
|---|---|---|---|
| Session state | — | Session open and the request bar ends before the entry cutoff | `SESSION_CLOSED`, `ENTRY_CUTOFF_PASSED` |
| Daily loss limit | 1.5% of capital (`risk.default_daily_loss_limit_pct`) | `realised_net_loss_today < daily_loss_limit` | `DAILY_LOSS_LIMIT_REACHED` |
| Consecutive losses | 3 (`risk.default_max_consecutive_losses`) | `losing_streak < max_consecutive_losses` | `MAX_CONSECUTIVE_LOSSES_REACHED` |
| Open positions | 2 (`risk.default_max_open_positions`) | open positions + plans in `TRIGGERED` awaiting fill `< max` | `MAX_POSITIONS_REACHED` |
| Open risk | 1.0% of capital (`risk.default_max_open_risk_pct`) | enforced through `qty_open_risk` (§3) | `OPEN_RISK_LIMIT_REACHED` when qty < 1 |
| Position value | ₹50,000 (`risk.default_max_position_value`) | enforced through `qty_position_cap` | `POSITION_CAP` when qty < 1 |

Once the daily loss limit or the consecutive-loss limit is reached, the book stays blocked for the rest of the session. Plans that are not yet filled are cancelled with reason `ACCOUNT_LIMIT` (TRD-07). Limits reset at the start of the next session.

### 8.1 Account state (derived, not stored)

For one book (`PAPER` or `ACTUAL`) and one session date:

```
realised_net_pnl_today = Σ net_pnl of trades in the book closed today (after costs)
realised_net_loss_today = max(0, −realised_net_pnl_today)
open_risk              = Σ over open positions: max(0, entry_fill − current_stop) × qty_open
day_loss_used          = realised_net_loss_today + open_risk
losing_streak          = number of most recent consecutive closed trades today with net_pnl < 0
                         (a trade with net_pnl ≥ 0 resets it to 0)
```

The state is **computed on demand** from the trade tables (Laravel for `GET /api/v1/risk/today`, and passed to the engine for sizing). It is not stored in a table in the MVP, which keeps the single-writer rule simple (this supersedes the `daily_risk_state` table proposed in ARC-03 §2.2). Paper and actual books never share state.

## 9. Capital constraints

- `capital` must be ≥ ₹10,000.
- No margin or leverage: `qty × entry ≤ available_capital` always (RM-10).

## 10. Costs

Intraday charges are a large share of a ₹500 risk. Rough estimate for a ₹50,000 round trip: about ₹40–60 (brokerage, STT on the sell side, exchange and SEBI charges, GST, stamp duty), roughly 10% of 1R. **The schedule is unverified** and lives in TRD-06 §5 (intraday cost schedule).

- The planner shows the estimated round-trip cost and the R:R after costs.
- Costs are excluded from `risk_budget` sizing in `pa-intraday 0.1.0` (OQ-RM-01) but are included in paper and backtest P&L and therefore in `realised_net_pnl_today`.

## 11. Outputs (risk calculation response)

`{qty, risk_budget, risk_per_share, actual_risk, actual_risk_pct, position_value, rr, rr_after_costs, est_round_trip_costs, binding_constraint, constraints: {qty_risk, qty_capital, qty_position_cap, qty_open_risk, qty_daily_loss}, account_state: {realised_net_pnl_today, open_risk, losing_streak, remaining_daily_loss, blocked_reason}, warnings[], errors[], rounding: {entry, stop, target}, ruleset_version}`.

The engine contract (`python-engine/app/schemas/risk.py`) and ARC-04 §8.1 still have the daily shape (`max_heat_pct`, `max_position_pct`); they change to this shape in I1 (task T-I09).

## 12. Open questions

| ID | Question |
|---|---|
| OQ-RM-01 | Should estimated round-trip costs be added to `risk_per_share` for sizing? |
| OQ-RM-02 | Add sector concentration limits? (Not needed with two open positions.) |
| OQ-RM-03 | Confirm NSE tick-size table and its history for backtests. |
| OQ-RM-04 | Resolved by ADR-014: the owner's planning values replace the old UI/onboarding/spec defaults; the remaining values are OQ-TRD-04. |
| OQ-RM-05 | Should the losing streak count only today's trades (chosen) or roll across sessions? |
| OQ-RM-07 | Implementation choices where §3-§8 are silent (T-I46..T-I51): the entry-cutoff check blocks a request whose bar ends after the cutoff; ties between sizing terms resolve in the §3 order; binding names are `RISK_BUDGET`, `CAPITAL`, `POSITION_CAP`, `OPEN_RISK`, `DAILY_LOSS`; extra fill skip codes `SKIPPED_ACCOUNT_LIMIT` and `SKIPPED_SIZE`; exit order is gap at the open, session end, structure exit, then intrabar stop/target; `est_round_trip_costs` and `rr_after_costs` are not computed until the TRD-06 §5 schedule is verified. Confirm or amend. |
| OQ-RM-06 | Broker automatic square-off time for intraday positions — verify, and keep `session.exit_minutes_before_close` earlier than it. |
