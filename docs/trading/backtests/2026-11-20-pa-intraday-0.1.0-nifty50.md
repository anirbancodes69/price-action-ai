# Backtest log: pa-intraday 0.1.0, NIFTY 50, 2026-09-01 to 2026-11-19

| Field | Value |
|---|---|
| Date run | 2026-11-20 |
| Purpose | `EXPLORATION:all`, the first replay on real bars ([TRD-06](../06_BACKTESTING_METHODOLOGY.md)) |
| Ruleset | `pa-intraday 0.1.0` (unchanged) |
| Engine | `priceaction-engine 0.1.0`, with the zone cache (T-I131; results identical to the uncached engine) |
| Data | PERSONAL Kite source, 5m and 15m bars; 55 sessions; universe `NIFTY50` from the owner's symbol list (no point-in-time membership, OQ-BT-01) |
| Sizing | `FIXED`, capital ₹1,00,000, 0.5% risk, ₹50,000 position cap, max 2 open positions, daily loss 1.5%, 3-loss streak |
| Costs | `nse-intraday-assumed-0` with 0.05% slippage: **unverified assumptions** (OQ-BT-02) |
| Run | 5 chunks of 11 sessions, merged by trade; input hashes `ff693a3893ef`, `b29d5614af79`, `b96a71167a49`, `715766b90c26`, `9ae8f9fb3ad2` |
| Flags | `short_history`, `survivorship_bias_risk` |

> Hypothetical, simulated results. Past performance does not indicate future results. Only aggregates are recorded here: the trade list is derived from personal-mode Kite data and is not published in this repository ([ADR-011](../../adr/ADR-011-DATA-MODES-AND-TENANT-ISOLATION.md)).

## 1. Result

| Metric | Value |
|---|---|
| Trades | 176 (50 wins, 126 losses) |
| Win rate | 28.4% |
| Net P&L | **−₹16,794** (−16.8% of capital) |
| Gross P&L (before costs) | −₹7,988 |
| Costs | ₹8,806 (median ₹52 per trade) |
| Average R | −0.39 net, −0.20 gross |
| Profit factor | 0.52 |
| Average win / loss | +₹367 / −₹279 |
| Daily P&L | mean −₹336; 15 of 50 trading days positive; best +₹1,866, worst −₹1,412 |
| Max drawdown (daily, fixed sizing) | ₹17,235 (17.2%) |
| Exits | 80 stop, 46 session-end, 37 structure exit, 13 target |
| Skips | 667 max open positions, 99 already in position, 99 reward-to-risk degraded at fill, 70 account limit, 3 session cutoff, 1 stop too wide, 1 RR below minimum |

| Setup | Trades | Win | Avg R net | Net |
|---|---|---|---|---|
| BREAKOUT_RETEST | 130 | 26% | −0.48 | −₹15,365 |
| PREV_DAY_HIGH_BREAK | 33 | 30% | −0.27 | −₹2,144 |
| OPENING_RANGE_BREAKOUT | 13 | 46% | +0.10 | +₹715 |

By month: September −₹6,084 (60 trades), October −₹7,305 (69), November −₹3,405 (47).

## 2. Diagnostics

The 55 sessions were split for every check below: **in-sample (IS)** = before 2026-10-21 (105 trades), **out-of-sample (OOS)** = from 2026-10-21 (71 trades). A finding counts only if it holds in both halves.

| # | Finding | Evidence |
|---|---|---|
| D1 | **The entries have no edge before costs.** | Gross expectancy −0.25R (IS) and −0.13R (OOS). |
| D2 | **Costs take about 0.2R per trade.** The ₹50,000 position cap binds, so with a median stop of 0.55% the money at risk is about ₹270, not ₹500; round-trip costs are about 0.1% of the position value, which is about 0.19R. | Cost per trade / risk per trade: mean 0.195. Trades with stops ≥ 0.7% lose −0.19R (IS) and −0.21R (OOS) net, against −0.45R / −0.32R for all trades. |
| D3 | **BREAKOUT_RETEST is negative in both halves**, and it is 74% of the trades. | −0.49R (IS, 77 trades) and −0.45R (OOS, 53 trades) net. |
| D4 | **Targets are far for the moves that occur.** Median stop-out takes 9 bars (45 minutes). | Of 172 trades with bars: 58% reach +0.5R, 39% reach +1R, 20% +1.5R, 12% +2R, 4% +2.5R. |
| D5 | **Structure exits give back gains.** The 37 structure exits averaged −0.23R gross, although 18 of them had first reached +1R. |
| D6 | **Changing exits alone does not fix it.** On the same entries, fixed targets of 1.0R to 2.5R, with or without a breakeven stop at +1R, all stay between −0.28R and −0.38R net in both halves. | 5m-bar simulation; a bar touching both stop and target counts as the stop. |
| D7 | **PAQS does not rank outcomes**, so choosing the highest-scoring signal when several fire at once is no better than any other order. | Average R net by PAQS band 60/70/80/90/100: −0.58, −0.26, −0.47, −0.29, −0.65. |
| D8 | **15m context `BULLISH` is worse than `TRANSITION`.** | −0.54R / −0.43R net (IS/OOS) against −0.33R / −0.12R. |
| D9 | No filter tested is positive net in both halves with a usable sample. The 09:30–09:59 window was +0.13R IS but −0.11R OOS; `OPENING_RANGE_BREAKOUT` alone was +0.01R / +0.23R on only 8 and 5 trades. | Filters were applied to the existing trades, so freed position slots were not refilled; a real re-run is needed for any candidate. |

## 3. Candidate changes (not adopted)

None of these is adopted. Each is a rule change that needs an owner decision, a new ruleset version, the TRD updates and an out-of-sample replay before use ([CLAUDE.md §4](../../../CLAUDE.md), TRD-01 MP-09).

| Candidate | Addresses | Testable today |
|---|---|---|
| Disable or rework BREAKOUT_RETEST | D3 | Tested as run C (§4); adopting it needs a code change and a ruleset version |
| Raise `risk.min_stop_distance_pct` (now 0.15) to about 0.5–0.7 so costs are a smaller share of risk | D2 | Tested as runs A and B (§4); a ruleset parameter |
| Prefer `TRANSITION` over `BULLISH` 15m context, or drop late-trend entries | D8 | Needs a code change |
| Replace PAQS ordering with a measure that predicts outcomes, or re-weight PAQS | D7 | Needs research and a ruleset version |
| Target and structure-exit rules | D4, D5 | Only together with better entries (D6) |

## 4. Exploration variants A–D (same 55 sessions)

Each variant changes one thing against `pa-intraday 0.1.0` and is otherwise identical: same data, sizing, costs and chunks. The changes were made by a temporary script, with no edits to the ruleset file or the engine code, so **none of them is a ruleset version**.

| Run | Change |
|---|---|
| A | `risk.min_stop_distance_pct` 0.15 → 0.5 |
| B | `risk.min_stop_distance_pct` 0.15 → 0.7 |
| C | BREAKOUT_RETEST detection off |
| D | C and B together |

| | 0.1.0 | A | B | C | D |
|---|---|---|---|---|---|
| Trades | 176 | 116 | 70 | 72 | 48 |
| Win rate | 28.4% | 34.5% | 38.6% | 36.1% | 43.8% |
| Avg R net / gross | −0.39 / −0.20 | −0.28 / −0.14 | −0.14 / −0.04 | −0.15 / −0.02 | +0.02 / +0.12 |
| Net P&L | −₹16,794 | −₹10,545 | −₹3,974 | −₹2,536 | +₹345 |
| Gross P&L | −₹7,988 | −₹4,855 | −₹750 | +₹749 | +₹2,406 |
| Profit factor | 0.52 | 0.56 | 0.70 | 0.79 | 1.05 |
| IS net (avg R net) | −₹11,429 (−0.45) | −₹7,880 (−0.37) | −₹2,012 (−0.13) | −₹2,868 (−0.23) | −₹550 (−0.03) |
| OOS net (avg R net) | −₹5,365 (−0.32) | −₹2,665 (−0.17) | −₹1,962 (−0.16) | +₹332 (−0.04) | +₹895 (+0.08) |
| Stop-outs | 80 | 42 | 14 | 19 | 5 |
| Max-positions skips | 667 | 564 | 394 | 60 | 52 |

Run D in more detail: costs ₹2,061 (about 0.09R per trade, against about 0.2R in 0.1.0); gross R positive in both halves (+0.07 IS, +0.17 OOS); OPENING_RANGE_BREAKOUT +0.05R / +0.18R net (12 and 10 trades), PREV_DAY_HIGH_BREAK −0.09R / 0.00R (15 and 11 trades); exits 24 session-end, 17 structure, 5 stop, 2 target.

**Reading:**

- Both changes improve the result in both halves; together (D) they bring the rules to about break-even after costs.
- D is **not evidence of profitability**: +₹345 over 48 trades is within noise, its in-sample half is still slightly negative net, and D was chosen after seeing A–C on the same days (selection bias). Costs are still assumptions.
- D is the best **candidate** for a proposed `pa-intraday 0.2.0`. Adopting it needs an owner decision, a ruleset version with the TRD updates, a setup on/off switch in code, and a test on sessions it was not chosen on (more history, or forward paper logging, TRD-07).

## 5. Limits of this run

- 55 sessions in one market period; IS and OOS are 34 and 21 sessions. Any variant tuned on these days must be checked on new days (forward paper logging, TRD-07) before it is trusted.
- Today's NIFTY 50 list is applied to the whole period (survivorship bias).
- Costs and slippage are assumptions; verify them against your actual Zerodha contract notes (OQ-BT-02).
- Kite equity bars end at 15:15, so the last 15 minutes of each session are not replayed.
