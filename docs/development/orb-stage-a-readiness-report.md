# ORB Stage A Readiness Report

| Field | Value |
|---|---|
| Version | 1.0.0 (2026-11-25) |
| Status | **Preparation, evidence and proposals only. Nothing in this report was executed against the database or the strategy.** D1.7 is NOT authorised and was not performed. No D2-D6 mutation, P0-1/P0-1b, backtest, service restart, candle change, schema change, B0/`ORB-MG-02`/PAQS/ruleset change, live trading, T-I165 execution, commit or push |
| Independence | Every finding is **AI-assisted and NON-INDEPENDENT**. DR-11 covers D1 only; **DR-7 and DR-7a remain applicable to D2-D6** and are not bypassed. No independent human sign-off is claimed |
| Evidence | `~/priceaction-backups/d1-20261125/stage-a-evidence/` (706 files, 242 MB; `MANIFEST.tsv`, `SHA256SUMS`, `ACQUISITION_MANIFEST_BHAVCOPY.tsv`) and the earlier `.../evidence/` |
| Builds on | [Data foundation report](orb-data-foundation-report.md), [D1 results](orb-d1-results.md), [validation plan](../research/orb-validation-plan.md), [Phase 2 readiness](orb-phase2-decisions-and-readiness.md) |
| Labels | **VERIFIED** reproduced from primary data or an official document read in this session; **INFERRED** consistent evidence, not proof; **UNKNOWN** no evidence; **UNVERIFIABLE** cannot be checked with available means; **UNRESOLVED** evidence conflicts or is insufficient |

## 0. Executive summary

> **Update (later on 2026-11-25).** The 14 `SCALE_UNVERIFIABLE` sessions were re-tested with an exact comparison of the 5m session open, high and low against NSE's (all 14 are on the traded scale). The corrected matrix is **23,509 traded-scale / 8,991 provider-adjusted / 0 unverifiable** and tick status **23,509 pass / 8,991 unverifiable / 0 fail**; see the [finalisation roadmap §3](orb-stage-a-finalisation-roadmap.md#3-critical-data-quality-questions-batch-3). The figures below are the original ones and are kept for the record.

1. **Collection done, no gaps.** 717 NSE bhavcopy files cover every stored session of the development window (650) and the reserve window (67): 674 downloaded in this run, 43 already held, **0 missing, 0 failed**. All came from the public archive (no login, cookie or API). The development window has **650** sessions, not the "about 450" in the brief; the extra 67 reserve sessions were fetched to resolve the TMPV, HINDUNILVR and November-2025 events (a deviation from the stated scope, §1.4).
2. **Price-scale matrix (32,500 instrument-sessions, 50 × 650).** `TRADED_SCALE_VERIFIED` **23,495** (72.3%); `PROVIDER_ADJUSTED` **8,991** (27.7%); `SCALE_UNVERIFIABLE` **14**; `SCALE_UNKNOWN` **0**. 28 instruments are on the traded scale in every session; 22 are not in some.
3. **Tick status for the same 32,500 sessions:** `TICK_VERIFIED_PASS` **23,495**, `TICK_VERIFIED_FAIL` **0**, `TICK_UNVERIFIABLE` **9,005**, `TICK_UNKNOWN` **0**. Every session that can be checked is on the resolved tick grid.
4. **Calendar reconciled with official circulars.** 42 of the 43 stored no-data weekdays match an NSE holiday circular read in full (including the amendments of 2024-05-20, 2024-11-20 and 2026-01-15); **2024-01-22** is INFERRED (amendment circular not fetched). Every weekend and Muhurat session is accounted for. The earlier 39 = 43 minus the 4 reserve-window holidays (§3.3).
5. **The 21 "unresolved" price steps now have exact ex-dates and sizes** (all fit cash dividends with round amounts); their identity is still INFERRED. The ITC and TMPV provider factors differ from the exchange's price discovery and stay UNRESOLVED (§3.1).
6. **Stage A input eligibility:** 32,145 of 32,500 instrument-sessions are eligible inputs; 355 are excluded (350 special sessions, 5 opening-range gaps). Range validity (`ORB-MG-02` OHLC rules) is not evaluated here; that is P0-1/E3.
7. **Correction to my earlier report.** I advised starting E9 prospective capture early. The approved plan and your OD-16 preference say **no early log**: capture may start only after the freeze package. E9 is prepared early (design, tests), not activated (§6, §7).
8. **A real conflict to settle before Stage A:** the 4b prospective trade floor (100 trades) may be unreachable under the planning account limits, and the feasibility count that would show it (P0-1b) is not approved (§5.3).
9. **Shortest path:** one decision batch, then three parallel tracks (data freeze and D6, engineering E1-E8/E10/E11, governance). Prospective capture, verified costs, survivorship repair and live trading do **not** block the first historical Stage A (§8).

## 1. Daily bhavcopy collection and price-scale matrix

### 1.1 Acquisition (VERIFIED)

| Item | Result |
|---|---|
| Source | `https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv` (public NSE archive) |
| Method | Sequential, about one request per second, one retry on transport failure, `.part` file renamed only on HTTP 200; no login, no session cookie, no restricted API; generic client string |
| Sessions covered | 650 `DEVELOPMENT` + 67 `RESERVE` = 717 stored sessions, 2024-01-01 to 2026-11-19 |
| Outcome | 674 downloaded, 43 already held from the earlier collection, **0 missing, 0 non-200** |
| Missing files | None. A missing file would have been recorded `MISSING` and its sessions `SCALE_UNVERIFIABLE`; no session was fabricated |
| Date check | Each file's own `DATE1` column equals its session date for all 650 development sessions (a holiday file carries the previous day's date) |
| Preserved | Original files untouched; fetch logs `bhav_fetch_log.txt`, `bhav_fetch_log_reserve.txt` |
| Manifest | `ACQUISITION_MANIFEST_BHAVCOPY.tsv`: session date, data class, file, size, acquisition time (UTC), SHA-256, URL, status (717 rows); `MANIFEST.tsv` and `SHA256SUMS` cover all 706 files; all sums verify |
| Use limits | Local personal research; attribution and URLs kept; **not redistributed; no licensing clearance claimed** (owner decision S-7) |
| Also collected (11 official circulars retrieved; 10 read in full) | NSE/CMTR/59722, 61518, 64960, 65587, 71775, 72260 (holidays and amendments), NSE/MSD/60942 and NSE/CMTR/60209 (special sessions); NSE/CMTR/61302 and 60129 (DR and mock sessions, not relevant to the data); NCL/CMPT/59922 (retrieved, not read) in `circulars/` |

### 1.2 Method of the price-scale classification

The stored daily close of each instrument-session (Kite) is divided by the NSE **unadjusted** close of the same session (symbol aliases: `ZOMATO`→`ETERNAL`, `TATAMOTORS`→`TMPV`). The result was cross-checked against the session's last 5m bar.

| Class | Rule |
|---|---|
| `TRADED_SCALE_VERIFIED` | Kite close / NSE close within 0.06% of 1 **and** the last 5m bar agrees with the daily scale within 3% |
| `PROVIDER_ADJUSTED` | ratio differs from 1 by more than 0.06% (the exact ratio is stored; each instrument has its own history) |
| `SCALE_UNKNOWN` | the symbol is not in the official file or there is no Kite daily bar |
| `SCALE_UNVERIFIABLE` | no same-day official file, a file dated another day, or the intraday bar disagrees with the daily scale by more than 3% |

Intraday scaling equals daily scaling (VERIFIED by the 5m cross-check). **Result (32,500 instrument-sessions):** 23,495 / 8,991 / 14 / 0 as in §0. The 14 `SCALE_UNVERIFIABLE` sessions are 13 on 2026-08-31/09-18/09-29 (after the closing-auction change, when the last continuous price and the official close can differ by 3-4%; INFERRED) and ETERNAL 2025-01-20 (UNKNOWN cause).

Limits: (a) a ratio of exactly 1 proves the stored prices equal the traded prices on that session, not that they equal them at every later re-fetch; (b) the provider may re-adjust history after a future event, so the matrix is dated **2026-11-25** and must be rebuilt after any new event (a freeze is needed, §5.2); (c) dividend adjustments do not appear for every dividend (HCLTECH, for example, never shows one), so the provider's dividend rule is UNKNOWN.

### 1.3 Matrix by instrument (full per-session rows in `analysis/price_scale_matrix_dev.csv`, `analysis/tick_status_dev.csv`, `analysis/stage_a_input_eligibility_dev.csv`)

| # | Symbol | Sessions | `TRADED_SCALE_VERIFIED` | `PROVIDER_ADJUSTED` | `SCALE_UNVERIFIABLE` | `TICK_VERIFIED_PASS` | `TICK_UNVERIFIABLE` | Provider steps ≥0.5% | Excluded (special / OR gap) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ADANIENT | 650 | 217 | 431 | 2 | 217 | 433 | 1 | 7 |
| 2 | ADANIPORTS | 650 | 648 | 0 | 2 | 648 | 2 | 0 | 7 |
| 3 | APOLLOHOSP | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 4 | ASIANPAINT | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 5 | AXISBANK | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 6 | BAJAJ-AUTO | 650 | 285 | 365 | 0 | 285 | 365 | 1 | 7 |
| 7 | BAJAJFINSV | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 8 | BAJFINANCE | 650 | 289 | 361 | 0 | 289 | 361 | 1 | 7 |
| 9 | BEL | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 10 | BHARTIARTL | 650 | 648 | 0 | 2 | 648 | 2 | 0 | 8 |
| 11 | CIPLA | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 12 | COALINDIA | 650 | 12 | 638 | 0 | 12 | 638 | 3 | 7 |
| 13 | DRREDDY | 650 | 445 | 205 | 0 | 445 | 205 | 1 | 7 |
| 14 | EICHERMOT | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 15 | ETERNAL | 650 | 648 | 0 | 2 | 648 | 2 | 0 | 7 |
| 16 | GRASIM | 650 | 643 | 7 | 0 | 643 | 7 | 0 | 7 |
| 17 | HCLTECH | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 18 | HDFCBANK | 650 | 239 | 411 | 0 | 239 | 411 | 1 | 8 |
| 19 | HDFCLIFE | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 20 | HINDALCO | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 21 | HINDUNILVR | 650 | 219 | 431 | 0 | 219 | 431 | 1 | 7 |
| 22 | ICICIBANK | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 8 |
| 23 | INDIGO | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 24 | INFY | 650 | 13 | 637 | 0 | 13 | 637 | 2 | 7 |
| 25 | ITC | 650 | 121 | 528 | 1 | 121 | 529 | 3 | 8 |
| 26 | JIOFIN | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 27 | JSWSTEEL | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 28 | KOTAKBANK | 650 | 210 | 440 | 0 | 210 | 440 | 1 | 7 |
| 29 | LT | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 30 | M&M | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 31 | MARUTI | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 32 | MAXHEALTH | 650 | 649 | 0 | 1 | 649 | 1 | 0 | 7 |
| 33 | NESTLEIND | 650 | 250 | 400 | 0 | 250 | 400 | 2 | 7 |
| 34 | NTPC | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 35 | ONGC | 650 | 6 | 644 | 0 | 6 | 644 | 4 | 7 |
| 36 | POWERGRID | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 37 | RELIANCE | 650 | 445 | 205 | 0 | 445 | 205 | 1 | 7 |
| 38 | SBILIFE | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 8 |
| 39 | SBIN | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 40 | SHRIRAMFIN | 650 | 393 | 256 | 1 | 393 | 257 | 1 | 7 |
| 41 | SUNPHARMA | 650 | 649 | 0 | 1 | 649 | 1 | 0 | 7 |
| 42 | TATACONSUM | 650 | 509 | 141 | 0 | 509 | 141 | 1 | 7 |
| 43 | TATASTEEL | 650 | 295 | 355 | 0 | 295 | 355 | 2 | 7 |
| 44 | TCS | 650 | 649 | 0 | 1 | 649 | 1 | 0 | 7 |
| 45 | TECHM | 650 | 97 | 553 | 0 | 97 | 553 | 3 | 7 |
| 46 | TITAN | 650 | 650 | 0 | 0 | 650 | 0 | 0 | 7 |
| 47 | TMPV | 650 | 218 | 431 | 1 | 218 | 432 | 1 | 7 |
| 48 | TRENT | 650 | 117 | 533 | 0 | 117 | 533 | 1 | 7 |
| 49 | ULTRACEMCO | 650 | 78 | 572 | 0 | 78 | 572 | 1 | 7 |
| 50 | WIPRO | 650 | 203 | 447 | 0 | 203 | 447 | 3 | 7 |

### 1.4 Deviation from the stated scope (needs your acknowledgement, S-1)

The brief said "approximately 450" files. The development window actually holds 650 sessions (and the reserve window 67). I fetched all 717 because (i) the scale test needs every session, (ii) the TMPV 2025-10-14 and HINDUNILVR 2025-12-05 events and the November-2025 steps fall in the reserve window. This is read-only, public and small (242 MB), but it exceeds the brief's number.

## 2. Consolidated D2-D4 data-quality findings

### 2.1 D2 corporate actions

**Method.** The exact session on which the provider's stored scale changes was found from the daily ratio (Kite close / NSE close) between consecutive sessions. NSE's bhavcopy `PREV_CLOSE` is the **raw** previous close (RELIANCE 2024-10-28: `PREV_CLOSE` 2,655.70, unadjusted), so exchange adjustment factors **cannot** be read from it; this route was tested and discarded (VERIFIED).

**Result: 35 provider steps of 0.5% or more across 21 instruments** (27 further wiggles of 0.1-0.2% are rounding noise and are ignored; the 22nd instrument with adjusted sessions, GRASIM, has one such 0.4% step):

| Symbol | Ex-session (provider step) | Step | Implied ₹/share if cash | Identification | Status |
|---|---|---|---|---|---|
| ADANIENT | 2025-11-17 | ×1.0315 | 76.8 | partly-paid rights issue (ex 2025-11-17) | INFERRED (dated secondary sources) |
| BAJAJ-AUTO | 2025-06-20 | ×1.0253 | 210.0 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| BAJFINANCE | 2025-06-16 | ×10.0011 | 8398.0 | 1:2 split + 4:1 bonus (ex 2025-06-16) | INFERRED (dated secondary sources) |
| COALINDIA | 2024-11-05 | ×1.0369 | 15.77 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| COALINDIA | 2025-11-04 | ×1.0270 | 10.23 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| COALINDIA | 2026-11-04 | ×1.0258 | 10.25 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| DRREDDY | 2024-10-28 | ×5.0000 | 5211.75 | 1:5 split (record/ex 2024-10-28) | INFERRED (dated secondary sources) |
| HDFCBANK | 2025-08-26 | ×2.0001 | 982.1 | 1:1 bonus (ex 2025-08-26) | INFERRED (dated secondary sources) |
| HINDUNILVR | 2025-12-05 | ×1.0195 | 47.0 | Kwality Wall's demerger (record 2025-12-05) | INFERRED (dated secondary sources) |
| INFY | 2026-06-10 | ×1.0217 | 25.08 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| INFY | 2026-11-03 | ×1.0229 | 26.0 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| ITC | 2025-01-06 | ×1.1561 | 65.01 | ITC Hotels demerger (record 2025-01-06) | UNRESOLVED magnitude (see 3.1) |
| ITC | 2026-02-04 | ×1.0211 | 6.55 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| ITC | 2026-05-27 | ×1.0272 | 8.0 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| KOTAKBANK | 2026-01-14 | ×5.0002 | 1706.1 | 1:5 split (record 2026-01-14) | INFERRED (dated secondary sources) |
| NESTLEIND | 2024-01-05 | ×10.0001 | 24404.8 | 1:10 sub-division, ISIN change (NSE/CML/60084) | VERIFIED (NSE circular) |
| NESTLEIND | 2025-08-08 | ×2.0000 | 1117.3 | 1:1 bonus, record 2025-08-08 (NSE/CML/69475) | VERIFIED (NSE circular) |
| ONGC | 2024-11-19 | ×1.0245 | 6.0 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| ONGC | 2025-11-14 | ×1.0246 | 6.02 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| ONGC | 2026-02-18 | ×1.0235 | 6.25 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| ONGC | 2026-11-12 | ×1.0353 | 8.0 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| RELIANCE | 2024-10-28 | ×2.0000 | 1327.85 | 1:1 bonus (ex 2024-10-28) | INFERRED (dated secondary sources) |
| SHRIRAMFIN | 2025-01-10 | ×5.0002 | 2247.9 | 1:5 split (record 2025-01-10) | INFERRED (dated secondary sources) |
| TATACONSUM | 2024-07-26 | ×1.0124 | 15.0 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| TATASTEEL | 2024-06-21 | ×1.0201 | 3.6 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| TATASTEEL | 2025-06-06 | ×1.0233 | 3.6 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| TECHM | 2024-07-19 | ×1.0185 | 28.0 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| TECHM | 2025-07-04 | ×1.0183 | 30.04 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| TECHM | 2026-07-03 | ×1.0260 | 36.0 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| TMPV | 2025-10-14 | ×1.4524 | 205.8 | Tata Motors demerger (record 2025-10-14) | UNRESOLVED magnitude (see 3.1) |
| TRENT | 2026-06-04 | ×1.5000 | 1419.2 | 1:2 bonus (record/ex 2026-06-04) | INFERRED (dated secondary sources) |
| ULTRACEMCO | 2026-07-30 | ×1.0204 | 240.0 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| WIPRO | 2024-12-03 | ×1.9996 | 292.22 | 1:1 bonus (ex 2024-12-03) | INFERRED (dated secondary sources) |
| WIPRO | 2025-01-28 | ×1.0198 | 5.99 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |
| WIPRO | 2026-01-27 | ×1.0258 | 6.0 | cash-dividend-like (amount is round) | UNRESOLVED identity (exact ex-date and size now known; NSE announcement not collected) |

**Findings.**
1. **The 21 formerly unresolved steps** (BAJAJ-AUTO, COALINDIA ×3, INFY ×2, ITC ×2, ONGC ×4, TATACONSUM, TATASTEEL ×2, TECHM ×3, ULTRACEMCO, WIPRO ×2) now have an exact ex-session and size. Every one implies a round per-share amount (₹3.6, 6, 6.25, 8, 10.25, 15, 28, 30, 36, 210, 240, ...), which fits a cash dividend. Identity is **INFERRED**; the amounts and dates are not checked against NSE announcements (not collected).
2. **ITC demerger discrepancy (UNRESOLVED).** The provider's step on 2025-01-06 is ×1.156 (implied ₹65 of ₹481.6, 13.5%). The exchange's special pre-open discovery moved ITC from ₹482 to about ₹455.6 (about 5.5%, per news). The provider scales **more than twice** as much as the exchange did.
3. **TMPV demerger discrepancy (UNRESOLVED).** The provider's step on 2025-10-14 is ×1.452 (it keeps 68.85% of the pre-demerger price, implied ₹205.8 of ₹660.75). The exchange's price discovery put TMPV at about ₹400 (it kept about 60.5%). The provider's factor differs by about 8 percentage points.
4. **HINDUNILVR, ADANIENT** steps are small (×1.019, ×1.031) and fit the reported events; sizes not checked against the exchange.
5. **The earlier claim "demergers are not adjusted" is contradicted** (ITC, TMPV, HINDUNILVR are scaled by the provider).
6. **Effect on B0:** a session's bars share one constant scale, so range, breakout (×1.0005), stop and fixed 2R target are scale-invariant. What the scale breaks is **tick-grid verification** and **any rupee-based cost or slippage**.
7. **Adjustment factors are not invented or applied.** No candle was changed.

**Eligibility rule proposed for the corporate-action days (decision S-2).** The plan (§2.3, L-6) says corporate-action windows are excluded but does not define the window. DR-3a approved the principle "affected = intersects the actual strategy input and lookback" and **rejected a fixed five-session window**. B0's only input is the same session's 5m bars, so the proposal is: (a) keep event-day sessions with an intact opening range, flagged `PROVIDER_ADJUSTMENT_EX_DAY`; (b) exclude sessions whose opening range is broken (the three demerger days, already caught by `OR_MISSING_BAR`); (c) report both ways in Stage A as a sensitivity. In the development window there are **30** such ex-day instrument-sessions. The owner must confirm or define L-6.

### 2.2 D3 historical tick sizes

| Result | Count (32,500 sessions) |
|---|---|
| `TICK_VERIFIED_PASS` (traded-scale session, every 5m OHLC value on the resolved grid) | **23,495** |
| `TICK_VERIFIED_FAIL` | **0** |
| `TICK_UNVERIFIABLE` (price scale is not the traded scale) | **9,005** (8,991 provider-adjusted + 14 scale-unverifiable) |
| `TICK_UNKNOWN` (tick cannot be determined) | **0** |

The tick for each instrument-month is resolved from the **two NSE circulars read in full** (NSE/CMTR/62174: 0.05 flat to 2024-06-09, then below ₹250 → 0.01, monthly review; NSE/CMTR/67133: ladder from 2025-04-15) and the NSE unadjusted close of the previous month's last session (`analysis/tick_status_dev.csv` states the reference date for every row). The same resolver reproduces Kite's recorded tick for all 50 instruments in November 2026 (VERIFIED in the earlier report). **No `TICK_VERIFIED_FAIL` exists in the development window**, so under MG02-A1 no session would be excluded by the tick clause; 27.7% simply cannot be checked and are **not failures** (approved policy). MG02-A1 is **not adopted** by this report (decision R-3). Limits: circulars after April 2025 that might change the ladder were not found (UNKNOWN beyond my search); the corporate-action transition months follow the circular rule "existing tick continues until the next review", which equals the monthly rule used.

### 2.3 D4 market calendar (official circulars)

| Year | Circular(s) read | Weekday holidays in the circular(s) | Stored sessions agree |
|---|---|---|---|
| 2024 | NSE/CMTR/59722; amendments NSE/CMTR/61518 (2024-05-20), NSE/CMTR/64960 (2024-11-20) | 14 listed (incl. 2024-11-01 Muhurat) + 2 amendments | 15 of 16 no-data weekdays verified (13 listed + 2 amendments); **2024-01-22** (special holiday) is the 16th: its amendment circular was **not** fetched; two search results say NSE declared it (INFERRED) |
| 2025 | NSE/CMTR/65587 | 14 (incl. 2025-10-21 Muhurat) | **13 of 13**; 2025-10-21 traded as a Muhurat session |
| 2026 | NSE/CMTR/71775; amendment NSE/CMTR/72260 (2026-01-15, CM segment) | 15 + 1 amendment | **14 of 14** through 2026-11-19 (2026-11-24 and 2026-12-25 are in the future) |

**Reconciliation of 43 versus 39 (VERIFIED arithmetic).** The data window has 43 no-data weekdays (2024: 16, 2025: 13, 2026: 14). The D0 package's 39 counted only the development window and omitted the four holidays inside the reserve window (2025-10-02, 2025-10-22, 2025-11-05, 2025-12-25): 43 − 4 = 39.

**Weekend and special sessions with data (all 50 instruments):** Sat 2024-01-20 (special live session with DR switch; circular reference NSE/CMTR/59999 cited by NSE/CMTR/60209, not fetched; full-length bars in the data, INFERRED normal timings), Sat 2024-03-02 (NSE/MSD/60942, VERIFIED; 21 bars), Sat 2024-05-18 (DR session; circular not fetched; 21 bars), Fri 2024-11-01 Muhurat (NSE/CMTR/59722, VERIFIED), Sat 2025-02-01 and Sun 2026-02-01 (Budget days; no circular collected; full-length), Tue 2025-10-21 Muhurat (NSE/CMTR/65587, VERIFIED), Sun 2026-11-08 Muhurat (NSE/CMTR/71775, VERIFIED). Muhurat timings come from later circulars that were not collected.

**Session end.** From **2026-08-03** continuous cash trading ends at 15:15 (75 regular sessions with 72 bars ending 15:10). Evidence: the bars (VERIFIED) and news plus a SEBI document (INFERRED for the rule; the NSE circular was not collected). A further change from 2026-12-07 is reported by one source (UNVERIFIED).

**`market_calendar` table:** 397 rows, 284 of them "Unverified weekday default"; 15 holidays marked trading and 2 traded weekend sessions marked closed (17 wrong rows); no rows before 2025-12. Proposal: rebuild it from these circulars with date-versioned session end (decision S-4). No database write was made.

### 2.4 Stage A input eligibility (32,500 instrument-sessions)

| Outcome | Count | Reason |
|---|---|---|
| Eligible input | **32,145** | |
| Excluded | **355** | 350 special sessions (7 dates × 50: Sat 2024-01-20, 2024-03-02, 2024-05-18, Fri 2024-11-01, Sat 2025-02-01, Sun 2026-02-01, Sun 2026-11-08), L-4; 5 opening-range gaps (BHARTIARTL, HDFCBANK, ICICIBANK, SBILIFE on 2024-06-25; ITC on 2025-01-06), `OR_MISSING_BAR` |
| Flags (not exclusions) | 3,800 sessions from 2026-08-03 (session end 15:10, L-3); 30 provider-adjustment ex-days; 8,991 adjusted-scale sessions; 9,005 `TICK_UNVERIFIABLE` | |

Not evaluated here: `ORB-MG-02` OHLC validity and duplicates inside the opening range (that is E3/P0-1), instrument identity exclusions for the four test artifacts (already outside the 50), and the `RESERVE` window (outside Stage A).

## 3. D5 completion preparation (nothing run)

**Targets (VERIFIED from bars):** the 5 development sessions with missing opening-range bars (rows 1-5) plus the 2 reserve ones (TMPV 2025-10-14, HINDUNILVR 2025-12-05); see the earlier report §4. The three demerger days (ITC, TMPV, HINDUNILVR) coincide with record dates and special pre-open sessions (INFERRED); the 2024-06-25 cause is UNKNOWN.

**Re-fetch tool specification (proposal; to be built only after approval, decision S-5).**

| Aspect | Specification |
|---|---|
| Name and place | `python-engine/scripts/refetch_opening_bars.py` (new); no application import of the database layer |
| Inputs | a reviewed JSON target list (symbol, date, timeframe); an output directory; `--dry-run` (prints the requests, no network) |
| Provider call | the existing `KiteProvider` historical endpoint through `FileTokenSupplier`; a thin raw-response wrapper keeps the **raw bytes** (the current `fetch_bars` parses and discards them, so a small additive wrapper is required) |
| Rate | at most 3 requests per second (provider limit), with back-off; a failed or partial response is recorded, never retried silently |
| Output | per request: raw response bytes, request parameters (JSON), HTTP status, fetch time (UTC), SHA-256; a `MANIFEST.tsv` and `SHA256SUMS`; files made read-only; directory mode 0700; a comparison report against the stored bars |
| Never | open a database connection, write to `candles`, overwrite or delete any file, print a token or API key, or log a response header containing credentials |
| Tests | unit tests with recorded fake payloads; a test that the tool imports no database module; a test that the output directory is the only write target; a test that a missing or expired token fails closed; a hash-stability test |
| Estimate | 2-3 engineer-days (estimate) |

**Broker session and secure authentication.** The repository already has the right mechanism: the owner runs `uv run python scripts/kite_login.py` in their own terminal; the Zerodha login page opens in their browser; they paste the redirect address into the terminal prompt; the access token is written to `.kite_token` (mode 0600, gitignored) and expires at the next 06:00 IST; `FileTokenSupplier` reads it just in time and never caches or logs it. **No credential is typed or pasted into chat, and no token is read or printed by the assistant.** The assistant may check only that the file exists and its age. A valid Kite Connect historical-data entitlement is assumed because the 2024-2026 backfill used the same endpoint (not verified here). The first run needs a trading-day login the same morning; no re-fetch has been run.

## 4. D6 and validation governance (proposal; AI-assisted, NON-INDEPENDENT)

### 4.1 Tick-status contract (for approval, decision S-8)

Statuses and rules are as in §2.2 (`TICK_VERIFIED_PASS`, `TICK_VERIFIED_FAIL`, `TICK_UNKNOWN`, `TICK_UNVERIFIABLE`). Only `TICK_VERIFIED_FAIL` is a tick-based hard failure; unknown and unverifiable are never failures. Prerequisites: the MG02-A1 formal adoption decision, the resolver specification (the two circulars plus the monthly-close rule), the per-session scale flag, and the freeze below.

### 4.2 Dataset freeze procedure (decision S-9)

1. Record the commit hash of the engine and the scripts, and the exact D0/D1 manifests.
2. Fix the date range, instrument list (the 50), data classes and the session list (650 + the reserve exclusion).
3. Hash every input: the candle tables per class (the D0 manifest method), the 717 bhavcopy files (SHA-256 list), the circulars, the identity map, the calendar rows and the scale, tick and eligibility matrices.
4. Make the evidence folder read-only; copy it to a second location on this Mac (the off-device waiver, DEC-032, still applies).
5. Write a freeze record (hashes, counts, date, who ran what) and register it in `DECISIONS.md`.
6. **Any later re-fetch, provider re-adjustment or new circular voids the freeze** and requires a new one.

### 4.3 Counts-only P0-1 contract

Re-state the approved contract unchanged: counts only; development data only; allowed outputs are instrument-sessions per class and month, exclusions by reason, `MG-02` sub-reasons, the four tick statuses, scale-class counts and coverage; **forbidden:** any return, price-movement, edge, ranking, control comparison, **and any signal or trade count (P0-1b stays unapproved)**. Output is in a fixed layout (alphabetical symbol, ascending date). The scan runs on the frozen data, twice (a second independent implementation), and the two outputs must match.

### 4.4 Review and evidence required

| Requirement | Status |
|---|---|
| Frozen dataset with hashes | Not done (S-9) |
| Two implementations of the scan, outputs identical | Not built (E10) |
| **Independent human review of the preparation (DR-7, DR-7a)** | **OPEN, no reviewer named.** Claude's review is NON-INDEPENDENT and cannot satisfy it |
| Owner approval of the contract (S-8) and an explicit run authorisation | Not given |

What Claude can do without a human: build and run checks, reproduce counts, prepare evidence and records. What needs a human (or an explicit owner decision to extend DR-11): the sign-off on curated D2-D4 data and on D6's preparation.

## 5. OD-8, OD-15 and OD-16: one owner decision document

### 5.1 OD-8: engineering scope (recommended: step-wise approval)

| Step | Items | Exact scope (proposed files) | Gate |
|---|---|---|---|
| 1 (fidelity and validation first) | **E1, E3, E7** | `app/domain/strategies.py` registry entry for the existing detector; a pure strict range validator `ORB-MG-02` with the sub-reasons; tests with TRD-08-style vectors, truncation-equality, replay-equivalence and the isolation proof | OD-8 step 1 |
| 2 | **E2, E4, E5** | a new research ruleset `pa-intraday/0.6.0.json` with `role = RESEARCH` (never `LIVE`) and the TRD-01 §6 registry update; the B0 path (three timestamps, targets T1-T4); the B0 run settings (structure exit off, no score gate) | step 1 passed; ruleset hashes |
| 3 | **E8, E10, E11** | run-record extensions, pre-registration file with commit and ruleset hashes; the P0-1 scan tool plus its second implementation; the 1,000-replicate benchmark | steps 1-2 |
| 4 | **E6** | matched random-entry control, statistics, the calibration of the interval method | OD-15 |
| 5 (design only) | **E9** | design, tests and dry runs of prospective capture; **no activation** | OD-16 freeze |

`0.1.0`-`0.5.0` rulesets, B0, `ORB-MG-02`, PAQS and released rulesets are not edited.

### 5.2 OD-15: matched random-control design and interval method (recommended: option (a))

As written in [plan §4.2](../research/orb-validation-plan.md#42-the-matched-random-entry-control-mtc): the control matches universe, sessions, entry-time distribution, trade frequency per instrument-month, direction (long only), risk and exit assumptions, costs and slippage, and portfolio constraints (4a none beyond one position per symbol; 4b the account limits); invalid ranges and special sessions are removed from ORB **and** every control alike; 1,000 seeded replicates; month-block bootstrap with the interval method chosen **only** by the predeclared calibration of [plan §4.6](../research/orb-validation-plan.md#46-interval-calibration-predeclared-not-run) (screening thresholds already accepted: coverage ≥ 98.0%, false positive ≤ 1.5% at both 60 and 120 sessions). If no method passes, the alternatives return to the owner; nothing is relaxed silently.

### 5.3 OD-16: prospective protocol and the unresolved conflicts (recommended: option (a), no early log)

**Protocol (plan §8, unchanged):** freeze package → capture only afterwards → append-only signal log with commit hash → 100 qualifying filled trades over at least 60 sessions in each of 4a and 4b **and** a 99% half-width of the gross edge ≤ 0.05R (4a) → judged only at 60 and 120 sessions → `INCONCLUSIVE` at 120 if either fails → width-only interim reports.

**Statistical acceptance criteria for Stage A (plan §4.4):** integrity gate (P0-3 zero differences, P0-4 passes, matching checks pass, run record complete, **≥ 1,000 filled B0 trades pooled in 4a**); `A-CONTINUE` if Δ ≥ +0.05R, lower bound of the 99% interval > 0, gross mean R > 0 and Δ > 0 in at least two of three parts; `A-STOP` if the upper bound < +0.05R; otherwise `A-INCONCLUSIVE`.

**Data-integrity requirements (from this report):** frozen and hashed input; per-session scale and tick flags; calendar from circulars with date-versioned session end; excluded sessions listed with reasons; costs flagged `costs_unverified`.

**Conflicts and gaps the owner should settle.**
1. **4b trade floor versus account limits (INFERRED, not quantified).** Planning values give ₹1,00,000 capital and ₹50,000 per position, i.e. about two concurrent positions. In 4b the 100-trade floor over 60 sessions is therefore plausible only if positions turn over; the count is unknown because P0-1b (the feasibility count) is **not approved**. Risk: `INCONCLUSIVE_TRADE_COUNT` after months of capture. Options: approve a P0-1b limited to 4b feasibility (counts only), lower the 4b floor before any data (a protocol change), or accept the risk.
2. **1,000 (historical, pooled, 4a) versus 100 (prospective, per configuration, 4a and 4b)** are different populations by design ([plan §4.5](../research/orb-validation-plan.md#45-what-the-sample-size-thresholds-count-clarification-2026-11-23)); no conflict in the text, but the precision rule at 60 sessions (≤ 0.05R half-width) practically needs a 4a trade count of the order of 1,000. Planning scale (M1: about 0.4 trades per instrument-session) suggests about 1,200 trades over 60 sessions × 50 instruments (a planning figure, not a result), so the margin is thin.
3. **Week blocks versus the calibration.** About 12 blocks at 60 sessions cannot support a 99% interval (plan §4.6); the method is undecided until the calibration runs. The development data hold about 650 sessions, so real-window coverage cannot be verified (the plan says so).
4. **"Start E9 early" versus "no early log".** My earlier suggestion is withdrawn: only design and tests are prepared early.
5. **Which sessions count as development.** 2026 exposed sessions are `DEVELOPMENT` (plan §2.1), so Stage A is optimistic by construction; the reserve window (67 sessions) is retrospective supportive evidence only.

## 6. E1-E11 execution matrix

Efforts are my estimates in engineer-days (wide uncertainty). "Existing" means code already in the repository.

| Item | Description | Blocks Stage A? | Existing implementation | Missing | Depends on | Verification | Effort | Order |
|---|---|---|---|---|---|---|---|---|
| E1 | Register `opening_range_breakout` (today's detector unchanged) | **Yes**: no isolated ORB run exists | `app/domain/strategies.py` registry (2 strategies); `detect_opening_range` in `app/domain/setups/opening_range.py` | the registry entry; isolation proof | OD-8 step 1 | P0-3: single-strategy ORB candidates equal the ORB candidates of a full `analyse()` run, 0 differences | 0.5 | 1 |
| E2 | New research ruleset with `orb.*` keys | **Yes**: B0 and variants need keys that do not exist | `app/rulesets.py` roles (`LIVE`/`RESEARCH`/`RETIRED`), `rulesets/pa-intraday/0.1.0-0.5.0`, ruleset integrity tests | `0.6.0.json`, role entry, TRD-01 §6 update | OD-8 step 2, TRD-01 | role test and hash check pass; released files unchanged | 1-2 | 4 |
| E3 | Strict `ORB-MG-02` range validator | **Yes**: a missing bar silently changes today's range | none (today's detector is not strict) | pure validator with sub-reasons; tick clause only if MG02-A1 is adopted | spec §7.1.2; R-3 for the tick clause | boundary tests per sub-reason; 7 extra MG02-A1 vectors (if adopted) | 2-3 | 2 |
| E4 | B0 detector path with switches and targets T1-T4 | **Yes** | current ORB detector (15m lock-out, target ladder) | B0 path, three evaluation timestamps, one-at-a-time target modules | E2, E3 | B0 reproduced on hand-built bars (P0-4); truncation equality | 3-5 | 5 |
| E5 | Run settings for B0 | **Yes** | `app/backtest/strategy_run.py` (single-strategy mode, unlimited profile, seeded order) | B0 configuration wiring (structure exit off, no score gate) | E1, E4 | isolation proof on real bars | 1 | 6 |
| E6 | Matched control generator and statistics | **Yes** (control-group requirement) | `app/backtest/diagnostics/{stats,sim,screen}.py`, `splits.py`, `slippage.py`, `costs.py` | seeded sampler with matching and redraw rules, 4a/4b replay, 1,000 replicates, month-block bootstrap, balance diagnostics, calibration harness | OD-15, E4, E5, E11 | matching tolerances met; calibration thresholds met on synthetic data | 8-12 (+3-5 calibration) | 9 |
| E7 | Tests (truncation, replay, isolation, boundary, TRD-08 vectors) | **Yes** | `tests/backtest/*`, `tests/trading/*` (8 shared ORB tests) | the new test families | E1, E3 first, then each item | all pass; no skipped | 4-6 (spread) | alongside 1-6 |
| E8 | Registry and run-record extensions, pre-registration file | **Yes** (reproducibility) | `app/backtest/report.py`, `run.py` | data-class labels, timestamps, variant counter, pre-registration with commit and ruleset hashes | E2 | a run record reproduces from its hashes | 2-3 | 7 |
| E9 | Prospective capture | **No** (Stage C only) | ingestion modules, `INGEST_ENABLED=False`, `FileTokenSupplier`, `scripts/kite_login.py` | append-only signal log, daily data hash, freeze manifest, outage log, scheduler job | OD-16, freeze package | dry-run on recorded data; **not activated** | 5-8 | 10 (design only; activate after freeze) |
| E10 | Data pre-flight scans (P0-1, P0-2) | **Yes** | one-off P0-1 scan (artifacts hashed); this report's analysis scripts | reproducible scan tool, tick-status contract, second implementation | §4.2 freeze, S-8, R-3 | two implementations agree on every count | 3-4 (+2 second implementation) | 8 |
| E11 | Runtime benchmark for 1,000 control replicates | **Yes** (decides `K`) | none | benchmark harness | E6 skeleton | time recorded before any result | 1 | 3 (skeleton) |

Total estimate for E1-E8, E10, E11: about **30-45 engineer-days** (E6 and its calibration dominate); E9 adds 5-8.

## 7. Exact remaining Stage A blockers

**Data (genuine blockers).** (1) D1: an accepted identity mapping (prepared; D1.7 writes are optional for Stage A). (2) D2: the dated event list is prepared; the owner must define the L-6 window (S-2) and accept the "minimum-sufficient" scope. (3) D3: resolver and statuses prepared; MG02-A1 adoption decision open (R-3). (4) D4: calendar rows still to be built from the collected circulars; two Saturday DR sessions and the Budget days have no collected circular. (5) D5: dispositions can default to exclusion; the optional re-fetch needs the tool and a broker session. (6) D6: frozen dataset, approved contract, second implementation, **human review (DR-7a)**.

**Engineering.** E1-E8, E10, E11 (§6): none started; OD-8 not approved.

**Governance.** OD-8, OD-15, OD-16 (or at least OD-8 and OD-15 for Stage A), approval of the validation plan as a whole (v0.6.0 draft), DR-7a reviewer, the 4b feasibility question (§5.3), pre-registration.

**Not blocking the first Stage A:** E9 capture, verified costs (Stage A uses the plan's schedule and `adverse-all` slippage, flagged `costs_unverified`; the gross rule decides), survivorship repair, minute data, D1.7 writes, historical ISINs, live trading, service restarts.

## 8. Shortest valid path to the first ORB B0 backtest

1. **Decision batch (§9).** One sitting; unblocks everything.
2. **Governance track (parallel):** approve the plan as a whole; OD-8 step 1; OD-15; name the human reviewer or extend DR-11 in writing; decide MG02-A1 and L-6.
3. **Engineering track (starts at OD-8):** E1, E3, E7 → E2, E4, E5 → E8, E10, E11 → E6 and the calibration. Independent of the data track until E10.
4. **Data track (starts at the decision batch):** build calendar rows from the collected circulars (D4) → finalise D2 event list and the per-session flags → **freeze** (§4.2) → D6 counts-only scan with a second implementation → human review → run authorisation.
5. **Join point:** E10 and the freeze; then the **pre-registration** (commit and ruleset hashes, seeds, frozen data hashes) and **Stage A** as one batch.
6. **Prepared but not activated:** E9 design; the D5 tool.

Estimated calendar time (estimate, wide uncertainty): about 5-8 weeks with parallel tracks, dominated by E6 plus calibration and by the human review.

## 9. Consolidated owner decision sheet

### 9.1 Already approved (unchanged)

DEC-034 (R13 approach), DEC-035 (D0 accepted with caveats), DEC-036 (DR-11 for D1 only; D1.0-D1.6), DEC-037 (data-foundation batch; evidence location); working decisions on identity, provenance and exceptions; D1.7 not authorised; T-I165 deferred; services stopped.

### 9.2 Authorised and done in this work

Read-only queries; public-archive collection of 717 bhavcopy files and 11 circulars; analysis of price scale, tick status, calendar and eligibility; documentation.

### 9.3 Proposed here (yes / amend / no)

| ID | Proposal |
|---|---|
| S-1 | Acknowledge the extended collection (717 sessions incl. the reserve window) |
| S-2 | Define the corporate-action window L-6 as in §2.1 (keep intact event days, flag, report both ways) |
| S-3 | Use the per-session price-scale and tick-status matrices as Stage A inputs |
| S-4 | Rebuild `market_calendar` from the circulars with a date-versioned session end (a Laravel change; not started) |
| S-5 | Build the read-only re-fetch tool (§3) |
| S-7 | Retain the NSE files and circulars for personal research; confirm the licence reading (DR-1) |
| S-8 | Approve the tick-status counts-only contract (§4.1, §4.3) |
| S-9 | Approve the freeze procedure (§4.2) |
| S-10 | OD-8: approve step 1 (E1, E3, E7), then steps 2-3, under the new research ruleset |
| S-11 | OD-15: option (a) with the calibration |
| S-12 | OD-16: option (a) (no early log); settle the 4b feasibility question (§5.3) |
| S-13 | Withdraw "start E9 early"; prepare E9 design only |

### 9.4 Still required from the owner

| ID | Decision |
|---|---|
| R-1 | D1.7: approve, amend or reject the per-instrument proposal |
| R-2 | DR-7a: name an independent human reviewer for D2-D6, or decide in writing whether DR-11 is extended |
| R-3 | MG02-A1 formal adoption |
| R-4 | Approval of the validation plan as a whole |
| R-6 | A broker session for the D5 re-fetch (the owner logs in; no credentials in chat) |
| R-7 | T-I165 before any step that needs the recovery key |
| R-8 | When the stopped services may restart |

### 9.5 Not authorised

D1.7 writes or schema changes; candle inserts, updates or deletes; bulk `is_demo` changes; D2-D6 database or historical-data mutations; P0-1 / P0-1b; any historical or prospective backtest; any change to B0, `ORB-MG-02`, PAQS or released rulesets; service restarts; live trading; T-I165; commits, merges or pushes; any bypass of DR-7 / DR-7a.

## 10. Files and verification

See the final session report and [TASKS.md](../../TASKS.md) (T-I170).
