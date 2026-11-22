# Gate 0 Plan: Daily-Timeframe Framework Diagnosis

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Status | **Draft pre-registration, 2026-11-23. Not approved. Nothing has run.** It becomes binding when the owner approves it; after that a change is a new, separately logged pre-registration |
| Task | T-I146 |
| Authority | [ADR-019](../adr/ADR-019-DAILY-TIMEFRAME-RESEARCH-TRACK.md) (accepted 2026-11-23): no daily strategy is specified or run until this diagnosis reports |
| Related | [Framework diagnosis plan](framework-diagnosis-plan.md) (the intraday model for this plan) · [Validation criteria](validation-criteria.md) · [Experiment registry §6](experiment-registry.md#6-daily-gate-0-experiments) · [TRD-06](../trading/06_BACKTESTING_METHODOLOGY.md) |

Hypothetical, simulated results only (TRD-06 BT-06). The repository is public, so only aggregates are recorded; raw output stays outside it.

## 1. Purpose and what this is not

Gate 0 builds and checks the **daily framework** before any strategy exists: the data, the delivery costs, the exit and gap handling, and the **random-entry baselines** a future strategy must beat. It tests no entry rule. Whether any daily entry beats these baselines is the question of the first screening plan **after** this report, pre-registered separately, as for the intraday work. Gate 0 can therefore stop the track only for a data or simulator defect that cannot be fixed, or because the owner reads the baselines and chooses to stop.

## 2. What is already known (open questions of ADR-019)

| ID | Finding so far (2026-11-23) |
|---|---|
| OQ-HP-01 | Stored `1D` bars: 705 per stock for all 50 stocks, 2024-01-01..2026-11-19 (about 2.9 years). Not enough for a multi-year test. **Adjustment:** NESTLEIND closes near 1,330 in January 2024, which matches the pre-2024 price after the 2024 split (10:1) and the 2025 bonus (1:1) were both applied, so the provider's daily bars look **back-adjusted** (one example; DG-0 checks more). The `corporate_actions` table is empty. Kite's daily candles are fetched at most about 2,000 days per request (forum reports, not the official docs) and long histories are fetched in chunks; the **earliest available date per stock is unverified** |
| OQ-HP-02 | No point-in-time NIFTY 50 membership source (OQ-BT-01); `survivorship_bias_risk` stays set |
| OQ-HP-03 | Maximum holding period: 20 sessions (hypothesis), with 10 as a sensitivity (§5) |
| OQ-HP-04 | Delivery charges read from Groww's pricing and help pages on 2026-11-23; no effective date; the NSE exchange rate differs between the pages (0.00297% / 0.00307%); brokerage is not split by segment on the pricing page |
| OQ-HP-05, 06 | Left to the first strategy plan; Gate 0 trades are independent, one position per symbol, no account limits (as intraday experiment 4a) |

An anomaly seen while checking: one overnight gap above 15% in the stored daily bars (SHRIRAMFIN, 2026-01-01, +17.5%). DG-0 explains or flags it.

## 3. Data (fixed now)

- **Source and version.** Kite daily bars for today's NIFTY 50 (`--members-on 2026-11-19`). Because the provider adjusts history for corporate actions on the day it is fetched, **all daily bars used for Gate 0 and later daily work must come from one backfill run**; its date is the **data version**, recorded in every result. A later re-backfill is a new data version and needs the affected tests re-run.
- **Range.** From the earliest date the provider returns (target 2015-01-01) to 2026-11-19. If fewer than 1,250 sessions (about 5 years) are available for most stocks, Gate 0 reports `short_history` and the owner decides whether to continue.
- **Split.** Chronological by session date, 60% in-sample / 20% out-of-sample / 20% holdout ([TRD-06 §9](../trading/06_BACKTESTING_METHODOLOGY.md)). **Only the in-sample segment is read by any test** (a guard in the runner refuses later dates). Out-of-sample and holdout stay untouched for the later strategy work.
- **Exclusions.** Special sessions (partial or Muhurat) are dropped from the series; stock-sessions with a defect found in DG-0 are excluded and counted; each exclusion is reported.
- **Flags.** `survivorship_bias_risk`, `costs_unverified`, and `short_history` when applicable.

## 4. Conventions (fixed now)

| Item | Rule |
|---|---|
| Signal and fill | A signal at the close of session *d* fills at the **open of session *d*+1** plus 0.05% adverse slippage. A fill is skipped when the open is at or below the stop, or more than 1% above the signal close (hypothesis) |
| Stop | Checked from the fill session onward. A low at or below the stop exits at `stop × (1 − 0.05%)`; an open at or below the stop (an overnight gap) exits at `open × (1 − 0.05%)` |
| Target | A high at or above the target exits at the target, no slippage (a limit order); an open above it exits at the open. Stop and target in one session: the stop wins (BT-04) |
| Time stop | If no exit by the close of the H-th session counting the fill session, exit at that close with 0.05% adverse slippage |
| Sizing | Risk unit ₹500 (0.5% of ₹1,00,000), quantity `floor(500 / (entry − stop))`, position cap ₹50,000, one open position per symbol, no other account limits. R is measured against the actual risk of each trade |
| Costs | A new dated **delivery schedule** (Groww published, 2026-11-23): STT 0.1% on both sides; stamp duty 0.015% on the buy; brokerage `min(₹20, 0.1%)` per order; NSE exchange charge 0.00307% (sensitivity 0.00297%); SEBI 0.0001%; investor-protection charge 0.0001%; DP charge ₹20 on each sell (₹3.50 + ₹16.50); GST 18% on brokerage, exchange, SEBI, IPFT and DP. A ₹50,000 round trip costs about ₹182. Reported with the intraday schedule's slippage assumption and as `costs_unverified` |
| Statistics | Intervals resample **calendar months** (10,000 resamples, seed 1) because trades overlap in time and across stocks. "Material" means the interval excludes zero and the effect is at least 0.05R (0.1% for returns) |

## 5. Tests

| ID | Test | Method | Output |
|---|---|---|---|
| DG-0 | **Data audit** | Per stock: first and last date, sessions against the expected exchange calendar, missing and duplicate sessions, non-positive prices, OHLC consistency (`low ≤ open, close ≤ high`), every overnight gap above 15% listed and explained by a known corporate action or flagged; adjustedness checked against the known split, bonus and demerger events of each stock in range (the plan lists them before the run, from public records) | Coverage table, anomaly list, exclusions, a `data version` and `short_history` verdict |
| DG-1 | **Drift baseline** | Buy the open of the session after every in-sample session, no stop or target, sell H sessions later (H = 5, 10, 20): mean return %, gross, with month-block intervals; by calendar year; an equal-weight basket of all stocks for context | Mean and median return, interval, by year. Tests whether random long holds have a positive baseline |
| DG-2 | **Friction decomposition** | For stop distances 2%, 3%, 4%, 5% and 8% at the risk unit: position size, charges, slippage, and the total in R (the table in ADR-019, recomputed with the code), plus the measured realised stop-out R of DG-3 trades (gap effect) | Table; confirms or corrects ADR-019 §Context |
| DG-3 | **Random-entry baseline grid** | For each stock, per calendar month and per seed (1 to 5), one uniformly random in-sample session as the signal day (a skipped fill is redrawn up to 20 times, redraws reported). Grid: stop distance 2%, 3%, 5%, 8% below the signal close × target none, 2.5R, 4R × maximum hold 10 and 20 sessions = 24 configurations, all reported. No R:R rule is applied (these are baselines, not setups) | Per configuration: trades, average R gross and net with month-block intervals, exit mix, average stop-out R. **This is the bar a future daily strategy must beat** (§6) |
| DG-4 | **Simulator spot check** | 20 trades from DG-3 (seed 1, five forced to be overnight gap exits) recomputed from the raw bars with separate logic: fill, stop, gap, target, time stop, P&L; the delivery cost of each recomputed by hand-checked arithmetic | Agreement table |
| DG-5 | **Survivorship and coverage** | Share of stock-sessions from stocks with the full history; DG-3 for the full-history stocks only against all stocks (a sensitivity, not a correction) | Difference in average R with an interval |
| DG-6 | **Charges sensitivity** | Net R of DG-3 under the two exchange rates (0.00297% and 0.00307%), and with brokerage 0 and ₹40 per order | Range of net R; shows how much the unverified items matter |

Slippage sensitivity (0%, 0.05%, 0.10%) is reported for DG-3.

## 6. Decision rules (fixed now)

The result is a report, not a rule change. Every framework change and the decision to continue go to the owner.

| Finding | Conclusion | Next step (owner decides) |
|---|---|---|
| DG-0 finds a defect (unadjusted actions, missing sessions, bad bars) | Results would be wrong | Fix or exclude with a test first; re-run the affected tests |
| DG-4 finds a defect | The simulator is wrong | Fix with a test; re-run DG-3, DG-5, DG-6 |
| DG-1 and DG-3 show random long entries with a net average R above zero in some configurations (interval above zero) | Market drift dominates; a strategy must beat the matched baseline of its own configuration, not zero | The screening plan fixes the baseline per configuration |
| DG-3 baselines are near 0R gross and negative net | Friction sets the bar: a strategy needs a gross edge of at least the DG-2 friction plus 0.05R at its stop distance | The screening plan states the needed edge per stop size |
| Every configuration is net negative and drift is not positive | The framework offers no free baseline; any edge must come from the entry | The owner decides whether to continue to a first pre-registered screen or stop |
| DG-5 shows a material difference between all stocks and full-history stocks | Survivorship distorts the baseline | Report both; later screens use the full-history set as the primary |
| History shorter than 1,250 sessions for most stocks | `short_history` | The owner decides whether to continue |

The **first strategy screening plan** (a pre-registered family, a matched control per variant, a stricter interval for the number tried, as [fast screening](fast-screening-protocol.md)) is drafted only after this report and needs its own approval.

## 7. Owner steps (before DG-0 can run)

1. Log in to Kite for the day: `uv run python scripts/kite_login.py` (the token expires about 06:00 IST).
2. Backfill daily history in one run, from the earliest date wanted: `uv run python scripts/market_data_cli.py backfill --code NIFTY50 --timeframe 1D --from 2015-01-01 --to 2026-11-19 --no-resume --as-of 2026-11-19`. Rows already stored are upserted, so the 2024 to 2026 bars are refreshed under the same adjustment. If the provider returns less than the target range, say so; DG-0 reports the real coverage.
3. Tell me the backfill date; it becomes the data version.

I will first check the backfill's behaviour against the existing rows (idempotent upsert, per its documentation) and that its chunking respects the provider's per-request limit; I will not run it myself without a fresh login.

## 8. Implementation (after approval)

- Daily simulator and the delivery cost schedule (`app/backtest/costs.py`, with the ₹50,000 example hand-computed in a test), daily random-entry sampler, month-block bootstrap, data-audit helpers, and the in-sample split guard, in `python-engine/app/backtest/diagnostics/` with unit tests (gap through the stop, stop and target in one session, time stop, one position per symbol, fill skips, month blocks, no read beyond the in-sample date).
- Runner `scripts/run_gate0.py`; raw output in the research directory outside the repository; the engine suite stays green and no detector, ruleset or replay behaviour changes.
- Report `docs/research/gate0-daily-diagnosis-report.md` (aggregates only) and one registry row per test ([§6](experiment-registry.md#6-daily-gate-0-experiments)).

## 9. Limits

- Survivorship bias (today's NIFTY 50 over many years); costs unverified (rates read on one date, two pages disagree, brokerage segment split unclear); slippage 0.05% is an assumption.
- Provider adjustment is inferred from one example until DG-0 checks more; the adjustment is as of the backfill date.
- Random baselines say nothing about any entry rule; a good baseline can also be market drift of a bull period (2015 to 2021 was largely rising), which DG-1 shows by year.
- The month-block bootstrap has fewer independent blocks than the intraday session bootstrap (about 85 months in-sample at most), so intervals will be wider.
