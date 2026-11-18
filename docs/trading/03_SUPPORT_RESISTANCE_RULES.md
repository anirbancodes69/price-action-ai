# Support and Resistance Rules

| Field | Value |
|---|---|
| Document ID | TRD-03 |
| Version | 0.2.0 |
| Status | Specification ready for intraday (ADR-014, `pa-intraday 0.1.0`); parameters are hypotheses |
| Owner | Quant / Trading Engine Lead |
| Last updated | 2026-11-17 |
| Related | [TRD-01 Parameter Registry](01_TRADING_METHODOLOGY.md#6-ruleset-parameter-registry-authoritative) · [TRD-02](02_MARKET_STRUCTURE_RULES.md) · [TRD-04](04_SETUP_DETECTION_RULES.md) |

## 1. Purpose

Defines how price zones (support/resistance) are built from confirmed pivots, how their strength is measured, how they are invalidated or flipped, how equal highs/lows are detected, how proximity is calculated, and which **session reference levels** (opening range, previous-day levels) the intraday setups use.

## 2. Principles

- Zones are built **only from confirmed pivots** (`confirmed_at_index ≤ t`). A zone that exists at bar `t` in a backtest must be reconstructable from data up to `t`.
- A zone is a price **band**, not a line.
- Zones are classified as support or resistance **relative to the current close**, not permanently.
- Zones are built on the 5m analysis series (the primary timeframe). Confirmed 15m pivots are added to the same clustering, each tagged with its timeframe, so that 15m swing levels become zones on the 5m chart. A 15m pivot is usable at 5m bar `t` only when its `confirmed_at ≤ bar_end_5m[t]` (TRD-02 §9).

## 3. Zone construction (pivot clustering)

Inputs: all confirmed 5m and 15m swing highs and lows whose bar lies in the last `analysis.lookback_sessions` sessions (default 5), including the current one.

Algorithm (deterministic greedy clustering):

1. Collect pivot prices `p_1..p_n`; sort ascending by price, then by index for ties.
2. Start a cluster with the first pivot. For each next pivot `p`:
   - if `p ≤ cluster_low × (1 + zone.cluster_tolerance_pct/100)` → add to cluster;
   - else close the cluster and start a new one with `p`.
   (Anchoring to `cluster_low` rather than a moving mean prevents chaining a cluster across a wide price range.)
3. For each cluster: `zone_low = min(p)`, `zone_high = max(p)`.
4. Minimum width: if `(zone_high − zone_low) / zone_low < zone.min_width_pct/100`, expand symmetrically around the midpoint to exactly the minimum width.
5. Maximum width: by construction width ≤ cluster tolerance (0.15%) unless `min_width_pct` exceeds it; `zone.max_width_pct` is a guard that rejects malformed parameter sets.
6. `formed_at_index` = max `confirmed_at_index` of the pivots in the cluster that existed when the zone was first formed (first pivot's confirmation for single-pivot zones).

Single-pivot clusters are valid zones with `touches = 1` (strength `WEAK`).

**Example** (tolerance 0.15%, minimum width 0.05%): pivot prices 1480.0, 1481.2, 1482.0, 1490.0.
`1480 × 1.0015 = 1482.22` → 1481.2 and 1482.0 join; 1490 starts a new cluster. Zone A = [1480.00, 1482.00] (width 0.135%, ≥ 0.05% min). Zone B = 1490.00 single pivot → expanded to the minimum width: [1489.63, 1490.37], then rounded outward to the tick (§9).

## 4. Touches and strength

### 4.1 Touch definition

A **touch** is either (a) a confirmed pivot inside the zone (the clustering members), or (b) a later bar `j > formed_at_index` whose range intersects the zone and that is followed by a reaction, defined as: within the next `R` bars price closes outside the zone on the side it came from. Touches of type (b) are only counted once confirmed (after the reaction bars close). Consecutive bars inside the zone count as one touch.

### 4.2 Strength score (0–100)

```
touch_pts    = min(touches, 4) × 15                          (max 60)
reaction_pts = min(max_reaction_pct, 2.0) × 10               (max 20)
               where max_reaction_pct = largest move away from the zone
               within 6 five-minute bars after any touch, as % of zone midpoint
recency_pts  = 20 if the last touch is in the current session
               10 if it is in the previous session
               0  otherwise
htf_pts      = +5 if at least one member pivot is a 15m pivot
flip_pts     = +10 if zone has flipped role (§5.2)
strength     = min(100, touch_pts + reaction_pts + recency_pts + htf_pts + flip_pts)
```

Bucket for UI (`weak` / `moderate` / `strong` in the frontend `PriceZone.strength`):

| Score | Bucket |
|---|---|
| < 40 | WEAK |
| 40–69 | MODERATE |
| ≥ 70 | STRONG |

> **HYPOTHESIS:** weights and buckets are unvalidated (see TRD-01 MP-09).

## 5. Invalidation and role reversal

### 5.1 Break

A zone is **broken downward** when `zone.break_confirm_closes` (default 1 in `pa-intraday`) **consecutive** 5m closes are below `zone_low × (1 − setup.breakout_buffer_pct/100)`. Upward break mirrors with closes above `zone_high × (1 + setup.breakout_buffer_pct/100)`. The break is recorded at the last confirming close (`broken_at_index`).

Buffer ownership: **swing-level** breaks (BOS/CHoCH, TRD-02) use `structure.break_buffer_pct_<tf>`; **zone** breaks and breakouts use `setup.breakout_buffer_pct`. All default to 0.05% in `pa-intraday`.

A single close beyond (with the next close back inside) is a **failed break**; it is counted as a touch and may qualify as a liquidity sweep (TRD-04 §7).

> Note: `pa-core` required 2 closes for a zone break. Intraday, a second 5m close often arrives after the move is gone, so `pa-intraday 0.1.0` uses 1 close, the same as BOS (OQ-SR-01 resolved for this ruleset). The retest requirement of the breakout-retest setup (TRD-04) protects against single-close false breaks.

### 5.2 Role reversal (flip)

After a break, the zone is retained with `role_reversed = true` and its role swaps (broken resistance → support candidate). Breakout-retest setups depend on this ([TRD-04 §5](04_SETUP_DETECTION_RULES.md)). A flipped zone that is broken again in the opposite direction is **retired** (`status = RETIRED`) and no longer drawn.

### 5.3 Zone status values

`ACTIVE`, `BROKEN_FLIPPED`, `RETIRED`.

## 6. Equal highs / equal lows

Two confirmed swing highs `a`, `b` (`b` later) form **equal highs** (EQH) when:

```
|b.price − a.price| / a.price ≤ structure.equal_level_tolerance_pct / 100     (0.10%)
and no close between a.index and b.index exceeded max(a.price, b.price)
and b.index − a.index ≥ 3 bars          (5m bars; both pivots inside the lookback)
```

Equal lows mirror. Equal highs/lows are recorded as **liquidity pools** (`liquidity_events.type = EQUAL_HIGHS | EQUAL_LOWS`) with level = `max` (highs) or `min` (lows). They are inputs to liquidity-sweep detection and are shown as evidence. They are distinct from the `EQH`/`EQL` swing label (which compares only to the immediately preceding pivot) but use the same tolerance.

## 7. Proximity

For close `C = C[T]`:

```
Support zone below price:     distance_pct = (C − zone_high) / C × 100      (≥ 0)
Resistance zone above price:  distance_pct = (zone_low − C) / C × 100       (≥ 0)
Price inside zone:            distance_pct = 0, position = INSIDE
```

`nearest_support` = active/flipped zone with the smallest non-negative distance below; `nearest_resistance` likewise above. A zone is **near** when `distance_pct ≤ zone.proximity_pct` (default 0.50%). Proximity is used by setup detection and for scanner filters ("near support").

## 8. Session reference levels

Besides pivot zones, every run computes these levels for the current session at the 5m close `t`. They are reference levels (single prices), not zones, and setups in TRD-04 use them directly.

| Level | Definition | Known from |
|---|---|---|
| `PDH`, `PDL`, `PDC` | High, low, close of the previous completed session's daily bar | Session open |
| `OR_HIGH`, `OR_LOW` | High and low of the 5m bars ending within the first `session.opening_range_minutes` (TRD-01 §4.1) | Close of the last opening-range bar; before that they do not exist |
| `SESSION_HIGH`, `SESSION_LOW` | Highest high and lowest low of the current session's closed 5m bars up to `t` | First 5m close |

A reference level that coincides with a zone (inside the zone or within `zone.cluster_tolerance_pct` of its bounds) is reported as confluence evidence for that zone; it does not change the zone's bounds.

## 9. Outputs

`price_zones` per run: id (deterministic hash of run + bounds), role (`SUPPORT`/`RESISTANCE` relative to `C[T]`), low, high, touches, strength score and bucket, formed/broken indexes and their `bar_start`, status, member pivot ids with their timeframes. Liquidity pools go to `liquidity_events`. Session reference levels (§8) are part of the run summary.

## 10. Edge cases

| Case | Handling |
|---|---|
| No pivots in lookback | No zones; setups that need zones return `NO_TRADE`. |
| Overlapping zones after expansion | Merge into one zone (union of bounds, sum of touches, recompute strength). |
| Price far from all zones (> 2%) | Zones still output; setups unlikely to qualify. |
| Zone narrower than 2 ticks | Expand outward to at least 2 ticks (tick size from the instrument master). |
| First bars of the session (opening range not yet known) | `OR_HIGH`/`OR_LOW` absent; setups that need them cannot form (TRD-04). |
| Previous session missing (new listing, data gap) | `PDH/PDL/PDC` absent; setups that need them return `NO_TRADE` with reason `MISSING_CONTEXT`. |

## 11. Open questions

| ID | Question |
|---|---|
| OQ-SR-01 | Zone break closes: resolved for `pa-intraday 0.1.0` as 1 close (§5.1); revisit with intraday backtests. |
| OQ-SR-02 | Should daily pivots (not only previous-day levels) be merged into intraday zones? Future scope. |
| OQ-SR-03 | Should touch counting decay with age instead of the recency bonus? |
| OQ-SR-04 | Implementation choices where §3-§6 are silent (T-I34..T-I38): `formed_at_index` is the latest member knowledge index among all members visible at `t` (zones are rebuilt at each `t`); a later touch whose preceding close is inside the zone is skipped; the reaction window for later touches is `pivot.right_bars_5m`; strength weights and buckets (§4.2) are code constants, not registry keys; equal levels use consecutive same-kind 5m pivots only; minimum width is measured against the midpoint; a zone can only be broken in the direction price approaches from (decided from the close of its formation bar; either direction when that close is inside the zone), otherwise every resistance zone would flip as soon as price moved below it. Confirm or amend. |
