# ADR-019: Daily-Timeframe Research Track (Longer Holding Period)

| Field | Value |
|---|---|
| Status | **Proposed** (2026-11-23). Not accepted: nothing below is in force until the owner accepts it |
| Date | 2026-11-23 |
| Deciders | Product owner |
| Version | 0.1 (proposal) |
| Related | [ADR-014](ADR-014-PERSONAL-INTRADAY-WORKSTATION.md) · [ADR-018](ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md) · [ADR-008](ADR-008-DETERMINISTIC-TRADING-ENGINE.md) · [ADR-010](ADR-010-MANUAL-TRADE-EXECUTION-MVP.md) · [ADR-015](ADR-015-INTRADAY-TIME-AND-SNAPSHOT-MODEL.md) · [TRD-01](../trading/01_TRADING_METHODOLOGY.md) · [Framework diagnosis report](../research/framework-diagnosis-report.md) · [Fast screening report](../research/fast-screening-report.md) · [Validation criteria](../research/validation-criteria.md) |

## Context

[ADR-014](ADR-014-PERSONAL-INTRADAY-WORKSTATION.md) sets the product scope: intraday, 15m structure and 5m setups, every position closed by the end of the session. Two independent strategies and three minimal entries have since been tested on that scope, over 427 in-sample sessions and 50 stocks:

- Neither parked strategy beats matched random entries (gross +0.009R and +0.037R, below the 0.05R line); before slippage and charges both earn about 0R ([diagnosis](../research/framework-diagnosis-report.md)).
- Friction costs about 0.3R per trade (slippage about 0.15R, charges about 0.16R, the latter now checked against the broker's published schedule) because intraday stops are 0.3% to 1.0% of price.
- A fixed family of 13 variants (stop-distance filters; three minimal entries) screened on 2024 produced no promotion; the simplest breakouts were worse than random entries ([screen](../research/fast-screening-report.md)).

This is evidence about intraday long entries of these kinds on today's NIFTY 50 at today's friction, not proof that no intraday edge exists. It does motivate looking at a scope where friction is a smaller share of each move.

**What a longer holding period does and does not change.** Friction is fixed in price terms, so its cost in R falls as the stop widens. The delivery schedule is not cheaper per trade, though: STT is 0.1% on both sides (intraday 0.025% on the sell side), stamp duty 0.015%, and a flat DP charge of about ₹20 falls on every sell. At the planning values (capital ₹1,00,000, risk 0.5% = ₹500 per trade, position cap ₹50,000, slippage 0.05% on each side) and Groww's published delivery charges (read 2026-11-23, dated history unverified, the pages disagree on the NSE exchange rate: 0.00297% or 0.00307%):

| Stop distance | Position | Charges | Charges + slippage, in R |
|---|---|---|---|
| 2% | ₹25,000 | ₹126 | 0.30R |
| 3% | ₹16,667 | ₹100 | 0.23R |
| 4% | ₹12,500 | ₹81 | 0.19R |
| 5% | ₹10,000 | ₹69 | 0.16R |
| 8% | ₹6,250 | ₹52 | 0.12R |

Intraday costs about 0.3R at 0.3% to 1.0% stops. So a longer hold is **no cheaper than intraday until the stop is about 3% to 4% or wider**, and the saving at 5% is about half. The gain exists only for setups with swing-sized structure, and positions are small (₹6,000 to ₹25,000 of ₹1,00,000), so several run at once. This corrects the shorthand "friction spread over larger moves": it is true only above those stop sizes.

Other facts that bear on the decision:

- Daily (`1D`) bars are already stored (2024-01-01 onwards, 24,300 bars loaded and checked, D-7). A multi-year test needs a longer backfill; the depth the broker allows is unverified.
- Daily replay is far cheaper than intraday: 50 stocks over ten years is about 125,000 bars and needs no per-bar structure analysis at 5m. The full intraday in-sample run took about 3.7 hours.
- Constraints that stay: long-only actionability (C-12), manual execution (ADR-010), closed bars, no look-ahead, deterministic versioned rulesets, no indicators (MP-01).
- Constraints that do not carry over: MP-11 "session-bounded", the 15:15 session exit, the entry cutoff and the daily-loss and consecutive-loss limits are intraday ideas.

## Decision (proposed)

1. **A research track, not a product pivot.** Add a **daily-timeframe, multi-day-hold research track** to the strategy library process of ADR-018. The workstation's product scope stays intraday (ADR-014 remains Accepted and is **not** superseded by this ADR). If a daily strategy reaches `RESEARCH_VALIDATED`, a separate ADR decides whether and how the product scope changes; until then nothing in the frontend, backend, scanner or schema changes.
2. **Research scope.** NSE cash equities, NIFTY 50, long-only. Daily bars are primary. A signal is evaluated at the close of a daily bar and acted on no earlier than the next session's open. A position may be held overnight; exits are the stop, the target, or a time stop at a maximum holding period (hypothesis: 20 sessions, fixed in the Gate 0 plan before any result). Gaps through the stop fill at the open.
3. **Gate 0 first.** The lesson of the intraday work applies before any strategy: **no daily strategy is specified or run until a framework diagnosis on daily data reports.** It would pre-register and run: drift baseline; matched random-entry controls under the delivery cost schedule; friction decomposition by stop distance; a simulator spot check with the overnight, gap and corporate-action handling; and a corporate-action and survivorship audit. Its report goes to the owner, who decides whether the track continues.
4. **Process unchanged.** ADR-018 holds: strategies are specified, implemented, tested and backtested in isolation, one at a time, with the validation criteria ([chronological 60/20/20 split](../research/validation-criteria.md), out-of-sample one-shot, holdout touched once) and an experiment registry entry for every run. The fast-screening discipline applies: families of variants are pre-registered with a stricter interval for the number tried.
5. **Costs.** A delivery cost schedule is added as a dated, versioned schedule next to the intraday one, from the broker's published charges (STT 0.1% both sides, stamp 0.015% on the buy, brokerage 0.1% capped at ₹20 per order, exchange, SEBI and investor-protection charges, the DP charge on each sell, GST). Rates and slippage stay labelled `costs_unverified` until checked against dated history and real fills.
6. **Risk model.** The per-trade risk (0.5%) and the position cap are kept as planning values. Account-level limits for overlapping multi-day positions (maximum concurrent positions, open risk) are re-specified in the Gate 0 plan; the intraday daily-loss and consecutive-loss limits are not reused as they are.
7. **Data and flags.** Backfill daily history as far back as the provider allows, with corporate-action adjustment (splits, bonuses) for any multi-day hold. Survivorship bias grows with the length of history (today's NIFTY 50 over ten years), so `survivorship_bias_risk` stays set and its handling is part of Gate 0 (OQ-BT-01).
8. **Statistics.** Trades overlap in time and in the market, so intervals resample by calendar month (or longer blocks), not by session.

## Alternatives considered

| Alternative | Why not chosen now |
|---|---|
| Stay intraday and pause strategy work | The evidence supports pausing, but it leaves no path to a validated strategy. This ADR keeps the pause for the product and adds a cheap place to look. Can be chosen instead. |
| Measure real slippage first | Cheap and useful, and independent of this ADR (a few small real trades). It does not change the entry result, so it can run in parallel, not instead. |
| Switch the whole product to daily now | No daily strategy has any evidence; ADR-014 took a large specification rewrite and this would repeat it before a result exists. |
| Other intraday variants (mid-caps, shorting, 1-minute bars) | Not evaluated; shorting needs its own ADR (C-12), mid-caps change the universe and liquidity assumptions. Possible later pre-registrations, not part of this decision. |
| Daily context as a filter on intraday entries | Already allowed (previous-day levels, daily structure as context) and used in the screens; it does not lower friction. |

## Consequences

+ A cheap, fast research track (daily bars, no per-bar structure replay) that can test the one lever the evidence points to: friction relative to the stop.
+ Nothing in production changes; if Gate 0 or the first strategies show no edge, the cost is a few research documents and some research code.
+ Reuses the existing harness (replay, exits, costs, controls, bootstrap) with a daily mode, a delivery cost schedule and gap handling.
− Overnight gap risk and a slower feedback loop (fewer, longer trades; fewer independent observations per year than intraday).
− Positions are small at ₹1,00,000 and 0.5% risk, so capital is largely idle unless several positions run at once, which needs concurrency rules.
− Longer history means more survivorship and corporate-action risk; a verified NIFTY 50 history is unavailable (OQ-BT-01).
− If accepted and a strategy validates, a later ADR must revise MP-11, TRD-01 scope, TRD-05 (session exit, account limits), TRD-06, ADR-015's session-bound assumptions, the roadmap milestones, the frontend and CLAUDE.md §1.

**Migration and compatibility (for this ADR).** None: research code and documents only; no schema, API, ruleset or frontend change; the stored `1D` bars are reused. A new ruleset family for the daily track would be created in the Gate 0 or first strategy plan, not here.

## Open questions

| ID | Question |
|---|---|
| OQ-HP-01 | How deep is the provider's daily history, and is it corporate-action adjusted? |
| OQ-HP-02 | Is a point-in-time NIFTY 50 membership history obtainable (OQ-BT-01)? |
| OQ-HP-03 | Maximum holding period (20 sessions is a hypothesis) and the time-stop rule |
| OQ-HP-04 | Delivery charges: dated history; the NSE exchange-rate discrepancy on the broker's two pages; and whether brokerage for delivery is the same 0.1% (cap ₹20) as intraday (the pricing page shows one equity brokerage box, not split by segment) |
| OQ-HP-05 | Concurrency and capital allocation for small overlapping positions |
| OQ-HP-06 | Whether 15m or 5m bars may refine the entry day (execution only) later |

## Stop conditions

The owner may stop the track at Gate 0 (no daily entry beats random controls under delivery costs, or the simulator or data audit finds a defect), or after a pre-registered family of strategy variants with no promotion, as for the intraday work. The decision then returns to the options left in the diagnosis report.

## Status

Proposed on 2026-11-23. To accept, the owner approves it as written or with changes; acceptance changes this status, adds a decision row and creates the Gate 0 task, and does not supersede ADR-014.
