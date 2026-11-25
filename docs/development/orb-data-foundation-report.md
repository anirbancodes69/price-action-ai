# ORB Data Foundation Report: D1 Closure, D2-D6 Preparation and the Path to the First B0 Backtest

| Field | Value |
|---|---|
| Version | 1.0.0 (2026-11-25) |
| Status | **Preparation and evidence only. D1.7 is NOT authorised and was not performed. D2-D6 were not executed (only read-only research, official-document collection and read-only database queries). No P0-1/P0-1b, backtest, service restart, candle change, schema change, B0/`ORB-MG-02`/PAQS/ruleset change, T-I165 execution, commit or push.** |
| Independence | Every finding is **AI-assisted and NON-INDEPENDENT** (DR-11 applies to D1 only; DR-7 / DR-7a still apply to D2-D6). Nothing here is independent human verification |
| Authority | Owner direction of 2026-11-25 (consolidated D1 closure and data-foundation brief); [DEC-035](../../DECISIONS.md), [DEC-036](../../DECISIONS.md), [DEC-037](../../DECISIONS.md); [D1 results](orb-d1-results.md); [D1 plan](orb-d1-readiness-plan.md) |
| Evidence | `~/priceaction-backups/d1-20261125/evidence/` (127 files, 27.1 MB; manifest and checksums inside, §2.1) |
| Labels | **VERIFIED** = reproduced from primary data or an official document read in this session. **INFERRED** = consistent evidence, not proof. **UNKNOWN** = no evidence found. **UNVERIFIABLE** = cannot be checked with available means. **UNRESOLVED** = checked, evidence conflicts or is insufficient |

## 1. Executive summary

1. **D1 is closed as prepared outputs** (evidence preserved, exceptions investigated, change proposal final). The D1.7 proposal is ready for the owner's separate decision (§2.7).
2. **Largest new finding: stored candle prices are provider-adjusted, not as traded.** The stored daily **and** intraday Kite history is scaled for splits, bonuses and at least some demergers/rights/dividends (VERIFIED against NSE unadjusted closes; e.g. the BAJFINANCE intraday series is exactly 1/10 of the traded price before 2025-06-16). 29 of the 50 instruments are on the traded price scale at every month-end checked; 21 are not for part of the history. Ratio-based B0 quantities are unaffected within a session; **tick-grid checks and any rupee-based cost are**. This sharpens D2/D3 and the approved "no adjusted-price exception" rule (§3.1, §3.2).
3. **The PostgreSQL write-counter rise is not in user tables.** The `public`-schema counters are identical to the D0 record; the increase is in `pg_catalog` (INFERRED to be role/ACL provisioning and statistics maintenance). Development data are byte-identical to the D0 baseline (§2.5).
4. **The 2,474,382 "PARTIAL" bars are complete apart from 7 recorded rejected bars** (all 2024-06-25 09:15); every short session is explained (§2.4). Two sessions with missing opening-range bars exist that the earlier count of five did not include (TMPV 2025-10-14, HINDUNILVR 2025-12-05), both in the `RESERVE` period (§4).
5. **Tick sizes are fully determined by two NSE circulars** (read in full), monthly closing prices (NSE bhavcopy) and a price ladder; the resolver reproduces the observed Kite tick of all 50 instruments for November 2026 and 128,000+ bars on traded-scale sessions sit exactly on the resolved grid (§3.2).
6. **The shortest valid path to the first Stage A (B0) backtest** is data tracks D2-D6 plus engineering E1-E8, E10, E11, and decisions OD-8, OD-15/16 and the validation-plan approval, in parallel (§6). Prospective capture (E9), verified costs, survivorship repair and live trading do **not** block the first historical Stage A (§6.3).

## 2. Batch A: D1 evidence, exceptions and the D1.7 proposal

### 2.1 D1 evidence preservation (VERIFIED)

| Item | Result |
|---|---|
| Location (owner-specified) | `~/priceaction-backups/d1-20261125/evidence/` (created new; nothing existed there; no existing evidence or backup overwritten) |
| Inventory | Scratchpad inventoried first: 13 files, hashes recorded; copied with no-overwrite; **all 13 copies match the original hashes** (`cmp` of the helper script also identical) |
| Evidence added after copy | Re-run baseline queries (originals were shown in-session only), investigation outputs, analysis scripts and outputs, 4 more circulars/filings, NIFTY 100/500 lists, 35 month-end and 51 calendar-probe bhavcopy files, a research log |
| Manifest and checksums | `MANIFEST.tsv` (path, size, file time UTC, sha256, kind, source URL) and `SHA256SUMS`, all verified |
| Acquisition timestamps | File times (UTC) in the manifest; bhavcopy fetch times in `src2/bhav_fetch_log.txt` |
| Permissions | Directory tree set read-only after the last write |
| **Missing or incomplete evidence (UNRESOLVED)** | (1) HTTP status/headers of the first four NSE downloads were not recorded (only file time and hash); (2) the circular PDFs behind the four in-window symbol changes, ISIN histories, most corporate actions and every holiday were not collected (NSE website APIs were not used); (3) no Kite instrument master (needs a broker session); (4) web-search results are secondary and summarised in `src2/web_research_log_20261125.md`, not stored verbatim; (5) licence terms were not read |
| Source-use context | Local personal research only. Attribution, URLs and download dates preserved in the manifest. The files are not redistributed and **no licensing clearance is claimed**. NSE's website API (cookie session) was attempted once and **blocked by the tool's safety classifier; it was not retried or worked around** |

### 2.2 WIPRO ISIN: VERIFIED (AI-assisted)

`INE075A01022` appears in: NSE equity list (E1), NSE NIFTY 100 list (E7), NSE NIFTY 500 list (E8), the issuer's own NSE governance filing (E9, `INTEGRATED_FILING_GOVERNANCE`, 2026-04-29) and Wipro's investor FAQ page (search result, not fetched). The check digit is valid. The two index files derive from NSE's master, so the issuer filing is the most independent source. Wipro is **not** on today's NIFTY 50 list (E2); its database membership stays X7 (below). Proposal: write the ISIN (confidence High).

### 2.3 NESTLEIND listing date: UNRESOLVED; `listed_on` stays NULL

- The NSE equity list gives `2023-08-01`; Kite daily bars start 2015-01-01 (VERIFIED).
- Official NSE circulars read: **NSE/CML/60084** (2024-01-02): the ISIN changed to `INE239A01024` effective **2024-01-05** (1:10 sub-division); **NSE/CML/69475** (2025-08-04): bonus shares listed from **2025-08-12**, record date 2025-08-08. Neither explains 2023-08-01 (VERIFIED that they do not).
- Therefore the NSE list date is **not** the original listing date and its meaning is **UNKNOWN**. Do not use it. **Important D1 consequence (VERIFIED):** the ISIN used today (`INE239A01024`) was **not valid before 2024-01-05**; the earlier ISIN was `INE239A01016`. An ISIN is therefore **not a stable identity key over the whole history** for instruments that were split (NESTLEIND 2024-01-05, DRREDDY 2024-10-28, SHRIRAMFIN 2025-01-10, KOTAKBANK 2026-01-14; BAJFINANCE 2025-06-16 probable). Recommendation: write the **current** ISIN and keep the ISIN history in the mapping file (UNRESOLVED for all but NESTLEIND, which has a read circular).
- No candle is touched; `listed_on` stays NULL.

### 2.4 The 2,474,382 PARTIAL-run bars: completeness assessment

**What the run metadata say (VERIFIED).** Two runs are `PARTIAL`: the 5m backfill `40c575d9` (2024-01-01..2025-12-31, 1,855,785 bars) and the 15m backfill `12725a1c` (618,597 bars). Both processed 50 of 50 instruments with **0 failed and 0 unmapped**. The only reason for `PARTIAL` is **rejected bars**: 4 (5m) and 3 (15m), all on **2024-06-25 at 09:15** (BHARTIARTL, HDFCBANK, ICICIBANK 5m only, SBILIFE; message "OHLC out of order"). Other statuses: one run `RUNNING` since 2026-11-20 21:39 with 0 bars attached (stale), three daily runs `FAILED` ("auth expired", 0 rows), and the stale-run case is explained next.

**Stale `RUNNING` run (INFERRED).** `132f5803` (5m, same range) never finished and has no bars attached; the later run `40c575d9` reports 339,165 **updated** rows. Rows inserted by the abandoned run were re-attributed to the later run. The evidence is the update count, the empty run and the same range; it is not proven by a log (`log_statement = none`).

**Session-level completeness from the bars themselves (VERIFIED).**

| Population | Instrument-sessions | Full (75 × 5m) | Short | Explanation of the short ones |
|---|---|---|---|---|
| PARTIAL-run 5m bars | 24,900 | 24,693 | 207 | 100 = Saturday special sessions 2024-03-02 and 2024-05-18 (21 bars, 09:15-12:25); 100 = Muhurat 2024-11-01 (12 bars, 18:00-18:55) and 2025-10-21 (12 bars, 13:45-14:40); 4 = the 2024-06-25 rejections (74 bars); 1 = ITC 2025-01-06 (72); 1 = TMPV 2025-10-14 (71); 1 = HINDUNILVR 2025-12-05 (71) |
| COMPLETED-run 5m bars | 10,950 | 7,150 | 3,800 | 76 dates × 50: from **2026-08-03** every regular session has 72 bars ending 15:10 (continuous trading ends 15:15, INFERRED from news and a SEBI document; the 15m series has 24 bars); plus Muhurat Sunday 2026-11-08 (11 bars, 14:20-15:10) |
| 15m (all) | sessions with 25 bars: 31,847; 24: 3,753 (3,750 = the 2026-08+ sessions, 3 = 2024-06-25 rejections); 7: 100 (the two Saturdays); 4: 150 (three Muhurat dates) | | | consistent with the 5m picture |
| Duplicates / revisions | all `PERSONAL` bars have `revision = 1`; 0 candles without an ingestion run | | | |
| Weekday sessions | every weekday not listed as closed (§3.3) has all 50 instruments in both 5m and 1D | | | |

**Assessment.** **Ingestion completeness CAN be established from existing metadata plus bar counts:** every instrument-session has the expected bar count except 207 + 3,800 short sessions that are each explained, plus the 7 recorded rejections. The bars are neither invalid nor automatically eligible: they are real source data (`PERSONAL`). Status of the explanations: special sessions VERIFIED (bhavcopy has data dated that day); 2026-08-03 timing INFERRED (secondary sources; no NSE circular read); the three demerger-day sessions INFERRED (record dates match, special pre-open sessions reported); 2024-06-25 cause UNKNOWN until the D5 re-fetch. The affected instruments and sessions are listed in §4.

### 2.5 PostgreSQL write-counter investigation

| Finding | Status |
|---|---|
| Per-table `public` counters now sum to **3,759,906 / 382,454 / 20,340** (ins/upd/del): **identical** to the D0 end-of-session record | VERIFIED |
| The database-level counter rose to 3,767,832 / 384,811 / 20,492; the extra is in **`pg_catalog`** (25,975 ins / 2,436 upd / 17,690 del), led by `pg_shdepend` (18,028 ins / 17,547 del) and `pg_statistic` (1,296 updates) | VERIFIED (counters) |
| Data manifest (counts and content hashes of the covered tables) regenerated read-only: **byte-identical to the D0 baseline**; six checksum lists 0 failures | VERIFIED |
| `audit_logs` 0 rows; `data_quality_issues` 0 rows; `candles.max(updated_at)` 2026-11-22 (pre-D0); `instruments.max(updated_at)` 2026-11-19 | VERIFIED |
| Cause: role/privilege churn from `make test-backend` provisioning (`CREATE/ALTER ROLE`, `GRANT/REVOKE`) and autovacuum/analyze on catalogs; `pg_shdepend` was last auto-vacuumed 2026-11-24 21:36:24 UTC, the minute the owner's R-run started | **INFERRED** (timing and table pattern fit; not proven) |
| Statement-level proof | **UNVERIFIABLE** (`log_statement = none`, no log retention for statements; counters are cumulative since Postgres start 2026-11-18) |
| Any development data or evidence affected | **No** (manifest, hashes and per-table `public` counters all unchanged) |

### 2.6 Classifications preserved (unchanged)

Real candles = candle `data_source` `PERSONAL`; synthetic = DEMO; the 29 mixed instruments are classified per candle source (their DEMO and Kite bars share 6,264 15m, 18,792 5m and 6,525 daily keys; nothing is overwritten); the 4 integration-test instruments (`IT3EF53C1C0`, `IT3EF53C1C1`, `ITF2FA122D0`, `ITF2FA122D1`) are excluded from research calculations by an explicit exclusion list; the stray DEMO bar (`ITF2FA122D0`, 2026-11-17, FAILED DEMO run) is ineligible and preserved. **No `is_demo` value is changed.**

### 2.7 D1.7 final change proposal (NOT APPROVED; nothing applied)

Complete per-row detail (existing value, proposed value, evidence, confidence, reason, validation query, expected impact, rollback) is in `analysis/d1_7_proposal.csv` (100 rows: 50 `isin`, 50 `listed_on`). All existing values are NULL.

**Principles kept:** ISIN needs authoritative evidence; NESTLEIND `listed_on` stays NULL; WIPRO's ISIN is now corroborated (§2.2); no `is_demo` change on the 29 mixed instruments; no candle row touched; no schema change; no historical record deleted.

**Common fields.**
- *Evidence:* E1 (NSE equity list) and E2 (NIFTY 50 list); WIPRO: E1, E7, E8, E9; NESTLEIND ISIN history: E10.
- *Reason:* give each instrument a stable, checkable identity for joins and later D2/D3 work.
- *Validation (before and after):* `SELECT id, trading_symbol, isin, listed_on FROM instruments WHERE id IN (…)`; ISIN check digit and uniqueness across the 50; `ck_instruments__*` constraints; `min(trade_date)` of each instrument's candles is not earlier than `listed_on`; data manifest differs only in the approved cells.
- *Expected impact:* none on behaviour or on any candle; `isin` is the **current** ISIN as of 2026-11-25; the history is not stored (§2.3).
- *Rollback:* a rehearsed `UPDATE … SET isin = NULL / listed_on = NULL` for the approved ids, plus restore of those cells from a fresh pre-write dump on a scratch copy first; no candle rows exist to restore.
- *Precondition:* a fresh encrypted backup needs the recovery key (T-I165 undecided).

**Groups.**

| Group | Rows | Field | Proposed | Confidence |
|---|---|---|---|---|
| A | 50 (all NIFTY 50 members in the database) | `isin` | NSE ISIN (table below); WIPRO now included | High; **historical ISIN UNRESOLVED** for NESTLEIND (history VERIFIED), DRREDDY, SHRIRAMFIN, KOTAKBANK, BAJFINANCE |
| B | 49 | `listed_on` | NSE listing date (table below) | Medium (the NSE date is that of the current record; X6 shows it can differ) |
| B2 | NESTLEIND | `listed_on` | stay NULL | n/a |
| C | 29 mixed | `is_demo` | **unchanged** (owner direction) | n/a |
| D | 4 test artifacts | handling | exclusion list, no write | High |
| E | 1 stray DEMO bar | candle | no change | High |
| F | 7 demo-only + 3 indices | all | no change | High |

| # | Symbol | Instrument ID | `isin`: NULL → | `listed_on`: NULL → | Confidence (isin / listed_on) |
|---|---|---|---|---|---|
| 1 | ADANIENT | `053ea254-d3cb-4ede-8793-9db4a950a12b` | INE423A01024 | 1997-06-04 | High / Medium |
| 2 | ADANIPORTS | `8451cc3f-f152-5c40-aa54-77dd9d4226c5` | INE742F01042 | 2007-11-27 | High / Medium |
| 3 | APOLLOHOSP | `50f9d9df-6a17-4731-a4ab-fe2b4170c648` | INE437A01024 | 1996-01-10 | High / Medium |
| 4 | ASIANPAINT | `a313185a-ca17-54e5-9c95-4f9188b74e64` | INE021A01026 | 1995-05-31 | High / Medium |
| 5 | AXISBANK | `6cf50c91-9987-5d27-b2cd-4c0e426f226f` | INE238A01034 | 1998-11-16 | High / Medium |
| 6 | BAJAJ-AUTO | `4f599325-0c3c-499d-8cd3-a9b794660c10` | INE917I01010 | 2008-05-26 | High / Medium |
| 7 | BAJAJFINSV | `cfbb094a-9d51-43a4-8e20-bc08a4b003c9` | INE918I01026 | 2008-05-26 | High / Medium |
| 8 | BAJFINANCE | `29837da6-1d86-5306-85e9-a1ab14f0e662` | INE296A01032 | 2003-04-01 | High (current ISIN; history UNRESOLVED) / Medium |
| 9 | BEL | `7c461b99-850a-53f8-9dce-ac4c129137a0` | INE263A01024 | 2000-07-19 | High / Medium |
| 10 | BHARTIARTL | `f7555b24-fe44-5611-b421-1a7b696c0ab4` | INE397D01024 | 2002-02-15 | High / Medium |
| 11 | CIPLA | `a7dc2a2f-3a05-4cc6-afa1-ddba4ae3f976` | INE059A01026 | 1995-02-08 | High / Medium |
| 12 | COALINDIA | `82d736c5-c4fc-4643-975e-4a4d3b1b2636` | INE522F01014 | 2010-11-04 | High / Medium |
| 13 | DRREDDY | `e405f2a8-eb89-5d02-a3ec-5c84cd678a44` | INE089A01031 | 2003-05-30 | High (current ISIN; history UNRESOLVED) / Medium |
| 14 | EICHERMOT | `95cdc2f8-c545-5d7c-b6a6-3f869e11e0b8` | INE066A01021 | 2004-09-07 | High / Medium |
| 15 | ETERNAL | `4a68132e-aff9-46c9-b905-b20ba7881097` | INE758T01015 | 2021-07-23 | High / Medium |
| 16 | GRASIM | `99054092-d7e6-4b8f-95ae-2c3a59cb88a9` | INE047A01021 | 1995-05-10 | High / Medium |
| 17 | HCLTECH | `f57a89ae-c67a-5027-9bb5-f80edd77808a` | INE860A01027 | 2000-01-06 | High / Medium |
| 18 | HDFCBANK | `8324ec8c-cf7f-54ba-802e-9e9a359662af` | INE040A01034 | 1995-11-08 | High / Medium |
| 19 | HDFCLIFE | `3c661d75-35f1-4caa-848b-e9c8a533243a` | INE795G01014 | 2017-11-17 | High / Medium |
| 20 | HINDALCO | `88dff8d8-8764-4dd5-8d6c-4b6a2ab4194d` | INE038A01020 | 1997-01-08 | High / Medium |
| 21 | HINDUNILVR | `551410db-3a37-573f-97c8-6ad82cdd2cfb` | INE030A01027 | 1995-07-06 | High / Medium |
| 22 | ICICIBANK | `4f78b8bd-4927-5740-b2de-4200b59a2efa` | INE090A01021 | 1997-09-17 | High / Medium |
| 23 | INDIGO | `7df92e1e-8f62-46b6-8f31-7223b09f2ec2` | INE646L01027 | 2015-11-10 | High / Medium |
| 24 | INFY | `6cd106be-c92f-5050-afc0-7ab7d2f9f135` | INE009A01021 | 1995-02-08 | High / Medium |
| 25 | ITC | `9140477a-a1f4-58f4-aff3-2bd027ac6c92` | INE154A01025 | 1995-08-23 | High / Medium |
| 26 | JIOFIN | `d8946fa7-53cd-4293-a511-c5e6e0c35b7d` | INE758E01017 | 2023-08-21 | High / Medium |
| 27 | JSWSTEEL | `d1c98b4b-5bcf-5612-a0f1-50a563825756` | INE019A01038 | 2005-03-23 | High / Medium |
| 28 | KOTAKBANK | `0276f31d-705b-5758-92db-95ece0dbf0c6` | INE237A01036 | 1995-12-20 | High (current ISIN; history UNRESOLVED) / Medium |
| 29 | LT | `dc414c78-75eb-5fa2-9b53-2937643907c5` | INE018A01030 | 2004-06-23 | High / Medium |
| 30 | M&M | `52574cf5-93e3-42b6-bf4a-9a9f7de55f9f` | INE101A01026 | 1996-01-03 | High / Medium |
| 31 | MARUTI | `bac1c388-a834-5dc8-89b3-89c9bdf4f216` | INE585B01010 | 2003-07-09 | High / Medium |
| 32 | MAXHEALTH | `9b2a38e9-dd40-450a-b274-1451ddbc9722` | INE027H01010 | 2020-08-21 | High / Medium |
| 33 | NESTLEIND | `05c1e592-03dc-491d-ad1a-35122c4abfc4` | INE239A01024 | NULL (unchanged) | High (current ISIN; history UNRESOLVED) / n/a |
| 34 | NTPC | `1756d7b7-2afb-5dd4-bdc4-3c997eda5ddf` | INE733E01010 | 2004-11-05 | High / Medium |
| 35 | ONGC | `c3bcfdb4-5549-47fa-841c-28e641fa2aa1` | INE213A01029 | 1995-07-19 | High / Medium |
| 36 | POWERGRID | `4bd866ec-84e8-5101-9357-b170098551e6` | INE752E01010 | 2007-10-05 | High / Medium |
| 37 | RELIANCE | `d41f4df7-9fe4-579d-a62a-eac4659d8434` | INE002A01018 | 1995-11-29 | High / Medium |
| 38 | SBILIFE | `b96462d5-e4cc-426a-986c-4cca0aeea290` | INE123W01016 | 2017-10-03 | High / Medium |
| 39 | SBIN | `b9cfc564-183a-5977-b1a8-662b148c2a70` | INE062A01020 | 1995-03-01 | High / Medium |
| 40 | SHRIRAMFIN | `a2c2497b-77dd-4370-be8c-9623d685f35e` | INE721A01047 | 1996-12-11 | High (current ISIN; history UNRESOLVED) / Medium |
| 41 | SUNPHARMA | `67dcc5e4-0d95-5fab-bb58-0082da5465ab` | INE044A01036 | 1995-02-08 | High / Medium |
| 42 | TATACONSUM | `07b36c5c-78d9-44a0-ad39-292fb9fc2eb4` | INE192A01025 | 1998-11-18 | High / Medium |
| 43 | TATASTEEL | `fb1c2f3d-5d68-565b-a3e8-c140aac706eb` | INE081A01020 | 1998-11-18 | High / Medium |
| 44 | TCS | `1353ea01-4260-5006-8aad-a4e065e2e8ee` | INE467B01029 | 2004-08-25 | High / Medium |
| 45 | TECHM | `85fcade7-2ec6-420d-a271-5da0a6fa0970` | INE669C01036 | 2006-08-28 | High / Medium |
| 46 | TITAN | `e58d1b8b-26a0-5ac7-885e-a9291a100a3b` | INE280A01028 | 2004-09-24 | High / Medium |
| 47 | TMPV | `66301ca6-1829-461a-aced-d4d63ff2ee7d` | INE155A01022 | 1998-07-22 | High / Medium |
| 48 | TRENT | `1e47c838-8ed4-545f-9d42-ae6e8df48af5` | INE849A01020 | 2004-06-07 | High / Medium |
| 49 | ULTRACEMCO | `e5d2d1c1-679e-588a-bdce-c323475d89d3` | INE481G01011 | 2004-08-24 | High / Medium |
| 50 | WIPRO | `ab24a2ff-62c9-5cf7-9852-80cfa1e5259d` | INE075A01022 | 1995-11-08 | High / Medium |

## 3. Batch B: D2, D3 and D4 (research and evidence; nothing executed against the database)

### 3.1 D2 Corporate actions

**Method.** NSE bhavcopy (unadjusted closes) for the last trading day of every month from 2024-01 to 2026-11 (35 files) was compared with the stored Kite closes for the 50 instruments (1,750 instrument-month-end pairs; symbol changes mapped with NSE's file). A step in the ratio between two consecutive month-ends marks a price-scaling event. The event itself was then identified with dated sources.

**Structural finding (VERIFIED).** The stored history is **provider-adjusted**: the ratio of stored to traded close is 1.0000 only after the last event; 29 instruments are on the traded scale at every month-end; 18 are not at some month-ends; 3 (`COALINDIA`, `INFY`, `ONGC`) are not on the traded scale before 2026-11-19. The last 5m bar of the same month-end sessions shows the same scaling (303 of 1,714 pairs differ by more than 3%; this 5m check did not map the two renamed symbols), so the **intraday data are adjusted too**.

**Candidate events (34 steps).** 10 split/bonus-like (factor ≥ 1.45), 1 large (ITC), 23 small (1.2%-3.7%).

| Symbol | Event (record/ex date) | Provider step | Evidence | Status |
|---|---|---|---|---|
| BAJFINANCE | 1:2 split + 4:1 bonus, ex 2025-06-16 | ×10.0005 | multiple sources | date VERIFIED (secondary); factor INFERRED (2×5) |
| DRREDDY | 1:5 split, ex 2024-10-28 | ×5.0001 | NSE filing and circular listed; sources | INFERRED |
| HDFCBANK | 1:1 bonus, ex 2025-08-26 (record 08-27) | ×2.0000 | sources | INFERRED |
| KOTAKBANK | 1:5 split, record 2026-01-14 | ×5.0002 | NSE record-date filing listed; sources | INFERRED |
| NESTLEIND | 1:1 bonus, record 2025-08-08 (NSE/CML/69475); 1:10 split 2024-01-05 (NSE/CML/60084) | ×2.0001 | **NSE circulars read** | **VERIFIED** (the 2024-01-05 split precedes the first month-end, so no step is visible) |
| RELIANCE | 1:1 bonus, ex 2024-10-28 | ×1.99997 | sources | INFERRED |
| SHRIRAMFIN | 1:5 split, record 2025-01-10 (new ISIN `INE721A01047`) | ×4.9998 | sources; NSE CML/65743 listed | INFERRED |
| TRENT | 1:2 bonus, record/ex 2026-06-04 | ×1.5000 | sources | INFERRED |
| WIPRO | 1:1 bonus, ex 2024-12-03 | ×2.0003 | sources | INFERRED |
| ADANIENT | partly-paid rights issue (3 for 25 at ₹1,800), ex 2025-11-17 | ×1.0315 | sources | INFERRED |
| HINDUNILVR | Kwality Wall's demerger, record 2025-12-05 (special pre-open 09:00-10:00) | ×1.0195 | sources | INFERRED |
| ITC | ITC Hotels demerger, record 2025-01-06 (special pre-open) | ×1.15625 | sources | **UNRESOLVED**: the reported exchange discovery adjustment was about 5.8% (₹482 → ₹455.6), far smaller than the 15.6% step |
| TMPV | Tata Motors demerger, record 2025-10-14 (some sources say ex 10-13) | ×1.4525 | sources | **UNRESOLVED**: the exchange price discovery implied about ×1.65 (₹660.75 → ~₹400); the provider's factor differs |
| 21 other steps | `BAJAJ-AUTO`, `COALINDIA` (×3), `INFY` (×2), `ITC` (×2), `ONGC` (×4), `TATACONSUM`, `TATASTEEL` (×2), `TECHM` (×3), `ULTRACEMCO`, `WIPRO` (×2) | ×1.012-×1.037 | none collected | **UNRESOLVED** (dividend-like; not identified) |

**Findings that change the plan.**
1. Because stored prices are adjusted, **sessions are not on the traded tick grid** whenever any later event exists. The approved MG02-A1 rule (no adjusted-price exception; ticks verifiable only on an unadjusted basis) therefore needs a **per-session scale test**.
2. **A per-session scale test needs no exact adjustment factors:** the ratio of the stored close to the NSE unadjusted close (daily bhavcopy) is exactly 1 on traded-scale sessions. This is a cheaper and more reliable route than deriving every factor (§6).
3. **B0 needs very little from D2.** B0 uses only the same-session 5m bars (spec dependency map), and every price in a session is scaled by the same constant, so range, breakout (×1.0005), stop and 2R target are scale-invariant. Under DR-3a ("affected = intersects the actual input and lookback") the affected sessions for B0 are: (a) event-day sessions with a special pre-open or a broken opening range (ITC 2025-01-06, TMPV 2025-10-14, HINDUNILVR 2025-12-05; MG-02 already excludes them); (b) tick-verification sessions that are not on the traded scale (status `TICK_UNVERIFIABLE`, not failure); (c) rupee-based costs, which need the traded price. **Proposal (not a decision):** a "minimum-sufficient D2" = dated event list with sources + the per-session scale flag + the dependency map; adjustment-factor derivation only if a later configuration needs it.
4. The earlier D0-era statement "demergers are not adjusted" is **contradicted** by the ITC, TMPV and HINDUNILVR steps (the provider does scale for them, by a factor that may not match the exchange's price discovery). Record as UNRESOLVED until D2 reconciles it.

Evidence: `analysis/d2_candidate_events.csv`, `analysis/kite_vs_bhav_ratio.csv`, `analysis/native_scale_by_instrument.csv`, `analysis/kite_5m_lastbar_vs_bhav.csv`, scripts `d2_*.py`.

### 3.2 D3 Historical tick sizes

**Official rule (two NSE circulars read in full: VERIFIED).**

| Period | Rule | Source |
|---|---|---|
| Up to 2024-06-09 | 0.05 for all equity series ("current tick size Rs 0.05") | NSE/CMTR/62174 (2024-05-24) |
| From 2024-06-10 | Price below ₹250: 0.01; otherwise 0.05. Reviewed **monthly**: the closing price on the last trading day of a month sets the tick for the next month (first set from the 2024-05-31 close) | NSE/CMTR/62174 |
| From 2025-04-15 | Below 250: 0.01; 250-1,000: 0.05; >1,000-5,000: 0.10; >5,000-10,000: 0.50; >10,000-20,000: 1.00; >20,000: 5.00. First set on 2025-04-11 from the 2025-03-28 close; monthly thereafter from the previous month's last trading-day close | NSE/CMTR/67133 (2025-03-13) |
| Corporate actions | Split, bonus, dividend, rights: the existing tick continues until the next monthly review; a new security from a corporate action keeps the parent's tick until the next review | NSE/CMTR/62174 |

No later circular changing the regular CM ladder was found (UNKNOWN beyond the search; check NSE's circular list before relying on it).

**Resolver and checks.**
- *Provisional tick per instrument-month* for all 50 instruments from the 35 unadjusted month-end closes: `analysis/d3_provisional_tick_by_month.csv`. Distribution: before 2024-06-10 flat 0.05 (200 instrument-months); 2024-06-10..2025-04-14: 479 × 0.05 and 21 × 0.01; from 2025-04-15: 574 × 0.10, 278 × 0.05, 81 × 0.50, 69 × 0.01, 48 × 1.00. 18 instruments change tick at least once since 2025-04-15.
- *Check 1 (VERIFIED):* the resolved tick for November 2026 (from the 2026-10-30 close) equals the tick recorded by Kite in the instrument snapshot for **all 50 of 50** instruments.
- *Check 2 (VERIFIED):* on month-end sessions where the stored price is on the traded scale, **128,436 5m and 15m bars (96,327 + 32,109) have 0 off-grid prices** under the resolved tick, across ticks 0.01, 0.05, 0.10, 0.50 and 1.00 (`db/d3_grid_check_month_end_sessions_20261125.txt`). This is a sample (month-end sessions only).

**Status mapping for the approved vocabulary (proposal; MG02-A1 is not adopted by this report).**

| Status | Rule |
|---|---|
| `TICK_VERIFIED_PASS` | stored price on the traded scale (session scale ratio = 1) and every OHLC value on the resolved grid |
| `TICK_VERIFIED_FAIL` | traded scale and at least one off-grid value |
| `TICK_UNVERIFIABLE` | the session's price scale is not the traded scale (adjusted history), or the instrument identity or price basis cannot be shown |
| `TICK_UNKNOWN` | the tick cannot be determined (no prior month-end close, unresolved corporate-action transition, unknown series) |

Unknown and unverifiable are not failures. **What is still open:** the per-session scale test over the whole development window (needs daily bhavcopy; §6), the transition months after corporate actions, and the formal MG02-A1 decision.

### 3.3 D4 Market calendar

| Finding | Evidence | Status |
|---|---|---|
| 6 weekend sessions have bars for all 50 instruments: Sat 2024-01-20, Sat 2024-03-02 (21 bars), Sat 2024-05-18 (21 bars), Sat 2025-02-01 (full, Budget), Sun 2026-02-01 (full, Budget), Sun 2026-11-08 (Muhurat, 11 bars) | stored bars; NSE bhavcopy for each date carries data **dated that day** | VERIFIED (trading, special) |
| 2 weekday Muhurat sessions: Fri 2024-11-01 (12 bars 18:00-18:55) and Tue 2025-10-21 (12 bars 13:45-14:40) | stored bars; bhavcopy dated that day | VERIFIED |
| **43** weekdays between 2024-01-01 and 2026-11-19 with no bars for any instrument (2024: 16, 2025: 13, 2026: 14; all consistent with holidays; the D0 package counted 39 over a different window, a minor discrepancy not investigated) | bhavcopy probe: 32 return the previous trading day's data (so no data dated that day), 11 archive files are absent (2024-11-15 and 2025-02-26 .. 2025-10-02) | **INFERRED** closed (no NSE holiday circular collected; plausible names, e.g. 2024-01-22 special holiday, 2024-05-20 election day) |
| `market_calendar` holds **397 rows** (2025-12-01 to 2026-12-31 plus one integration-test row): **284 are "Unverified weekday default (NSE holidays not loaded)"**, 112 weekends, all sessions 09:15-15:30 | database | VERIFIED |
| That table is **wrong in 17 places** inside its range: 15 weekday holidays marked trading (2025-12-25, 2026-01-15, 01-26, 03-03, 03-26, 03-31, 04-03, 04-14, 05-01, 05-28, 06-26, 09-14, 10-02, 10-20, 11-10) and 2 traded weekend sessions marked closed (2026-02-01, 2026-11-08) | database vs bars | VERIFIED |
| It has **no rows at all for 2024-01 to 2025-11** | database | VERIFIED |
| Session end changed on **2026-08-03**: continuous cash trading ends 15:15 (closing auction 15:15-15:35); 75 regular sessions have 72 bars ending 15:10; the table still says 15:30 | bars (VERIFIED); news and a SEBI document (INFERRED for the rule); a further change from 2026-12-07 is reported by **one** source (UNVERIFIED) | INFERRED |
| Opening-range gaps outside special sessions: 7 sessions (§4) | bars | VERIFIED |

**Proposal.** Build `market_calendar` rows from official NSE holiday and special-session circulars (to be collected), verify against the bars and bhavcopy date test, and make the session end **date-versioned**. The B0 "session-end exit" then has an unambiguous bar (15:25 start before 2026-08-03; 15:10 after). That is an application of the frozen exit, not a change to B0, but the owner should confirm it (decision register).

## 4. Batch C: D5 missing opening bars

**Sessions with missing opening-range bars (VERIFIED from bars; 5m; expected 09:15..15:25).**

| # | Instrument, date | Missing bars (IST) | Data class | Recorded or likely cause | Status |
|---|---|---|---|---|---|
| 1-4 | BHARTIARTL, HDFCBANK, ICICIBANK, SBILIFE, 2024-06-25 | 09:15 | DEVELOPMENT | ingestion rejected the provider's 09:15 bar: "OHLC out of order" (run `40c575d9`; 15m: BHARTIARTL, HDFCBANK, SBILIFE) | cause of rejection **UNKNOWN** (provider data defect INFERRED); re-fetch needed |
| 5 | ITC, 2025-01-06 | 09:20, 09:25, 09:30 | DEVELOPMENT | ITC Hotels demerger record date; special pre-open session reported | INFERRED (date match; the exact bar pattern is not fully explained, since bars exist from 09:35) |
| 6 | TMPV, 2025-10-14 | 09:20 to 09:35 | **RESERVE** (outside P0-1) | Tata Motors demerger record date; special pre-open 09:00-10:00 | INFERRED |
| 7 | HINDUNILVR, 2025-12-05 | 09:20 to 09:35 | **RESERVE** | Kwality Wall's demerger record date; special pre-open 09:00-10:00 | INFERRED |

The earlier count of five equals rows 1-5 (a count restricted to the development data). **Rows 6 and 7 are new to the record**, both in the `RESERVE` window (2025-09-24..2025-12-31) which P0-1 did not scan; they would fail `ORB-MG-02` (`OR_MISSING_BAR`) in any later scan of that window. The 2024-06-25 cause for row 1-4 was recorded as a "provider-rejected bar" in the D0 era; its reason remains unknown.

**Read-only re-fetch procedure (DR-5; to run only after authorisation; nothing was fetched).**
1. **Prerequisites:** a valid broker session (daily login); a small read-only tool that calls the provider client for one instrument, one date and one interval and **writes no database row** (the ingestion code writes to the database, so this tool does not exist yet; building it is an engineering item, §6); D1, D4 done.
2. **Requests:** the 7 instrument-sessions above, 5m and 15m, plus one control instrument-session per date on which a missing bar was recorded (to show the provider still serves that date).
3. **Archive each response as received:** raw bytes, request parameters, provider status, fetch time (UTC), SHA-256; files made read-only; manifest with hashes; stored under the D5 evidence folder.
4. **Compare** the response with the stored bars (never write to `candles`): `PROVIDER_STILL_REJECTS`, `PROVIDER_NOW_RETURNS_BAR`, `SESSION_SPECIAL`, `NO_DIFFERENCE`.
5. **Disposition per session:** `EXCLUDED_MG02` (default), or `RECOVERABLE` (only a decision, never an automatic insert); `MISSING_BAR` data-quality issues for history are proposals only.
6. **Never overwrite or delete a candle.** A failed or partial fetch is recorded, not retried silently.

## 5. Batch D: D6 and P0-1 readiness

**D6 becomes executable only when all of these hold.**

| # | Requirement | Today |
|---|---|---|
| 1 | D1 closed (identity map accepted; D1.7 decision taken) | Prepared; D1.7 undecided |
| 2 | D2 event list and per-session scale flags complete and reviewed | Research done for 13 events; scale flags not built (needs daily bhavcopy); 21 steps UNRESOLVED |
| 3 | D3 resolver spec adopted; MG02-A1 formal adoption decision taken | Resolver prepared and checked; adoption not decided |
| 4 | D4 verified calendar and date-versioned session end | Research done; circulars not collected |
| 5 | D5 re-fetch done, raw responses archived | Procedure written; tool, broker session and authorisation missing |
| 6 | **Dataset freeze:** manifest and hashes of the candle tables per data class, the reference data and the scale flags, recorded before any scan | Not done |
| 7 | Counts-only contract approved first, including the four tick statuses; **no strategy performance, no signal or trade counts (P0-1b stays unapproved)** | Contract defined in the validation plan §3; the tick-status version needs approval |
| 8 | **Independent human review** of the preparation (DR-7) and a **second implementation reproduces** the counts | Reviewer not named (DR-7a OPEN); DR-11 covers D1 only |
| 9 | Explicit owner run authorisation | Not given |

Nothing in this report adds strategy-performance analysis to P0-1.

## 6. E1-E11 backtest dependency matrix and the critical path

### 6.1 Frozen B0 (unchanged)

15-minute opening range, wick-based; first qualifying close above the range (buffer ×1.0005); stop at range low; fixed 2R target; no filters; first breakout only; mandatory exits: stop, target, session end; retest is a separate strategy; no weighted score. No change to B0, `ORB-MG-02`, PAQS or released rulesets is proposed.

### 6.2 Dependency matrix

"Blocks first historical backtest" means Stage A of the [validation plan](../research/orb-validation-plan.md) (the entry-edge test, the first valid historical test); a descriptive B0 replay without the matched control would not be a valid test under that plan (INFERRED from the plan).

| Item | What | Status | Blocks Stage A? |
|---|---|---|---|
| E1 | Register `opening_range_breakout` in the strategy registry (today's detector unchanged) | NOT STARTED | **Yes** |
| E2 | New research ruleset (`pa-intraday`, role RESEARCH) with `orb.*` keys | NOT STARTED | **Yes** |
| E3 | Strict range validator (`ORB-MG-02`) for the B0 path | NOT STARTED | **Yes** |
| E4 | B0 detector path (switches, three evaluation timestamps, targets) | NOT STARTED | **Yes** |
| E5 | Run settings for B0 (isolation) | NOT STARTED | **Yes** |
| E6 | Matched random-entry control generator and statistics | NOT STARTED | **Yes** (control-group requirement) |
| E7 | Tests (truncation equality, replay equivalence, isolation proof, boundary tests, TRD-08 vectors) | NOT STARTED | **Yes** |
| E8 | Registry and run-record extensions, pre-registration file with hashes | NOT STARTED | **Yes** (reproducibility) |
| E9 | Prospective capture (daily ingestion, signal log, freeze manifest) | NOT STARTED | **No** (Stage C only), but **start early**: the validation clock is data that does not exist yet |
| E10 | Data pre-flight scans (P0-1, P0-2) | P0-1 executed once; post-remediation scan = D6 | **Yes** (via D6) |
| E11 | Runtime benchmark for 1,000 control replicates | NOT STARTED | **Yes** (decides `K`, recorded before results) |

### 6.3 Blockers by class

| Class | Blocks the first historical (Stage A) backtest | Blocks only later stages / live |
|---|---|---|
| Data integrity | D0 (done); D1 accepted mapping; D6 pre-flight on a frozen dataset | D1.7 database writes themselves (the mapping file can serve Stage A) |
| Corporate actions | D2 minimum-sufficient: dated events, per-session scale flags, dependency map; unreconciled event sessions excluded (DR-3) | Exact adjustment factors for all 34 steps (needed only if a configuration uses cross-session prices) |
| Tick size | D3 decision and resolver: **required if the tick check stays hard**; with MG02-A1 statuses it becomes a flag, not a failure | Full historical tick remediation before 2024 |
| Calendar | D4 verified dates and session-end versioning (needed for exits and special-session removal, L-4) | Dates before 2024; forward calendar |
| Missing bars | D5 dispositions for the 7 sessions (default exclusion is sufficient); re-fetch is optional if exclusion is accepted | Completeness for backfilled history |
| Execution / slippage | Stage A uses the plan's cost schedule and the `adverse-all` slippage, flagged `costs_unverified`; the **gross** rule decides | Verified costs (needed for `PAPER_TRADING_READY`, criteria §4) |
| Cost model | schedule as defined in the plan; no new work required to run | Real fee and slippage verification |
| Reproducibility | E8 pre-registration with commit and ruleset hashes, seeds, frozen data hashes; E7 tests | Prospective daily data hash |
| Control group | E6 plus the calibration of the interval method (OD-15, F-1) | Stage B reality-check bootstrap |
| Prospective validation | Not blocking | E9, 60/120-session horizon, 100-trade floor, Stage C; survivorship repair; live trading |
| Governance | OD-8 (scope of E1-E8), OD-15, OD-16, approval of the validation plan as a whole (v0.6.0 draft), DR-7a reviewer for D2-D6 (or a decision extending DR-11) | Owner acceptance for paper trading |

### 6.4 Shortest valid path (parallel tracks)

1. **Decision batch (owner, one sitting):** §7. Unblocks every track below.
2. **Track Data** (needs the human reviewer or an extension of DR-11 for D2-D6): collect NSE circulars (holidays, symbol/ISIN changes, corporate actions) and fetch **daily bhavcopy for the development window** (about 450 sessions; public archive; a licence note is needed) → D2 event list and per-session scale flags → D3 per-session tick statuses → D4 calendar rows and session-end versions → D5 dispositions (re-fetch only if wanted) → **freeze** → D6 counts-only scan with a second implementation.
3. **Track Engineering** (needs OD-8): E1, E3, E7 first → E2, E4, E5 → E6, E8, E10, E11. Independent of the data track until E10.
4. **Track Governance** (parallel): approve the validation plan, settle OD-15/OD-16, decide MG02-A1, name the reviewer.
5. **Track Capture** (design only): ~~start E9 now~~ **superseded** by the [Stage A readiness report](orb-stage-a-readiness-report.md#0-executive-summary) (item 7): the plan and OD-16 allow no early log; prepare E9, do not activate it before the freeze package.
6. **Pre-register** (commit and ruleset hashes, seeds, frozen data hashes) → **Stage A**.

D2-D5 can be prepared in parallel; D6 and E10 are the join point.

## 7. Consolidated owner decision register

### 7.1 Already approved (in force)

| Decision | Reference |
|---|---|
| D0 accepted with caveats; review NON-INDEPENDENT | DEC-035 |
| DR-11 for D1 only; D1.0-D1.6 authorised; working decisions C1-C8 (ISIN plus symbol history; candle source is the provenance authority; test artifacts isolated, never deleted; stray DEMO bar ineligible and preserved; mapping and evidence files first, no schema change; unknown stays unresolved; T-I165 deferred; services stopped) | DEC-036 |
| Evidence location `~/priceaction-backups/d1-20261125/evidence/`; research and document collection (subject to licensing); batch order A-D; D1.7 not authorised | DEC-037 (recorded with this report) |
| R13 remediation approach (approach only); DR-7 and DR-7a for D2-D6 | DEC-034, DR-7, DR-7a |

### 7.2 Proposed here (need the owner's yes / amend / no)

| ID | Proposal |
|---|---|
| P-1 | Accept the **D1.7 proposal** (groups A, B, B2, C-option-1, D, E, F, §2.7) or amend it; D1.7 itself stays a separate approval |
| P-2 | Treat the **current ISIN** as the stored value and keep ISIN history in the mapping file (§2.3) |
| P-3 | Record WIPRO's ISIN as VERIFIED (AI-assisted, NON-INDEPENDENT) |
| P-4 | **Minimum-sufficient D2** for B0 (§3.1 item 3) |
| P-5 | Authorise fetching **daily NSE bhavcopy** for the development window from the public archive (about 450 files) to build per-session scale flags and unadjusted closes (network use; licence note) |
| P-6 | Adopt the **D3 resolver specification and status mapping** (§3.2) as the working D3 design, **subject to** the separate MG02-A1 decision |
| P-7 | **D4**: build the calendar from official circulars checked against bars and bhavcopy; session-end exit versioned by date (§3.3) |
| P-8 | **D5**: build the read-only re-fetch tool (engineering) and run it only when a broker session is available (§4); add rows 6-7 to the D5 scope as `RESERVE` items |

### 7.3 Still required from the owner

| ID | Decision |
|---|---|
| R-1 | **D1.7:** approve, amend or reject the per-instrument write (and decide group C option 1 versus 2, test-artifact handling) |
| R-2 | **DR-7a:** name an independent human reviewer for D2-D6, or decide in writing whether DR-11 is extended (DR-7 is not silently waived) |
| R-3 | **MG02-A1:** formal adoption decision (wording points and extra vectors open) |
| R-4 | **OD-8** (scope of E1-E8), **OD-15**, **OD-16**, and approval of the validation plan as a whole |
| R-5 | **Licence:** confirm that keeping the NSE files for personal research is acceptable (DR-1) |
| R-6 | A **broker session** for the D5 re-fetch (daily login) |
| R-7 | **T-I165:** decide before any step that needs the recovery key (a D1.7 backup needs it) |
| R-8 | **Services:** when the backend, queue, scheduler and engine may restart (not needed for D1-D5 research) |
| R-9 | Whether to start **E9** prospective capture early |

### 7.4 Authorised now / not authorised

| Authorised (done in this report) | Not authorised |
|---|---|
| Read-only database queries; collection of public NSE documents and files; analysis and documentation; evidence preservation | D1.7 writes or any schema change; D2-D6 database or historical-data mutations; candle inserts/updates/deletes; bulk `is_demo` changes |
| | P0-1 / P0-1b; any historical or prospective backtest; any change to B0, `ORB-MG-02`, PAQS or released rulesets |
| | Service restarts; live trading; T-I165; commits, merges, pushes |

## 8. Files changed and verification

See the final section of the session report; the list is also kept in [TASKS.md](../../TASKS.md) (T-I169).
