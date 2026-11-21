# Adaptive Strategy Research Readiness Audit

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Scope | Can the repository backtest an Adaptive Strategy Orchestrator on NSE data from 2024-01-01 to the latest session? |
| Type | **Audit only.** No source, configuration, database or strategy change was made. The only file written is this report. |
| Code audited | branch `feature/liquidity-sweep-reversal`, HEAD `10be806` (includes `pa-intraday 0.2.0`) |
| Data audited | the live Postgres container (`priceaction-postgres-1`), read-only `SELECT`s on the PERSONAL Kite source `01a1f4ec-…` |
| Tests run | `pytest tests/backtest tests/trading tests/ingestion`: 189 passed, 0 failed (executed 2026-11-21) |

Evidence conventions: `path:line` for code, "SQL" for a query run against the database. Anything taken from memory or the repo's own docs rather than verified here is labelled **unverified**.

---

## Summary

- **Verdict: ready after minor fixes**, for a **long-only, 5m/15m-structure** experiment. It is **not** ready for anything that needs executable shorts, 1-minute resolution, or a claim of point-in-time universe correctness.
- The backtester mechanics are sound. I found no look-ahead path, next-bar fills are enforced, and same-bar stop/target ambiguity resolves against the trader. Classification: **partially reliable**, because the inputs and assumptions around the engine are weaker than the engine.
- 717 sessions of 5m and 15m bars exist for 50 instruments from 2024-01-01 to 2026-11-19, with no duplicate bars and no invalid OHLC rows.
- Three data findings matter most: (1) the universe is today's 50 names (survivorship); (2) the last 15 minutes of every session are missing from 2026-08-03 onward, which changes how previous-day levels are derived; (3) the TMPV demerger on 2025-10-14 is an unadjusted price break.
- None of the three existing strategies has shown an edge on this repository's own backtests (§5.C). The orchestrator experiment should be framed as a test of whether switching helps, not as a search for something that already works.

---

## A. Repository Architecture Assessment

### Flow from market data to a simulated trade

```
Kite historical API ──► KiteProvider.fetch_bars        python-engine/app/providers/kite/provider.py:38,108
        │                  (5m, 15m, 1D only)
        ▼
backfill()  ──► invalid_bar_reason() drops corrupt bars   app/ingestion/backfill.py:50-64,128-135
        │         "stores what the provider returns"        app/ingestion/backfill.py:4
        ▼
candles table (Postgres, PK source+instrument+timeframe+bar_start, CHECK constraints)
        │
        ▼
load_backtest_inputs()                                   app/backtest/loader.py:84-128
  · sessions = days that have 5m bars (no holiday calendar)   loader.py:3-6, 110-114
  · prev-day H/L/C from the previous session's 5m bars        loader.py:46-52
  · 15m bars from the stored 15m series (not rebuilt from 5m)
        │
        ▼
run_backtest() → replay_session()                        app/backtest/run.py:96, replay.py:104
  per 5m bar close, per symbol:
    default_analyse(sym, k) → analyse(bars[:k], 15m ended ≤ now, …)    replay.py:77-93
      snapshot check → pivots → structure (BOS/CHoCH) → 15m alignment
      → session levels → zones → equal-level pools
      → detect_opening_range / detect_prev_day / detect_breakout_retest / detect_liquidity_sweep
      → trade_levels (stop, target ladder) → PAQS score → choose_signal    app/domain/analyse.py:56-119
    ENTRY_CONFIRMED candidates sorted by (-PAQS, symbol)                    replay.py:231
    calculate_risk() (limits, stop-distance, RR, sizing)                    app/domain/risk/request.py:65-119
    order queued ──► filled at next bar open (simulate_entry)               app/domain/risk/fill.py
    step_position() on each later bar (stop / target / session end / structure exit)
    close_trade() applies the cost schedule                                 app/backtest/trade.py:94-122
        │
        ▼
compute_metrics(), splits, report (app/backtest/metrics.py, splits.py, report.py)
```

### Assessment

- **One code path.** The backtest calls the same `analyse()` the live engine uses (`replay.py:77-93`), which is what TRD-06 BT-03 requires. All trading logic lives under `app/domain` (pure, `Decimal`-based).
- **Extension points that need no production edit.** `run_backtest(..., analyse_fn=…)` accepts a replacement analysis function (`run.py:96-99`). `RulesetParams(code, version, values)` is a plain dataclass (`app/domain/params.py`), so a research script can build a parameter set without touching `rulesets/`. `AnalysisResult.setups` carries every scored setup with its `TradeLevels`, not only the primary one. These three points are enough to build an orchestrator outside `app/`.
- **Weak points in the surrounding system:**
  - The session calendar is inferred from bars (§B.5).
  - The universe loader reads effective-dated memberships, but only one date exists (§B.2).
  - The CLI does not persist runs (`backtest_runs` has 0 rows, SQL) although TRD-06 §9 requires every tried parameter set to be logged.
  - `scripts/run_backtest.py` always uses the default `CostSchedule()` (`run_backtest.py:86`) and defaults to ruleset `pa-intraday@0.1.0` (`:49`).
  - Variants A–D in the earlier report were run by "a temporary script" that is not in the repository (`docs/trading/backtests/2026-11-20-pa-intraday-0.1.0-nifty50.md` §4), so those runs cannot be reproduced from the repo alone.

---

## B. Historical Data Availability

All figures from SQL on the PERSONAL Kite source. The DEMO source (36 instruments, Nov 2026 only) is synthetic and was excluded.

### B.1 Coverage by timeframe

| Timeframe | Rows | First day | Last day | Sessions | Instruments |
|---|---|---|---|---|---|
| 5m | 2,662,585 | 2024-01-01 | 2026-11-19 | 717 | 50 |
| 15m | 887,547 | 2024-01-01 | 2026-11-19 | 717 | 50 |
| 1D | 10,950 | **2026-01-01** | 2026-11-19 | 219 | 50 |
| **1m** | **0** | none | none | 0 | 0 |

The candles table accepts `1m` (`ck_candles__timeframe`) but the provider layer does not: `Timeframe = Literal["5m", "15m", "1D"]` (`app/providers/base.py:11`) and the Kite interval map has no minute entry (`app/providers/kite/provider.py:38`). Whether Kite serves 1m history for 2024 was not tested here and must not be assumed.

`CURRENT.md` says the stored bars start on 2026-01-01. That is out of date: the 2024-01-01..2025-12-31 backfill finished on 2026-11-20 (`ingestion_runs`, SQL).

### B.2 Universe and instruments

- `NIFTY50` universe: 50 members, all with `effective_from = 2026-09-01` and no closed memberships (SQL on `universe_memberships`). It is the owner's symbol file, applied to the whole period (`app/ingestion/universe.py:1-5`, OQ-BT-01).
- Consequence 1, **survivorship**. Names that are in the database: ETERNAL, TMPV, JIOFIN, TRENT, BEL, SHRIRAMFIN, MAXHEALTH, INDIGO. Names absent from the database: BPCL, BRITANNIA, DIVISLAB, HEROMOTOCO, INDUSINDBK, LTIM, UPL. That several of the first group joined the index after January 2024 and that several of the second group were members in 2024 is **unverified** (from recollection, no in-repo source). The absence of the second group is verified.
- Consequence 2, **the CLI cannot select a 2024–2025 universe.** `universe_members(conn, code, a.to)` (`scripts/run_backtest.py:65`) filters on `effective_from <= to`. With every membership dated 2026-09-01, `--to 2026-08-31` returns no members and the script exits with "No members in universe" (`:66-71`). The earlier Jan–Aug 2026 replay must therefore have used a script that bypassed this.
- Instrument mapping: 64 instruments (all `ACTIVE`); Kite provider references exist for 50, all with `valid_from = 2026-11-19` and none closed (SQL on `instrument_provider_refs`). History is stored under today's instrument rows (`backfill.py:94-99`). Symbol changes (ETERNAL formerly Zomato, TMPV formerly Tata Motors) are not recorded as `SYMBOL_CHANGE` actions.
- `run_backtest` marks every run `survivorship_bias_risk` unless `point_in_time_universe=True` (`app/backtest/run.py:40,119-120`), and nothing sets it to true.

### B.3 Bar completeness

Expected: 75 5m bars and 25 15m bars per normal session (`app/ingestion/session.py:1-3`).

| Period | Sessions | 5m bars per session | 15m bars per session |
|---|---|---|---|
| 2024-01-01 .. 2026-07-31 | 637 normal | 75 (09:15–15:25 starts) | 25 |
| **2026-08-03 .. 2026-11-19** | **75** | **72 (last bar starts 15:10)** | **24** |
| Special sessions | 5 | 11, 12, 12, 21, 21 (see B.5) | 4, 4, 4, 7, 7 |

Finding **D-1, regime break at 2026-08-03.** From that date every session lacks the 15:15, 15:20 and 15:25 bars. Both periods were fetched in one backfill run on 2026-11-20 (the Jan–Aug 2026 run, which covers both sides of the boundary), so this is a property of what the provider returned, not of when a range was fetched. The cause is not determined. `ARC-08 §4.0` and TRD-06 §3 state that Kite equity bars stop at 15:15; the 637 earlier sessions contradict that.

Effect on previous-day levels, measured against the official daily bars (SQL, 2026 sessions that have a 1D row):

| Period | Sessions compared | PDH differs | PDL differs | Official close differs from last 5m close |
|---|---|---|---|---|
| 75-bar sessions | 7,150 | 13 (0.2%) | 16 (0.2%) | 6,991 (98%, mean 0.155%) |
| 72-bar sessions | 3,800 | **349 (9.2%)** | **253 (6.7%)** | 3,625 (95%, mean 0.306%) |

The loader derives PDH/PDL/PDC from the previous session's 5m bars (`app/backtest/loader.py:46-52`), so from August 2026 the levels used by the opening-range, previous-day and retest setups are wrong about one time in ten for PDH. The close differs in both periods because the official close is not the last trade; PDC is not used by any setup trigger, only PDH and PDL are.

Individual missing bars (SQL, 5m): 7 instrument-sessions out of 35,850:

| Instrument | Session | Bars | Cause |
|---|---|---|---|
| BHARTIARTL, HDFCBANK, ICICIBANK, SBILIFE | 2024-06-25 | 74 | the 09:15 bar was rejected as "OHLC out of order" in the backfill (`ingestion_runs.error_summary`) |
| ITC | 2025-01-06 | 72 | 3 bars missing |
| TMPV | 2025-10-14 | 71 | 4 bars missing |
| HINDUNILVR | 2025-12-05 | 71 | 4 bars missing |

Zero-volume bars: 16 (5m) and 9 (15m), all in the opening bars of ITC 2025-01-06, TMPV 2025-10-14 and HINDUNILVR 2025-12-05, the same sessions that have missing bars.

`data_quality_issues` has **0 rows**. The historical backfill runs no quality check (`backfill.py:3-4`), so the gaps above are known only because this audit queried them.

### B.4 Integrity checks that passed (SQL)

| Check | Result |
|---|---|
| Duplicate `(source, instrument, timeframe, bar_start)` | 0 (also enforced by the primary key) |
| Non-positive prices | 0 |
| `low > min(open, close)` or `high < max(open, close)` | 0 (also enforced by `ck_candles__ohlc`) |
| Bars off the 5m grid, or outside 09:15–15:30 | none; the only out-of-hours bars are the 18:00 Muhurat sessions |
| Timezone | `bar_start` is `timestamptz`; every start falls on the IST 5-minute grid; `ck_candles__session_date` ties `trade_date` to the IST date |
| 15m bars vs their three 5m bars | 887,490 full groups: 115 OHLC mismatches (0.013%), 148 volume mismatches beyond 1% |
| Revised or updated rows | 0 (`candle_revisions` empty) |

### B.5 Trading calendar

- `market_calendar` has 397 NSE rows, all from 2025-12-01 and all noted "Unverified weekday default (NSE holidays not loaded)". Nothing exists for 2024 to November 2025.
- Sessions are therefore inferred from bars (`loader.py:3-6`). 754 weekdays fall in the range and 43 have no bars. For 2024 and 2025 those dates match the NSE holidays I recall, but that is **unverified** and nothing in the repository confirms it. The 2026 dates are also unverified.
- 717 sessions = 711 weekday sessions + 6 weekend sessions. Special sessions present:

| Date | Day | Bars | Note |
|---|---|---|---|
| 2024-01-20 | Sat | 75 | full-length special session |
| 2024-03-02 | Sat | 21 | partial |
| 2024-05-18 | Sat | 21 | partial |
| 2024-11-01 | Fri | 12 | evening session, bars start 18:00 |
| 2025-02-01 | Sat | 75 | full-length |
| 2025-10-21 | Tue | 12 | short session |
| 2026-02-01 | Sun | 75 | full-length |
| 2026-11-08 | Sun | 11 | evening session, bars start 18:00 |

Eight dates are special; five of them are partial (11–21 bars) and three are full length. Without a calendar row, the loader replays each of these with normal 09:15–15:30 hours (`loader.py:27,59-63`). The two evening sessions fall entirely outside the replay window; the 2025-10-21 session is replayed with hours that do not match its bars.

### B.6 Corporate actions

- `corporate_actions` is **empty** (SQL), and no code under `python-engine/app` reads it (grep).
- TRD-06 §6 says intraday bars are unadjusted and that sessions whose lookback contains a split or bonus are excluded. **That exclusion is not implemented, and the stored data is not unadjusted.** Evidence that the provider returns split/bonus-adjusted history: HDFCBANK closes 972.30 → 961.80 across its late-August 2025 bonus date, NESTLEIND ≈ 1,368 in January 2024, and WIPRO ≈ 275–280 across its December 2024 bonus (SQL). None shows a step. TRD-06 §6 needs correcting.
- **Demergers are not adjusted.** TMPV opens 22.9% above the previous close on 2025-10-14 (457.15 → 561.65) and closes at 394.90 (SQL). A scan of all instrument-days with an overnight gap above 7% found no other discontinuity of that size; the other 37 hits are consistent with ordinary event days (for example 2025-04-07).
- Adjusted history is a moving target: Kite rewrites past prices when a new action occurs. All ranges were fetched on 2026-11-17..20, so they are mutually consistent today. Any later top-up will need a full refetch to stay consistent.

---

## C. Backtesting Reliability

**Classification: partially reliable.** The simulation loop is trustworthy as a mechanism. The numbers it produces are not yet trustworthy as evidence, for the data, cost and selection reasons below.

### C.1 What is sound

| Property | Finding | Evidence |
|---|---|---|
| Candle-by-candle, closed bars only | Analysis at bar *i* sees `bars_5m[:i+1]` and only the 15m bars with `end ≤` that bar's end | `replay.py:77-93` |
| Entry timing | Signal at close *t*, fill at open of *t+1*; skipped if the open gaps through the stop or beyond `max_entry_gap_pct`, or if RR degrades | `replay.py:159-190`, `app/domain/risk/fill.py:31-53` |
| No look-ahead in HTF alignment | Largest 15m bar with `end ≤` the 5m bar end | `app/domain/htf.py:20-36` |
| No look-ahead in inputs | Previous-day levels come from the previous session only; the session's bars are loaded in full but sliced per bar | `loader.py:106-125`, `replay.py:81` |
| Zone cache is not a leak | Key includes `t`, first/last bar start, close, session opens, tick, ruleset; a cache hit only re-serves a result computed from the same bars | `app/domain/zone_cache.py:35-45`, `tests/backtest/test_zone_cache.py` |
| Intrabar ambiguity | Order is: gap through stop, gap through target, session end, structure exit, stop, target. Stop and target in one bar: stop wins, reason `STOP_COLLISION` | `app/domain/risk/exits.py:35-46`, `app/backtest/trade.py:85` |
| Same-bar entry and exit | Exits are evaluated on the fill bar too, stop first | `replay.py:194-202` |
| Account limits | Daily loss, loss streak, max positions and open risk apply in-simulation and reset each session | `app/domain/risk/account.py:90-106`, `run.py` |
| Signal duplication | One open or pending order per symbol; a setup anchor is used once per session | `replay.py:233-236`, `breakout_retest.py` (`taken`) |
| Reproducibility | Run record holds ruleset, engine version, cost schedule version, universe, source and an SHA-256 of the input bars | `run.py:48-63,69-80` |
| Tests | 189 tests pass across trading, backtest and ingestion | run 2026-11-21 |

### C.2 What is not sound, or not yet known

| # | Issue | Evidence | Effect |
|---|---|---|---|
| R-1 | **Survivorship bias.** Today's 50 names for all of 2024–2026 | §B.2 | Inflates results; size unknown |
| R-2 | **Costs are unverified assumptions**, and a single schedule is used for 34 months. Slippage is a flat 0.05% applied to entries and stops only; target, session-end and structure exits get none | `app/backtest/costs.py:1`, `app/backtest/trade.py:63-91`, `run_backtest.py:86`, TRD-06 §5, OQ-BT-02 | Costs are about 0.1–0.2R per trade (earlier report, D2), the same size as any edge being searched for. Exit slippage is missing, which is optimistic |
| R-3 | **Position cap makes risk smaller than planned.** The ₹50,000 cap binds, so money at risk is about ₹270 not ₹500 | earlier report §2 D2; `sizing.py` | R-multiples are in units of a smaller, cost-heavy risk |
| R-4 | **Slot allocation is arbitrary.** Max 2 positions; candidates are ordered by `(-PAQS, symbol)`, and PAQS does not rank outcomes (earlier report D7). Ties therefore fall back to alphabetical symbol order | `replay.py:231`; 667 of the 0.1.0 run's skips were `MAX_POSITIONS_REACHED` | Which trades get taken is partly an alphabet effect; strategy comparisons that share the slot limit are confounded |
| R-5 | **Last-15-minutes regime break** changes PDH/PDL definition from 2026-08-03 | §B.3 | Affects ORB-adjacent, PDH and retest setups; the sample before and after is not like for like |
| R-6 | **Special sessions** are replayed with normal hours; 2025-10-21 is a 12-bar session treated as a full day | §B.5, `loader.py:59-63` | A handful of spurious or distorted sessions |
| R-7 | **No 1m data.** Collisions are resolved against the trader | §B.1, TRD-06 BT-04, OQ-BT-07 | Safe direction, but it understates strategies with tight targets |
| R-8 | **End-of-data trades are removed from the statistics but not from the equity curve.** `compute_metrics` filters them (`metrics.py:119-120`); `equity_curve` sums every session's `net_pnl` | `metrics.py:116-120,76-81`, `replay.py:277-287` | Trade stats and equity curve can disagree on days with an `END_OF_DATA` exit |
| R-9 | **Corporate actions:** no exclusion for demergers; TMPV 2025-10-14 sits inside five sessions' lookback | §B.6 | A false gap and false structure for TMPV for about a week |
| R-10 | **Data quality is unchecked for history**; 7 instrument-sessions have missing bars; no `data_quality_issues` rows | §B.3 | Small. Snapshot validation does not detect missing bars, so a gappy session is analysed as if complete |
| R-11 | **Multiple-testing log absent.** `backtest_runs` is empty; the earlier variants were run by an unrecorded script | SQL; earlier report §4 | A study that tries many orchestrator variants cannot show how many were tried |
| R-12 | **No end-to-end truncation-equality test for the other setups.** Such a test exists for the sweep setup (`tests/trading/test_setups_sweep.py:226`); pivots, structure and HTF have their own look-ahead tests | grep of `tests/` | I read the code paths and found no leak, but BT-01's "equal to a fresh run on the truncated series" is only machine-checked for the sweep |
| R-13 | **Sample is one market period.** 717 sessions pass TRD-06's 120-session minimum and are above its 500-session recommendation, but contain a single continuous regime sequence | TRD-06 §3 | Regime-switching claims need regime counts, not session counts |

### C.3 Prior evidence from this repository

From `docs/trading/backtests/2026-11-20-pa-intraday-0.1.0-nifty50.md` (55 sessions, Sep–Nov 2026): 176 trades, net −₹16,794, profit factor 0.52, no gross edge (−0.20R). Variant D (retest off, min stop 0.7%) was +₹345 in-sample and −₹13,310 on 164 earlier sessions. These figures were **not** re-derived in this audit. `pa-intraday 0.1.0` itself has not been replayed on January–August 2026, nor on 2024–2025.

---

## D. Strategy Readiness

Executable means: the engine can emit `ENTRY_CONFIRMED` with trade levels **and** the backtester will open a position from it.

### D.1 Direction handling (applies to all strategies)

Shorts are never executed anywhere in the stack. Four independent gates:

1. `_eligible()` returns false for any non-long setup (`app/domain/setups/signal.py:48`), so a short can never be the primary signal.
2. `trade_levels()` returns `None` for short setups (`app/domain/levels.py:88`), so no stop, target or RR exists for them.
3. `calculate_risk()` rejects with `SHORT_NOT_SUPPORTED` (`app/domain/risk/request.py:68-69`).
4. The replay hardcodes `SetupDirection.LONG` in the request it builds (`app/backtest/replay.py:243`), and `evaluate_bar_exit` and `simulate_entry` only model long positions (`exits.py`, `fill.py`).

Short setups still appear in `AnalysisResult.setups` as informational rows. They must not be counted as trades.

### D.2 Per-strategy findings

| Strategy | Long | Short | Testable now | Behaviour that matters for research |
|---|---|---|---|---|
| **OPENING_RANGE_BREAKOUT** (`app/domain/setups/opening_range.py`) | Executable. Opening range = first 15 minutes; width must be 0.3–2.0% of the low; confirms on a 5m close above `OR_high × (1 + 0.05%)`; invalidated by a close below `OR_low`; not allowed against the 15m trend | Setup built, **informational** | **Yes (long)** | Entry reference is the confirmation close. Target ladder includes a measured opening-range projection (`levels.py:98-99`). Needs a valid 15m context (`htf_against` treats "no context" as against, `common.py:30-40`) |
| **PREV_DAY_HIGH_BREAK** (`prev_day.py`) | Executable. Skipped if the session opens at or above PDH; any bar closing within 0.5% of PDH starts a setup; confirms on a close above PDH by the buffer; stop at the latest session swing low below entry | `PREV_DAY_LOW_BREAK` informational | **Yes (long), but PDH is wrong for about 9% of sessions after 2026-08-03 (D-1)** | Detection loop starts at the first bar and stops at the cutoff; one setup per session returned (`_detect_one` returns on the first hit) |
| **BREAKOUT_RETEST** (`breakout_retest.py`) | Executable. Anchors: PDH, OR high, and active non-support zones with ≥2 touches; needs a closed-bar break, then a retest within 6 bars, then a close above the retest high | **Not implemented** (module docstring, `breakout_retest.py:1`) | **Yes (long)** | The only strategy with zone dependence, so the most expensive to replay (hence the zone cache). It produced 74% of the 0.1.0 trades and is negative in both halves of that run |
| LIQUIDITY_SWEEP_REVERSAL (not in the request) | Executable only if the ruleset has `setup.liquidity_sweep_enabled`; true in `pa-intraday 0.2.0` and absent in 0.1.0 | none | Yes, with ruleset 0.2.0 | Mentioned because the orchestrator can use it. Added at HEAD `10be806` and **never backtested** (no run in `docs/trading/backtests/`) |

### D.3 What the orchestrator would need that does not exist

- **Regime features.** The methodology forbids indicators (CLAUDE.md §4, TRD-01). Regime classification would have to be built from price action only: 15m structure state (`BULLISH`/`BEARISH`/`TRANSITION`, available), opening-range width, gap vs previous close, distance to PDH/PDL, and swing counts. None is combined into a "regime" today.
- **Volume, VWAP and candlestick patterns** are not built (`CURRENT.md`, component table). The orchestrator cannot use them, and the stored data has volume only for context.
- **Trend-continuation setups and short mirrors** are not built.
- `choose_signal` returns one primary setup per symbol per bar (`signal.py:57-85`). An orchestrator that arbitrates between strategies needs all candidates, which `AnalysisResult.setups` provides.

---

## E. Critical Blockers

"Blocker" means: a result produced without resolving it should not be presented as evidence. Severity: **H** invalidates conclusions, **M** biases them, **L** adds noise.

| # | Blocker | Sev | Evidence | Resolvable inside the repo? |
|---|---|---|---|---|
| BL-1 | Survivorship: universe is today's 50; no point-in-time membership source | H | §B.2; OQ-BT-01 | **No.** Needs an external, verified membership history. Without it, results must carry the flag and be described as upper bounds |
| BL-2 | Cost schedule unverified and undated; exit slippage absent | H | §C.2 R-2; OQ-BT-02 | Partly. Verify against the owner's contract notes; add a dated schedule per period; apply slippage on all adverse exits (research harness only) |
| BL-3 | PDH/PDL definition changes on 2026-08-03 (last 15 minutes absent) | M | §B.3 D-1 | Yes. Backfill 1D from 2024-01-01 (the provider supports it, `_INTERVALS`), and derive PDH/PDL from official daily bars in the harness |
| BL-4 | CLI cannot load a 2024–2025 universe | M | §B.2 | Yes, in a research script that passes the member dictionary directly; no DB change is needed |
| BL-5 | Special sessions replayed with wrong hours | M | §B.5, R-6 | Yes. Exclude the 5 partial or evening sessions (2024-03-02, 2024-05-18, 2024-11-01, 2025-10-21, 2026-11-08), or supply session hours |
| BL-6 | Demerger discontinuity (TMPV, 2025-10-14) not handled; no corporate-action exclusion | M | §B.6 | Yes. Exclude TMPV for the sessions whose lookback contains that date; record the action |
| BL-7 | Slot allocation confounds strategy comparison (alphabetical tie-break, non-predictive PAQS) | M | §C.2 R-4 | Yes, by design: evaluate signals trade-by-trade without the slot limit first, then apply a portfolio layer with a documented, seeded tie-break |
| BL-8 | No run log for multiple testing | M | §C.2 R-11 | Yes, in the harness (write each run's config and hash to a local file) |
| BL-9 | Shorts are not executable; no 1m data | M (scope) | §D.1, §B.1 | Not without production changes. Keep the experiment long-only and say so |
| BL-10 | Historical data not quality-checked; 7 gappy instrument-sessions | L | §B.3 | Yes. Mask those sessions or use the harness to skip instrument-sessions with missing bars |
| BL-11 | End-of-data trades excluded from stats but not from equity | L | §C.2 R-8 | Yes. Report both, or exclude those sessions |
| BL-12 | Prior evidence shows no edge in any existing strategy | Context | §C.3 | n/a. Sets the prior for the experiment |

---

## F. Research Implementation Plan

Principle: **do not modify `app/domain`, `rulesets/` or the production replay.** Build the study as a separate research package that imports the engine and passes its own inputs.

### F.1 Data preparation (no engine change)

1. Decide and record the study universe. Use the 50 names with the survivorship flag on, and additionally report results on any subset the owner can verify as continuously in the index.
2. Backfill daily bars for 2024-01-01..2025-12-31 for the 50 names (the existing `market_data_cli.py backfill` path), then build PDH/PDL/PDC from the daily series in the harness instead of from 5m bars.
3. Produce a **session manifest** from the database: date, bar count per symbol, a normal/special flag. Exclude the 5 special sessions listed in BL-5. Keep the 3 full-length weekend sessions.
4. Produce an **exclusion list** for instrument-sessions: the 7 gappy ones (§B.3), and TMPV for the lookback window after 2025-10-14.
5. Verify the NSE holiday list for 2024–2026 and the cost schedule against a trusted source and the owner's contract notes, then record the sources. Until then label every output "costs assumed".

### F.2 Harness (new, outside `app/`)

6. A loader that builds `SymbolData` and `SessionSpec` directly from the database using the manifest, bypassing `universe_members` and the calendar defaults. `SymbolData`, `SessionSpec` and `SessionInput` are plain dataclasses (`replay.py:41-58`, `run.py:52-55`).
7. A parameter set built in the harness with `RulesetParams("pa-intraday", "0.2.0", values)`, with the three strategies switched on or off by filtering `AnalysisResult.setups`, not by editing the ruleset.
8. The orchestrator as an `analyse_fn` wrapper: call `analyse`, read the regime from `result.htf`, `result.levels` and `result.structure_5m`, pick which strategy's setups are allowed, and return `dataclasses.replace(result, signal=…)` using `choose_signal` over the allowed subset. `replay_session` then runs unchanged.
9. A **cost model object** per period, passed to `run_backtest` in separate runs (the replay takes one `CostSchedule` per run, `replay.py:104-110`), plus exit slippage added in the harness's own wrapper around `close_trade` if the study wants it.
10. A run ledger: each run appends config, ruleset values, input hash, code commit and result summary to a file under `docs/research/adaptive-strategy-validation/`.

### F.3 Experiment design

11. **Stage 1, signal quality without the portfolio layer.** For each strategy, record every `ENTRY_CONFIRMED` signal with its simulated outcome in R, ignoring the 2-position limit. This isolates entry quality from the alphabetical slot effect (BL-7).
12. **Stage 2, regime study.** Define regimes from price-action features only, fixed before looking at results. Report each strategy's R by regime with trade counts. Require a minimum count per cell.
13. **Stage 3, orchestrator vs static baselines.** Compare the orchestrator against each strategy alone and an equal-weight mix, on identical sessions, costs and sizing.
14. Use `walk_forward()` (`app/backtest/splits.py:40-49`: 120-session in-sample, 40-session out-of-sample) and `oos_allows_promotion` / `walk_forward_positive_in_most`; freeze rules before each out-of-sample window. Report the number of variants tried.
15. Run chunks of about 40–55 sessions one at a time. The project's own notes record out-of-memory failures at 10 parallel runs (memory: backtest runs); the earlier 164-session replay took an estimated 1.5–2 hours, so a full 717-session replay is roughly 7–9 hours single-threaded (**extrapolation, not measured**).

### F.4 Add before trusting any result

- A truncation-equality test for the harness: for a sample of bars, the signal produced in the full replay must equal the signal from a fresh `analyse` on the data truncated at that bar (BT-01).
- A reconciliation between trade statistics and the equity curve (R-8).

---

## G. Final Verdict

**Ready after minor fixes**, for the stated scope.

- **What is ready:** 34 months of 5m and 15m data for 50 names with no duplicates or invalid prices; a deterministic, look-ahead-clean replay engine with next-bar fills and conservative intrabar handling; three long strategies that are executable and testable; extension hooks (`analyse_fn`, `RulesetParams`, `AnalysisResult.setups`) that let an orchestrator be built without touching production behaviour.
- **What the "minor fixes" are:** BL-3 to BL-8 and BL-10/11 (data preparation and a harness, §F.1–F.2). None needs a change to a production strategy.
- **What stays limited even after those fixes:** BL-1 (survivorship) and BL-2 (cost verification). Results will be upper bounds until the owner supplies a point-in-time membership list and verified charges. BL-9 means no shorts and no 1-minute resolution.
- **What would change the verdict to "not ready":** an unverified cost schedule used for a claim of profitability, or a presentation of survivorship-flagged results as unbiased.

### Open questions for the owner

1. Is there a verified source for NIFTY 50 membership by date (OQ-BT-01)?
2. Can the Zerodha contract notes for the period be used to verify charges and the real slippage (OQ-BT-02)?
3. Should the three full-length weekend special sessions stay in the sample?
4. Should the study backfill 1D from 2024 (a data change, outside this audit)?
5. Does Kite serve 1m history for 2024, and is the 15:15–15:25 gap from 2026-08-03 a provider behaviour or a fetch artefact? Neither was tested here.

### Documentation discrepancies found (not fixed here)

| Document | Says | Observed |
|---|---|---|
| `CURRENT.md` (Python engine row) | Real bars stored 2026-01-01..2026-11-19 | Stored from 2024-01-01 |
| TRD-06 §3, ARC-08 §4.0 | Kite equity bars end at 15:15 | 75-bar sessions through 2026-07-31; 72-bar sessions only from 2026-08-03 |
| TRD-06 §6 | Intraday bars unadjusted; split/bonus sessions excluded | Split/bonus history is provider-adjusted; no exclusion in code; demergers unadjusted |
| `docs/trading/backtests/2026-11-20-…md` §4 | Variants A–D run by a temporary script | Script not in the repository; runs not reproducible from it |
