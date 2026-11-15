# Support and Resistance Rules

| Field | Value |
|---|---|
| Document ID | TRD-03 |
| Version | 0.1.0 |
| Status | Specification ready (parameters are hypotheses) |
| Owner | Quant / Trading Engine Lead |
| Last updated | 2026-11-15 |
| Related | [TRD-01 Parameter Registry](01_TRADING_METHODOLOGY.md#6-ruleset-parameter-registry-authoritative) · [TRD-02](02_MARKET_STRUCTURE_RULES.md) · [TRD-04](04_SETUP_DETECTION_RULES.md) |

## 1. Purpose

Defines how price zones (support/resistance) are built from confirmed pivots, how their strength is measured, how they are invalidated or flipped, how equal highs/lows are detected, and how proximity is calculated.

## 2. Principles

- Zones are built **only from confirmed pivots** (`confirmed_at_index ≤ t`). A zone that exists at bar `t` in a backtest must be reconstructable from data up to `t`.
- A zone is a price **band**, not a line.
- Zones are classified as support or resistance **relative to the current close**, not permanently.

## 3. Zone construction (pivot clustering)

Inputs: all confirmed swing highs and lows with `index ≥ T − analysis.lookback_bars` (default 250).

Algorithm (deterministic greedy clustering):

1. Collect pivot prices `p_1..p_n`; sort ascending by price, then by index for ties.
2. Start a cluster with the first pivot. For each next pivot `p`:
   - if `p ≤ cluster_low × (1 + zone.cluster_tolerance_pct/100)` → add to cluster;
   - else close the cluster and start a new one with `p`.
   (Anchoring to `cluster_low` rather than a moving mean prevents chaining a cluster across a wide price range.)
3. For each cluster: `zone_low = min(p)`, `zone_high = max(p)`.
4. Minimum width: if `(zone_high − zone_low) / zone_low < zone.min_width_pct/100`, expand symmetrically around the midpoint to exactly the minimum width.
5. Maximum width: by construction width ≤ cluster tolerance (0.50%) unless `min_width_pct` exceeds it; `zone.max_width_pct` is a guard that rejects malformed parameter sets.
6. `formed_at_index` = max `confirmed_at_index` of the pivots in the cluster that existed when the zone was first formed (first pivot's confirmation for single-pivot zones).

Single-pivot clusters are valid zones with `touches = 1` (strength `WEAK`).

**Example** (tolerance 0.50%): pivot prices 1480.0, 1484.5, 1486.0, 1512.0.
`1480 × 1.005 = 1487.40` → 1484.5 and 1486.0 join; 1512 starts a new cluster. Zone A = [1480.00, 1486.00] (width 0.41%, ≥ 0.20% min). Zone B = 1512.00 single pivot → expanded to [1510.49, 1513.51].

## 4. Touches and strength

### 4.1 Touch definition

A **touch** is either (a) a confirmed pivot inside the zone (the clustering members), or (b) a later bar `j > formed_at_index` whose range intersects the zone and that is followed by a reaction, defined as: within the next `R` bars price closes outside the zone on the side it came from. Touches of type (b) are only counted once confirmed (after the reaction bars close). Consecutive bars inside the zone count as one touch.

### 4.2 Strength score (0–100)

```
touch_pts    = min(touches, 4) × 15                          (max 60)
reaction_pts = min(max_reaction_pct, 10) × 2                 (max 20)
               where max_reaction_pct = largest move away from the zone
               within 10 bars after any touch, as % of zone midpoint
recency_pts  = 20 if last touch within 60 bars of T
               10 if within 61–120 bars
               0  otherwise
flip_pts     = +10 if zone has flipped role (§5.2), capped so total ≤ 100
strength     = min(100, touch_pts + reaction_pts + recency_pts + flip_pts)
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

A zone is **broken downward** when `zone.break_confirm_closes` (default 2) **consecutive** closes are below `zone_low × (1 − setup.breakout_buffer_pct/100)`. Upward break mirrors with closes above `zone_high × (1 + setup.breakout_buffer_pct/100)`. The break is recorded at the last confirming close (`broken_at_index`).

Buffer ownership: **swing-level** breaks (BOS/CHoCH, TRD-02) use `structure.break_buffer_pct`; **zone** breaks and breakouts use `setup.breakout_buffer_pct`. Both default to 0.10%.

A single close beyond (with the next close back inside) is a **failed break**; it is counted as a touch and may qualify as a liquidity sweep (TRD-04 §6).

> Note: zone breaks (2 closes) are deliberately stricter than structural BOS (1 close, TRD-02 §6). BOS concerns a single swing price; zones concern an area that has attracted multiple reactions. **Unresolved:** whether to align both on one close — see OQ-SR-01.

### 5.2 Role reversal (flip)

After a break, the zone is retained with `role_reversed = true` and its role swaps (broken resistance → support candidate). Breakout-retest setups depend on this ([TRD-04 §3](04_SETUP_DETECTION_RULES.md)). A flipped zone that is broken again in the opposite direction is **retired** (`status = RETIRED`) and no longer drawn.

### 5.3 Zone status values

`ACTIVE`, `BROKEN_FLIPPED`, `RETIRED`.

## 6. Equal highs / equal lows

Two confirmed swing highs `a`, `b` (`b` later) form **equal highs** (EQH) when:

```
|b.price − a.price| / a.price ≤ structure.equal_level_tolerance_pct / 100     (0.20%)
and no close between a.index and b.index exceeded max(a.price, b.price)
and b.index − a.index ≥ 3 bars
```

Equal lows mirror. Equal highs/lows are recorded as **liquidity pools** (`liquidity_events.type = EQUAL_HIGHS | EQUAL_LOWS`) with level = `max` (highs) or `min` (lows). They are inputs to liquidity-sweep detection and are shown as evidence. They are distinct from the `EQH`/`EQL` swing label (which compares only to the immediately preceding pivot) but use the same tolerance.

## 7. Proximity

For close `C = C[T]`:

```
Support zone below price:     distance_pct = (C − zone_high) / C × 100      (≥ 0)
Resistance zone above price:  distance_pct = (zone_low − C) / C × 100       (≥ 0)
Price inside zone:            distance_pct = 0, position = INSIDE
```

`nearest_support` = active/flipped zone with the smallest non-negative distance below; `nearest_resistance` likewise above. A zone is **near** when `distance_pct ≤ zone.proximity_pct` (default 1.50%). Proximity is used by setup detection and for scanner filters ("near support").

## 8. Outputs

`price_zones` per run: id (deterministic hash of run + bounds), role (`SUPPORT`/`RESISTANCE` relative to `C[T]`), low, high, touches, strength score and bucket, formed/broken indexes, status, member pivot ids. Liquidity pools go to `liquidity_events`.

## 9. Edge cases

| Case | Handling |
|---|---|
| No pivots in lookback | No zones; setups that need zones return `NO_TRADE`. |
| Overlapping zones after expansion | Merge into one zone (union of bounds, sum of touches, recompute strength). |
| Price far from all zones (> 10%) | Zones still output; setups unlikely to qualify. |
| Very low-priced stocks (< ₹20) | Min width may be below 1 tick — expand to at least 2 ticks. |

## 10. Open questions

| ID | Question |
|---|---|
| OQ-SR-01 | Should zone breaks require 1 close (consistent with BOS) or 2 closes (current)? |
| OQ-SR-02 | Should higher-timeframe (weekly) pivots be merged into daily zones with a weight? Future scope. |
| OQ-SR-03 | Should touch counting decay with age instead of the recency bonus? |
