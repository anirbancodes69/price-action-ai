# ORB D1 Results: Identity and Provenance (D1.0-D1.6)

| Field | Value |
|---|---|
| Version | 1.0.0 (2026-11-25) |
| Status | **D1.0-D1.6 COMPLETED as prepared outputs. D1.7 (any database write or schema change) is NOT approved and was NOT performed.** Reviews here are **AI-assisted and NON-INDEPENDENT** (DR-11, D1 only); they are not independent human verification. D2-D6 stay under DR-7 / DR-7a |
| Authority | Owner consolidated D1 authorisation of 2026-11-25 ([DEC-036](../../DECISIONS.md), DR-11); [plan](orb-d1-readiness-plan.md) |
| Method | Read-only database session; public NSE files downloaded once (no login, no paid product); analysis scripts and raw files staged outside the repository (§9). No candle, instrument or schema change; no service restart; no P0-1/P0-1b; no backtest; no B0, `ORB-MG-02`, PAQS or ruleset change |

## 1. D1.0 Preconditions (all met)

D0 evidence: six checksum lists 0 failures; development manifest hash `e74c391c473c…` equal to the baseline; key directory empty; services unchanged (backend, queue, scheduler, engine stopped); repository HEAD `a33bb83`. DEC-035 (D0 accepted with caveats) and DEC-034 (R13 approach) in force.

**Post-D1 integrity check.** After all D1 queries, the data manifest was regenerated from the development database in a read-only session and compared with the pre-D0 baseline: **byte-identical** (`MANIFEST_IDENTICAL`). Observation, not explained: the database-level write counters (`pg_stat_database`) read 3,767,832 inserts / 384,811 updates / 20,492 deletes, against 3,759,906 / 382,454 / 20,340 recorded at the end of D0 on 2026-11-23, a rise of 7,926 / 2,357 / 152. The D1 session was forced read-only (`transaction_read_only = on`) and the manifest shows no change in the covered tables, so the rise is not attributed to D1; it may come from activity between the D0 record and this session (the counters also include catalog and uncovered tables). It is not investigated further here.

## 2. D1.1 Baseline (unchanged since the plan)

64 instruments (50 NIFTY 50 members, 7 demo-only equities, 3 demo indices, 4 test artifacts); `isin` and `listed_on` NULL for all 64; two data sources (`DEMO`, `PERSONAL`/`ZERODHA_KITE`); 93 provider refs; 89 snapshots; `corporate_actions` 0 rows; no `audit_logs` row about instruments. The counts equal the plan's §3.

## 3. D1.2 Provenance classification

| Class | Count | Meaning | Candles |
|---|---|---|---|
| REAL-KITE | 21 | NIFTY 50 member, `is_demo = false`, Kite data only | Kite only |
| REAL-MIXED | 29 | NIFTY 50 member, `is_demo = true`, real security | Kite **and** DEMO candles under one instrument id |
| DEMO-ONLY | 7 | Demo equities outside NIFTY 50 (`CUMMINSIND`, `DMART`, `HAL`, `PERSISTENT`, `PIDILITIND`, `POLYCAB`, `TVSMOTOR`) | DEMO only |
| DEMO-INDEX | 3 | `NIFTY 50`, `NIFTY BANK`, `INDIA VIX` | none |
| TEST-ARTIFACT | 4 | Symbols `IT3EF53C1C0`, `IT3EF53C1C1`, `ITF2FA122D0`, `ITF2FA122D1`, name `t`, `is_demo = false` | 1 stray DEMO 5m bar (on `ITF2FA122D0`) |

**Rule adopted (owner decision C2): a candle is REAL only if its data source mode is `PERSONAL` (provider `ZERODHA_KITE`).** The instrument `is_demo` flag is informational. By source: 3,690,447 PERSONAL bars on 50 instruments; 44,641 DEMO bars (44,640 on 36 demo-universe instruments + the 1 stray bar).

**Cause of the mislabel (code evidence, not a guess).** The Kite sync ([instruments.py](../../python-engine/app/ingestion/instruments.py)) adopts an existing ACTIVE `(exchange, trading_symbol)` row, here the demo row created 2026-11-17, and only adds a provider ref and a snapshot. It never changes `is_demo`, name or ISIN. So 29 real securities kept the demo flag, the demo name and a live `DEMO` provider ref beside the new Kite ref.

## 4. D1.3 Evidence register

All files were fetched once on 2026-11-25 (about 11:37 UTC) with a generic client string, from public NSE archive URLs, with no login and no paid product (DR-1). They are **NSE-published reference files**, not individual circular PDFs. They are held in the scratchpad (§9), **not** in the repository, and not redistributed. **Licensing:** the files are public downloads, but NSE's terms of use were not reviewed; the owner should confirm that keeping them for personal research is acceptable before they are archived (DR-1).

| ID | Source | URL | sha256 | Used for |
|---|---|---|---|---|
| E1 | NSE equity list (`EQUITY_L.csv`) | `https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv` | `aa4b5c46bcd791b52e61d9da17e1ce9b25be1b5c902d111ee31207cfdd39f9d2` | ISIN, series, NSE listing date |
| E2 | NIFTY 50 constituents (`ind_nifty50list.csv`) | `https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv` | `f5ba4027d935ae72879d5c24bbebf0e8439ec8ed504ffdf4175fde69206244b3` | Second ISIN source; current membership |
| E3 | NSE symbol changes (`symbolchange.csv`) | `https://nsearchives.nseindia.com/content/equities/symbolchange.csv` | `6989d499b6a7900c8db9558b32e992a18a08907d6a30493c011a5c1c7de1483a` | Symbol history |
| E4 | NSE name changes (`namechange.csv`) | `https://nsearchives.nseindia.com/content/equities/namechange.csv` | `b25a3ebb8cfb0772f8027c9b27bc37c304e93ce2010d29aee34f0acb0213b98f` | Name history (retrieved; not needed for any row) |
| E5 | Development database, read-only session | tables `instruments`, `candles`, `data_sources`, `ingestion_runs`, `instrument_snapshots`, `instrument_provider_refs`, `universe_memberships`, `audit_logs` | classification TSV `db/instruments_classification.tsv` | Provenance, candle ranges, overlaps |
| E6 | Repository code | `python-engine/app/ingestion/instruments.py` | git HEAD `a33bb83` | Cause of the mislabel |

The files change daily; E1-E4 reflect 2026-11-25, not history. The circular PDFs behind each symbol change were **not** collected (they remain UNRESOLVED at circular level, §6).

## 5. D1.4 Identity and provenance matrix (64 instruments)

Evidence codes: "NSE x2 + checksum" = the same ISIN in E1 and E2 and a valid ISIN check digit; "NSE x1 + checksum" = E1 only (the symbol is not in today's E2 list). "Listing vs data" compares the E1 listing date with the first Kite daily bar (the earliest stored bar is 2015-01-01, which is not a listing date). Before values of the proposed fields are NULL for every row.

| # | Symbol | Class | ISIN | ISIN evidence | NSE listing | Listing vs data | Kite / DEMO bars | `is_demo` | Symbol changes 2015+ (before 2015) | Proposal (D1.7, not applied) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ADANIENT | REAL-KITE | INE423A01024 | NSE x2 + checksum | 1997-06-04 | listing precedes the data start (consistent) | 73944 / 0 | f | none recorded (ADANIEXPO→ADANIENT 2006-09-20) | isin, listed_on |
| 2 | APOLLOHOSP | REAL-KITE | INE437A01024 | NSE x2 + checksum | 1996-01-10 | listing precedes the data start (consistent) | 73944 / 0 | f | none recorded | isin, listed_on |
| 3 | BAJAJ-AUTO | REAL-KITE | INE917I01010 | NSE x2 + checksum | 2008-05-26 | listing precedes the data start (consistent) | 73944 / 0 | f | none recorded | isin, listed_on |
| 4 | BAJAJFINSV | REAL-KITE | INE918I01026 | NSE x2 + checksum | 2008-05-26 | listing precedes the data start (consistent) | 73944 / 0 | f | none recorded | isin, listed_on |
| 5 | CIPLA | REAL-KITE | INE059A01026 | NSE x2 + checksum | 1995-02-08 | listing precedes the data start (consistent) | 73944 / 0 | f | none recorded | isin, listed_on |
| 6 | COALINDIA | REAL-KITE | INE522F01014 | NSE x2 + checksum | 2010-11-04 | listing precedes the data start (consistent) | 73945 / 0 | f | none recorded | isin, listed_on |
| 7 | ETERNAL | REAL-KITE | INE758T01015 | NSE x2 + checksum | 2021-07-23 | = first Kite bar | 72325 / 0 | f | ZOMATO→ETERNAL 2025-04-09 | isin, listed_on |
| 8 | GRASIM | REAL-KITE | INE047A01021 | NSE x2 + checksum | 1995-05-10 | listing precedes the data start (consistent) | 73944 / 0 | f | none recorded | isin, listed_on |
| 9 | HDFCLIFE | REAL-KITE | INE795G01014 | NSE x2 + checksum | 2017-11-17 | = first Kite bar | 73234 / 0 | f | none recorded | isin, listed_on |
| 10 | HINDALCO | REAL-KITE | INE038A01020 | NSE x2 + checksum | 1997-01-08 | listing precedes the data start (consistent) | 73944 / 0 | f | none recorded (HINDALC0→HINDALCO 2007-08-27) | isin, listed_on |
| 11 | INDIGO | REAL-KITE | INE646L01027 | NSE x2 + checksum | 2015-11-10 | = first Kite bar | 73732 / 0 | f | none recorded | isin, listed_on |
| 12 | JIOFIN | REAL-KITE | INE758E01017 | NSE x2 + checksum | 2023-08-21 | = first Kite bar | 71810 / 0 | f | none recorded | isin, listed_on |
| 13 | M&M | REAL-KITE | INE101A01026 | NSE x2 + checksum | 1996-01-03 | listing precedes the data start (consistent) | 73944 / 0 | f | none recorded | isin, listed_on |
| 14 | MAXHEALTH | REAL-KITE | INE027H01010 | NSE x2 + checksum | 2020-08-21 | = first Kite bar | 72554 / 0 | f | none recorded | isin, listed_on |
| 15 | NESTLEIND | REAL-KITE | INE239A01024 | NSE x2 + checksum | 2023-08-01 | DISCREPANCY (NSE date after first bar) | 73944 / 0 | f | none recorded | isin, listed_on (listed_on stays NULL) |
| 16 | ONGC | REAL-KITE | INE213A01029 | NSE x2 + checksum | 1995-07-19 | listing precedes the data start (consistent) | 73945 / 0 | f | none recorded | isin, listed_on |
| 17 | SBILIFE | REAL-KITE | INE123W01016 | NSE x2 + checksum | 2017-10-03 | = first Kite bar | 73263 / 0 | f | none recorded | isin, listed_on |
| 18 | SHRIRAMFIN | REAL-KITE | INE721A01047 | NSE x2 + checksum | 1996-12-11 | listing precedes the data start (consistent) | 73944 / 0 | f | SRTRANSFIN→SHRIRAMFIN 2022-12-20 | isin, listed_on |
| 19 | TATACONSUM | REAL-KITE | INE192A01025 | NSE x2 + checksum | 1998-11-18 | listing precedes the data start (consistent) | 73944 / 0 | f | TATAGLOBAL→TATACONSUM 2020-02-27 (TATATEA→TATAGLOBAL 2010-07-21) | isin, listed_on |
| 20 | TECHM | REAL-KITE | INE669C01036 | NSE x2 + checksum | 2006-08-28 | listing precedes the data start (consistent) | 73947 / 0 | f | none recorded | isin, listed_on |
| 21 | TMPV | REAL-KITE | INE155A01022 | NSE x2 + checksum | 1998-07-22 | listing precedes the data start (consistent) | 73940 / 0 | f | TATAMOTORS→TMPV 2025-10-24 (TELCO→TATAMOTORS 2003-12-26) | isin, listed_on |
| 22 | ADANIPORTS | REAL-MIXED | INE742F01042 | NSE x2 + checksum | 2007-11-27 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded (MUNDRAPORT→ADANIPORTS 2012-01-17) | isin, listed_on; is_demo: option (see 8) |
| 23 | ASIANPAINT | REAL-MIXED | INE021A01026 | NSE x2 + checksum | 1995-05-31 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 24 | AXISBANK | REAL-MIXED | INE238A01034 | NSE x2 + checksum | 1998-11-16 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded (UTIBANK→AXISBANK 2007-08-16) | isin, listed_on; is_demo: option (see 8) |
| 25 | BAJFINANCE | REAL-MIXED | INE296A01032 | NSE x2 + checksum | 2003-04-01 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded (BAJAUTOFIN→BAJFINANCE 2010-09-29) | isin, listed_on; is_demo: option (see 8) |
| 26 | BEL | REAL-MIXED | INE263A01024 | NSE x2 + checksum | 2000-07-19 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 27 | BHARTIARTL | REAL-MIXED | INE397D01024 | NSE x2 + checksum | 2002-02-15 | listing precedes the data start (consistent) | 73942 / 1240 | t | none recorded (BHARTI→BHARTIARTL 2006-06-19) | isin, listed_on; is_demo: option (see 8) |
| 28 | DRREDDY | REAL-MIXED | INE089A01031 | NSE x2 + checksum | 2003-05-30 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 29 | EICHERMOT | REAL-MIXED | INE066A01021 | NSE x2 + checksum | 2004-09-07 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 30 | HCLTECH | REAL-MIXED | INE860A01027 | NSE x2 + checksum | 2000-01-06 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 31 | HDFCBANK | REAL-MIXED | INE040A01034 | NSE x2 + checksum | 1995-11-08 | listing precedes the data start (consistent) | 73942 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 32 | HINDUNILVR | REAL-MIXED | INE030A01027 | NSE x2 + checksum | 1995-07-06 | listing precedes the data start (consistent) | 73940 / 1240 | t | none recorded (HINDLEVER→HINDUNILVR 2007-07-19) | isin, listed_on; is_demo: option (see 8) |
| 33 | ICICIBANK | REAL-MIXED | INE090A01021 | NSE x2 + checksum | 1997-09-17 | listing precedes the data start (consistent) | 73943 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 34 | INFY | REAL-MIXED | INE009A01021 | NSE x2 + checksum | 1995-02-08 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded (INFOSYSTCH→INFY 2011-06-29) | isin, listed_on; is_demo: option (see 8) |
| 35 | ITC | REAL-MIXED | INE154A01025 | NSE x2 + checksum | 1995-08-23 | listing precedes the data start (consistent) | 73941 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 36 | JSWSTEEL | REAL-MIXED | INE019A01038 | NSE x2 + checksum | 2005-03-23 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded (JSWSTL→JSWSTEEL 2005-09-16) | isin, listed_on; is_demo: option (see 8) |
| 37 | KOTAKBANK | REAL-MIXED | INE237A01036 | NSE x2 + checksum | 1995-12-20 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded (KOTAKMAH→KOTAKBANK 2003-04-21) | isin, listed_on; is_demo: option (see 8) |
| 38 | LT | REAL-MIXED | INE018A01030 | NSE x2 + checksum | 2004-06-23 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 39 | MARUTI | REAL-MIXED | INE585B01010 | NSE x2 + checksum | 2003-07-09 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 40 | NTPC | REAL-MIXED | INE733E01010 | NSE x2 + checksum | 2004-11-05 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 41 | POWERGRID | REAL-MIXED | INE752E01010 | NSE x2 + checksum | 2007-10-05 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 42 | RELIANCE | REAL-MIXED | INE002A01018 | NSE x2 + checksum | 1995-11-29 | listing precedes the data start (consistent) | 73948 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 43 | SBIN | REAL-MIXED | INE062A01020 | NSE x2 + checksum | 1995-03-01 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 44 | SUNPHARMA | REAL-MIXED | INE044A01036 | NSE x2 + checksum | 1995-02-08 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 45 | TATASTEEL | REAL-MIXED | INE081A01020 | NSE x2 + checksum | 1998-11-18 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded (TISCO→TATASTEEL 2005-10-17) | isin, listed_on; is_demo: option (see 8) |
| 46 | TCS | REAL-MIXED | INE467B01029 | NSE x2 + checksum | 2004-08-25 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 47 | TITAN | REAL-MIXED | INE280A01028 | NSE x2 + checksum | 2004-09-24 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 48 | TRENT | REAL-MIXED | INE849A01020 | NSE x2 + checksum | 2004-06-07 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded (LAKME→TRENT 2004-06-07) | isin, listed_on; is_demo: option (see 8) |
| 49 | ULTRACEMCO | REAL-MIXED | INE481G01011 | NSE x2 + checksum | 2004-08-24 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 50 | WIPRO | REAL-MIXED | INE075A01022 | NSE x1 + checksum | 1995-11-08 | listing precedes the data start (consistent) | 73944 / 1240 | t | none recorded | isin, listed_on; is_demo: option (see 8) |
| 51 | CUMMINSIND | DEMO-ONLY | INE298A01020 (ref) | reference only | 1995-03-29 | n/a | 0 / 1240 | t | - | none (DEMO identity, no real candles) |
| 52 | DMART | DEMO-ONLY | INE192R01011 (ref) | reference only | 2017-03-21 | n/a | 0 / 1240 | t | - | none (DEMO identity, no real candles) |
| 53 | HAL | DEMO-ONLY | INE066F01020 (ref) | reference only | 2018-03-28 | n/a | 0 / 1240 | t | - | none (DEMO identity, no real candles) |
| 54 | PERSISTENT | DEMO-ONLY | INE262H01021 (ref) | reference only | 2010-04-06 | n/a | 0 / 1240 | t | - | none (DEMO identity, no real candles) |
| 55 | PIDILITIND | DEMO-ONLY | INE318A01026 (ref) | reference only | 1995-03-29 | n/a | 0 / 1240 | t | - | none (DEMO identity, no real candles) |
| 56 | POLYCAB | DEMO-ONLY | INE455K01017 (ref) | reference only | 2019-04-16 | n/a | 0 / 1240 | t | - | none (DEMO identity, no real candles) |
| 57 | TVSMOTOR | DEMO-ONLY | INE494B01023 (ref) | reference only | 2000-08-02 | n/a | 0 / 1240 | t | - | none (DEMO identity, no real candles) |
| 58 | INDIA VIX | DEMO-INDEX | n/a | index | - | n/a | 0 / 0 | t | - | none |
| 59 | NIFTY 50 | DEMO-INDEX | n/a | index | - | n/a | 0 / 0 | t | - | none |
| 60 | NIFTY BANK | DEMO-INDEX | n/a | index | - | n/a | 0 / 0 | t | - | none |
| 61 | IT3EF53C1C0 | TEST-ARTIFACT | n/a | test artifact | - | n/a | 0 / 0 | f | - | isolate (exclusion list); optional status SUSPENDED |
| 62 | IT3EF53C1C1 | TEST-ARTIFACT | n/a | test artifact | - | n/a | 0 / 0 | f | - | isolate (exclusion list); optional status SUSPENDED |
| 63 | ITF2FA122D0 | TEST-ARTIFACT | n/a | test artifact | - | n/a | 0 / 1 | f | - | isolate (exclusion list); optional status SUSPENDED |
| 64 | ITF2FA122D1 | TEST-ARTIFACT | n/a | test artifact | - | n/a | 0 / 0 | f | - | isolate (exclusion list); optional status SUSPENDED |

## 6. D1.5 Reconciliation

**ISIN.** 50 of 50 NIFTY 50 instruments have an ISIN in E1; 49 also in E2 and all agree; all 50 pass the ISIN check digit; no duplicate. `WIPRO` is single-source (see below).

**Membership against today's NSE list.** The database universe (effective 2026-09-01) has 50 members; E2 (2026-11-25) has 50. They differ: **`WIPRO` is in the database but not in E2, and `BSE` is in E2 but not in the database.** D1 does not change membership; it is recorded as an exception. The 50 are therefore "the 50 in the database's universe", not necessarily today's NIFTY 50. Membership history needs NSE index press releases (not collected).

**Listing date.** 6 instruments have a first Kite bar equal to the NSE listing date (`ETERNAL`, `HDFCLIFE`, `INDIGO`, `JIOFIN`, `MAXHEALTH`, `SBILIFE`), which supports the token-to-security mapping for those six. 43 have a listing date before the data start (consistent). **`NESTLEIND` is a discrepancy:** E1 gives 2023-08-01 but Kite daily bars start 2015-01-01. The E1 date is probably the listing date of the current ISIN or share class (not verified), so `listed_on` stays UNRESOLVED.

**Symbol history.** E3 records changes for 4 instruments inside the 2015+ data window: `TATACONSUM` (from `TATAGLOBAL`, 2020-02-27), `SHRIRAMFIN` (from `SRTRANSFIN`, 2022-12-20), `ETERNAL` (from `ZOMATO`, 2025-04-09) and `TMPV` (from `TATAMOTORS`, 2025-10-24); and for other instruments only before 2015 (shown in the matrix). "None recorded" means no entry in E3; it is **not** proof that no change happened. The stored daily history of these four runs under the new symbol back to 2015 (the provider's continuing series). For `TMPV` this spans the 2025 demerger; price adjustment is D2.

**Provider token.** The `ZERODHA_KITE` token of each instrument was **not** verified against a Kite instrument master (needs a broker session; the DB token is the only evidence). Status: UNVERIFIED. The six listing-date matches are the only independent support.

**Tick evidence (D3 input).** The 21 REAL-KITE instruments have a single snapshot effective 2026-11-19 (no earlier tick). The 29 REAL-MIXED and 7 DEMO-ONLY instruments carry a demo placeholder snapshot (`2000-01-01`, tick 0.05) in addition; the 3 indices carry `2000-01-01`, tick 0.01. Pre-2026-11-19 ticks are UNKNOWN for all 50. D1 changes nothing here.

### 6.1 The 29 mixed instruments

- **One instrument id, two data sources.** Each of the 29 has Kite candles (from 2015 daily, from 2024 intraday, to 2026-11-19) **and** 1,240 DEMO bars (250 15m, 240 1D, 750 5m; daily 2025-12-15 to 2026-11-13, intraday 2026-11-02 to 2026-11-13).
- **The two sources occupy the same keys.** For these 29, DEMO and Kite bars share 6,264 15m keys and 18,792 5m keys (same instrument and `bar_start`), and 6,525 daily keys (same `trade_date`). Candle rows are separated by `data_source_id`, so nothing is overwritten, but **any research query that ignores the data source would double count or mix synthetic and real bars.** The rule in §3 prevents it.
- **Every candle has an ingestion run** (0 without); the 1 stray DEMO bar belongs to a FAILED DEMO run.
- **Provider refs.** Each has a live `DEMO` ref (no `valid_to`) and a live Kite ref.
- **Instrument-level flag.** `is_demo = true` is wrong for the identity (a real listed company) but right for the demo candles; it cannot express both. The source-based rule resolves this without changing the flag.

### 6.2 Exception register

| ID | Exception | Evidence | Handling in D1 |
|---|---|---|---|
| X1 | 29 REAL-MIXED instruments flagged `is_demo` with real Kite data | §3, §6.1, E6 | Classify by candle source; no flag change without owner approval |
| X2 | 36 demo placeholder snapshots (`2000-01-01`, 0.05): 29 mixed + 7 demo-only; 3 index placeholders (0.01) | database | Mark pre-2026-11-19 ticks UNKNOWN; D3 owns the fix |
| X3 | 21 REAL-KITE instruments have no snapshot before 2026-11-19 | database | Same as X2 |
| X4 | 4 test artifacts (`name = t`, `is_demo = false`, no ISIN, no snapshot) | database, created 2026-11-18 | Isolate by exclusion list; **never delete**; optional status change in D1.7 |
| X5 | 1 stray DEMO 5m bar on `ITF2FA122D0` (2026-11-17, belongs to a FAILED DEMO ingestion run) | database | Ineligible by the source rule; original record preserved |
| X6 | `NESTLEIND` NSE listing date after the first Kite bar | E1 versus database | `listed_on` UNRESOLVED |
| X7 | `WIPRO` in the database NIFTY 50 universe, not in E2; `BSE` in E2, not in the database | E2 versus database | Record only; membership decision belongs to the owner |
| X8 | Token to ISIN link unverified for 44 of 50 | no Kite master available | UNVERIFIED; needs a broker session |
| X9 | 2,474,382 Kite 5m/15m bars belong to ingestion runs with status `PARTIAL`; one `PERSONAL` run still shows `RUNNING` since 2026-11-20; 3 `PERSONAL` runs `FAILED` | database | **Not** classified as ineligible (they are real source data), but completeness is unproven; D4/D5 |
| X10 | Symbol changes recorded by NSE file, not by circular | E3 | UNRESOLVED at circular level |
| X11 | Demo-only equities carry real tickers and (as reference) real ISINs, but no real data | matrix | Keep DEMO; `isin` stays NULL |

## 7. D1.6 Per-instrument change proposal (D1.7; NOT approved; nothing applied)

Before values: `isin` NULL, `listed_on` NULL, `is_demo` as in the matrix. Each write would be per instrument, in a transaction, with an `audit_logs` row, an evidence id (E1-E6), and a dry-run diff. No candle row is touched.

| Group | Rows | Field | Before | Proposed after | Evidence | Confidence | Impact |
|---|---|---|---|---|---|---|---|
| A | 49 REAL (all except `WIPRO`) | `isin` | NULL | ISIN from the matrix | E1 + E2 + check digit | **High** | Lets research joins use a stable identity; no behaviour change today |
| A2 | `WIPRO` | `isin` | NULL | `INE075A01022` | E1 only + check digit | **High-Medium** (single NSE source; membership X7) | Same |
| B | 49 REAL (all except `NESTLEIND`) | `listed_on` | NULL | NSE listing date from the matrix | E1 | **Medium** (E1 date is the NSE listing date of the current record; X6 shows it can differ from first trading) | Informational; later sanity check for data starts |
| B2 | `NESTLEIND` | `listed_on` | NULL | stay NULL | E1 versus data | n/a | None |
| C (option 1, **recommended**) | 29 mixed | `is_demo` | `true` | **unchanged** (informational; source rule governs) | §6.1 | High that the flag cannot express both | Zero risk to demo mode |
| C (option 2) | 29 mixed | `is_demo` | `true` | `false` | §6.1, E6 | Medium: flipping makes 1,240 DEMO bars each sit on a "non-demo" instrument; **UI and engine effects not assessed** | Possible effect on DEMO-mode lists and on the demo universe; needs an impact check before any write |
| D | 4 test artifacts | handling | `ACTIVE`, `is_demo = false` | exclusion list (no write); optional `status = SUSPENDED` | X4 | High that they are test fixtures; `SUSPENDED` is not an exact description (allowed values: ACTIVE, SUSPENDED, DELISTED) | None in option 1; option 2 changes only status |
| E | 1 stray DEMO bar | candle | as is | **no change** (ineligible by rule; record preserved) | X5 | High | None |
| F | 7 demo-only + 3 indices | all | as is | no change | X11 | High | None |
| G | Symbol history | storage | none | mapping file entries for 4 in-window and the pre-2015 changes (no schema) | E3 | **Medium** (E3 only; circulars not collected) | None until a table exists |

**Unresolved questions for the owner:** (1) group C option 1 or 2; (2) test-artifact option; (3) whether to keep E1-E4 (licensing) and where (§9); (4) membership for `WIPRO`/`BSE` (X7); (5) whether to obtain circular PDFs behind the four in-window symbol changes; (6) a broker session to verify tokens (X8).

**Validation plan (before and after a write).** Fresh backup with the D0 procedure (needs the recovery key: decide T-I165 first); rehearsal on a scratch restore; dry-run diff equals the approved list; manifest after differs only in the approved cells; ISIN check digit and uniqueness re-checked; `ck_instruments__*` constraints pass; test suites on `priceaction_test`.

**Rollback.** A rehearsed reverse update from the pre-write dump for the changed cells only; no candle rows exist to restore; additive schema changes are not proposed.

## 8. Remaining D2-D6 and backtest dependencies

| Item | Depends on D1 how | Still blocked by |
|---|---|---|
| D2 corporate actions (`corporate_actions` has 0 rows) | Needs the identity map (ISINs, symbol history); the `TMPV` demerger and the `TATACONSUM`, `SHRIRAMFIN`, `ETERNAL` symbol changes | DR-7a reviewer for curated data; owner authorisation |
| D3 tick rules | Needs identity and effective dates; ticks before 2026-11-19 UNKNOWN (X2, X3) | D1, D2; DR-7a; MG02-A1 adoption decision |
| D4 calendar | Independent of D1 | Owner authorisation; DR-7a |
| D5 five missing-bar sessions (read-only re-fetch) | Needs D1 identity and D4 calendar; a broker session | D1, D4; owner authorisation |
| D6 post-remediation P0-1 | Needs D1-D5, a frozen dataset and independent human review | All of the above; contract approval |
| Stage A and any historical or prospective backtest | Need D1-D6, the validation-plan approvals, E1-E11 | Not authorised |
| Completeness of `PARTIAL`-run candles (X9) | D4/D5 | Owner decision |
| Membership history and survivorship | Needs NSE index press releases | Not scheduled; remains a documented limit |

## 9. Evidence location (approved and created 2026-11-25)

The owner approved `~/priceaction-backups/d1-20261125/evidence/` ([DEC-037](../../DECISIONS.md)). The scratchpad evidence was inventoried, copied without overwriting and verified (all 13 original files match their hashes); later evidence was added and a manifest with SHA-256 sums was written. See the [data foundation report §2.1](orb-data-foundation-report.md#21-d1-evidence-preservation-verified). The NSE licence question (§4) is still open: no licensing clearance is claimed.

**Later updates to this page's exceptions** (the table above is left as written): X7 `WIPRO` ISIN is now corroborated by four sources; X6 `NESTLEIND` is explained only in part (NSE circulars show an ISIN change on 2024-01-05 and a bonus listing on 2025-08-12, not 2023-08-01); X9 the PARTIAL runs are assessed in report §2.4. The ISIN is not stable over the history for split instruments (report §2.3).

## 10. What D1 did not do

No database write, schema change, candle change or deletion; no D1.7; no D2-D6; no P0-1/P0-1b; no backtest; no service restart; no `ORB-MG-02`, B0, PAQS or ruleset change; no commit or push; no purchase or use of a paid NSE product; T-I165 not executed. Review statements are AI-assisted and NON-INDEPENDENT.
