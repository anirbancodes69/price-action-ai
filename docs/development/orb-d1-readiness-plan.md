# ORB D1 Readiness: AI-Assisted Review and Execution Plan

| Field | Value |
|---|---|
| Version | 1.1.0 (2026-11-25). **Update:** the owner adopted DR-11 for D1 only and authorised D1.0-D1.6 ([DEC-036](../../DECISIONS.md)); they were run read-only and are reported in [orb-d1-results.md](orb-d1-results.md). This plan text is otherwise unchanged. D1.7 is still not approved |
| Status | **PLAN ONLY. D1 is NOT authorised.** D0 stays ACCEPTED WITH CAVEATS ([DEC-035](../../DECISIONS.md)); R13 restrictions stay in force ([DEC-034](../../DECISIONS.md)). Every review statement below is **AI-assisted and NON-INDEPENDENT**: it is not a review by an independent human and does not satisfy DR-7 / DR-7a |
| Related | [Remediation page](orb-data-remediation.md) (DR-4, DR-7, DR-7a, §3, §5 row D1) · [D0 package](orb-d0-review-package.md) · [ARC-03](../architecture/03_DATABASE_DESIGN.md) |
| Method | Read-only. Documents read; evidence checksums re-verified; development database queried in a **read-only session** (counts only). No database write, no network fetch, no service restart, no P0-1/P0-1b, no backtest, no change to B0, `ORB-MG-02`, PAQS or rulesets |

## 1. AI-assisted review of the D0 and governance state

### 1.1 What was reviewed

D0 acceptance records (DEC-032 to DEC-035, [package §1-§6](orb-d0-review-package.md#1-acceptance-matrix)), DR-7, DR-7a, DR-10, R13 ([remediation §2.10](orb-data-remediation.md#210-r13-proposed-minimum-sufficient-remediation-approved-approach-only)), R14, and the owner-run log `owner-review-20261124T213558Z-owner.log`.

### 1.2 Findings

| # | Finding | Severity | Classification |
|---|---|---|---|
| F1 | **DR-7 states that "the AI session cannot be the reviewer".** The owner's current direction (an AI technical review in place of waiting for a human) conflicts with an approved decision. It must not be resolved by assumption: it needs a formal owner decision (§2). DR-7a stays **OPEN** | High (governance) | Governance conflict; AI-assisted observation |
| F2 | The D0 review was owner-executed but **NON-INDEPENDENT**, and R5 rests on owner attestation (the key steps were not observed by anyone else) | Known caveat | Already recorded (DEC-035) |
| F3 | The official `verify_key_from_clipboard.sh` fails on a key copied with a trailing space; recovery was proven only by a manual method whose output is not in the evidence folder | Medium | Known (T-I165, proposal-only) |
| F4 | All three backup copies are on the same Mac; the key exists only in the password manager | High (availability) | Known, accepted (DEC-032) |
| F5 | The package heading "§3 Independent reviewer checklist (DR-7a: OPEN)" is stale next to the NON-INDEPENDENT self-review. Wording only; not changed in this step | Low | Inconsistency reported, not fixed |
| F6 | **D1 facts that matter** (read-only counts, §3): no instrument has an ISIN or a listing date; 29 of the 50 NIFTY 50 instruments are flagged `is_demo = true` yet carry real provider candles; four non-demo instruments are integration-test artifacts, one of them holding a stray `DEMO` bar | High for D1 | Reproduced from the database (AI-assisted) |
| F7 | `audit_logs` holds no instrument rows and no instrument has been updated since creation: **there is no history of any `is_demo` change**, so provenance for the flag cannot come from the database | Medium | Reproduced (AI-assisted) |

### 1.3 Verified, and by whom

"Reproduced" means the AI re-ran a check in this session from repository or evidence files. It is still **NON-INDEPENDENT**: the same assistant prepared much of the material.

| Item | Status |
|---|---|
| Six evidence checksum lists (0 failures each) | **Reproduced** (AI-assisted) |
| Ciphertext hashes of copy A, copy B (`verify_offdevice.sh`), and the Desktop duplicate | **Reproduced** (AI-assisted); decryption was *not* re-run (no key was read or used) |
| Development manifest equals the baseline (hash `e74c391c473c…` before and after) | **Reproduced** (AI-assisted) |
| D1 baseline counts in §3 | **Reproduced** (read-only queries) |
| Documents consistent with DEC-035 and its caveats | **Reproduced** (AI-assisted reading); F5 is the only inconsistency found |
| Test isolation (engine and Laravel) | **Not re-run in this step.** It writes to `priceaction_test`; the owner-run result (R7, R8) stands |
| Key is in the password manager; the manual decryption succeeded; the key file was removed | **Not independently verifiable.** Owner attestation only (R5). The AI checked only that the key file is absent |
| That the backups are recoverable from the password-manager entry | **Needs a human or the owner** to repeat with the corrected procedure (T-I165) |
| Any claim about the real world (NSE ISINs, listing dates, symbol changes, circulars) | **Needs external evidence** and a human check of source authority; the AI has not fetched or verified any |
| Licensing and legal status of any source (DR-1) | **Needs the owner**; the AI cannot decide it |

## 2. Owner decision: how to treat DR-7 for D1 (proposed here; ADOPTED as DR-11 on 2026-11-25, D1 only)

DR-7 says curated reference data needs a preparer and a **separate independent human reviewer**, and that the AI cannot be the reviewer. If the owner wants to proceed with AI-assisted technical review, the honest way is a new, explicit decision, not a silent waiver. Draft text for the owner to accept, amend or reject:

> **DR-11 (proposed).** For D1 only, the independent human reviewer of DR-7 / DR-7a is replaced by (a) an AI-assisted technical review and (b) the owner's own review, **both labelled NON-INDEPENDENT AI-ASSISTED / OWNER REVIEW**. This is **not** an independent human review. Residual risk accepted by the owner: errors or blind spots shared by the preparer (an AI-assisted engineer) and the reviewers would not be caught by a separate person; curated identity data, if wrong, can silently corrupt every later step. DR-7 and DR-7a remain in force for D2-D6 and are not changed by this decision. The decision can be withdrawn at any time; if it is, D1 outputs are re-reviewed by a human before D2 starts.

Considerations (AI-assisted advice, not a decision):
- D1's data is **cheaper to verify** than D2 and D3: identity facts (ISIN, symbol, listing date) are checkable against public lists, and the work product is a mapping, not corporate-action factors or tick rules.
- A **cheap compensating control** is available: the owner spot-checks a random sample of mapping rows against the cited source documents (suggested: all rows that are exceptions plus 10 random rows of the 50), and records the result.
- Do **not** extend this waiver to D2-D6 by implication. D2 and D3 errors are costlier and harder to see.
- The AI cannot be described as independent in any record. Records use "AI-assisted, NON-INDEPENDENT".

Until the owner decides, this plan can still be **prepared and reviewed**; **no D1 step is run**.

## 3. D1 baseline facts (read-only, 2026-11-25; development database, counts only)

| Fact | Result |
|---|---|
| Instruments | 64 = 50 NIFTY 50 members + 7 demo-only equities + 3 demo indices + 4 test artifacts |
| `isin` | **NULL for all 64** (including all 50 NIFTY 50 members) |
| `listed_on`, `delisted_on` | `listed_on` NULL for all 64; no delisting recorded |
| Symbols | 64 distinct `(exchange, trading_symbol)`; 3 contain whitespace (the index names) |
| `is_demo` | 39 true (29 NIFTY 50 members + 7 demo-only equities + 3 indices); 25 false (21 NIFTY 50 members + 4 test artifacts) |
| Data sources | 2: `DEMO/DEMO` and `PERSONAL/ZERODHA_KITE` (both active) |
| Candles on the **29 mixed instruments** | both `DEMO` (15m, 5m, 1D, roughly 2025-12 to 2026-11-13) **and** `PERSONAL` Kite candles (2015 to 2026-11-19 daily; 2024 to 2026-11-19 intraday). One instrument id, two data sources |
| Candles on the **21 non-demo NIFTY 50 instruments** | Kite only |
| `DEMO` candles total | 44,640 bars on the 36 demo instruments, plus **1 stray 5m `DEMO` bar** on a non-demo test instrument (44,641 in total) (2026-11-17, ingestion run recorded) |
| Instrument snapshots | 89 rows over 60 instruments; **36 instruments carry the demo placeholder** (`effective_from 2000-01-01`, tick 0.05); 50 have a later effective date |
| Provider refs | 93 = 43 `DEMO` + 50 `ZERODHA_KITE`; all have `valid_from`; none has `valid_to`; each NIFTY 50 instrument has 1 or 2 |
| NIFTY 50 universe | 50 members, one effective date (2026-09-01), `source_ref` present; no history of earlier constituents |
| Test artifacts | 4 instruments with symbols `IT…`/`ITF…` and name `t` (created 2026-11-18, `is_demo = false`) |
| Audit | `audit_logs` has no rows about instruments; no instrument was ever updated after creation |
| `corporate_actions`, `market_calendar` | 0 and 397 rows (D2 and D4 scope; unchanged here) |

Consequence for ORB: the `is_demo` flag is **not a reliable guide to which candles are real**. The reliable guide is the candle's data source. A research query that selects by instrument flag instead of by data source could include or exclude the wrong rows. D1 must make the classification explicit and per candle source.

## 4. D1 objectives and deliverables (from [remediation §5](orb-data-remediation.md#5-d1-d6-dependency-and-acceptance-criteria-matrix), DR-4)

Objective: for each of the 50 NIFTY 50 instruments, record a stable identity, symbol history, listing date, data source and mode, so that no demo placeholder can be read as real data. **No bulk `is_demo` change.** Any per-instrument change needs evidence, an audit record and the owner's approval of the write.

| # | Deliverable | Form |
|---|---|---|
| 1 | Identity map of the 50 instruments: ISIN, current and previous symbols with dates, listing date, exchange, segment | Reviewed file in the repository (CSV plus JSON), with source reference and document hash per row |
| 2 | Source evidence pack: each cited NSE document with URL, retrieval time, sha256 | Immutable archive folder + manifest, outside the repository if large |
| 3 | Classification of every instrument and every candle source: REAL (provider data), DEMO (synthetic), TEST ARTIFACT | Report (counts and the per-instrument list) |
| 4 | Dispositions of the 14 non-NIFTY-50 instruments (7 demo-only equities, 3 indices, 4 test artifacts) | Proposal list; no change without owner approval |
| 5 | Design for provenance columns (`basis`, source, mode) on shared reference rows, as an additive migration proposal | ARC-03 change proposal; **not applied** |
| 6 | Proposed per-instrument change list for any `is_demo` or identity write, each row with evidence | Owner-approval list |
| 7 | D1 evidence report: queries, outputs, hashes, mismatches | Immutable report with sha256 |

## 5. Required source evidence (DR-1: public official sources first)

| Need | Authority (primary) | Note |
|---|---|---|
| ISIN for each of the 50 | NSE's published equity master / official listings and index factsheet | Provider tokens are **not** identity authority; a broker instrument file may lack the ISIN and is a lead only |
| NIFTY 50 membership over the study period | NSE Indices press releases and constituent lists | **Needed for the survivorship note** (today's list is applied to all history, an accepted limitation); D1 records which constituents the 50 are, it does not repair survivorship |
| Listing date, symbol changes, mergers | NSE listing and symbol-change circulars; corporate announcements | Feeds the symbol history; also needed by D2 |
| Demo versus real status of each candle source | The database (`data_sources`, `ingestion_runs`) and the repository's demo seeder | Internal evidence |

Not allowed without a recorded review: purchase of any paid NSE product (DR-1). The AI has not fetched or verified any source.

## 6. Execution plan (to run only after owner authorisation)

Legend: **RO** read-only, **FILE** writes files outside the database, **DB** writes to a database (never in D1.0 to D1.5).

| Step | Name | Type | What happens | Output / gate |
|---|---|---|---|---|
| D1.0 | Preconditions | RO | Confirm D0 evidence checksums, development manifest equals the baseline, services unchanged, owner decisions of §8 recorded | Gate: all true |
| D1.1 | Re-baseline | RO | The §3 queries run again with a timestamp; compare with this plan | Baseline report with hash; gate: unchanged since 2026-11-25 or explained |
| D1.2 | Provenance classification | RO | Per instrument: candle sources, first and last bar per source, provider refs, snapshot type, created date; per candle source: data source mode and ingestion runs | Classification report; flags the 29 mixed instruments, the 4 test artifacts and the stray `DEMO` bar |
| D1.3 | Source collection | FILE | With owner authority, collect the NSE documents (DR-1), store immutably with sha256 and retrieval time | Evidence pack; no database access |
| D1.4 | Identity map preparation | FILE | Build the 50-row identity map from the evidence, one cited source per field; list unresolved fields explicitly (never fill by guess) | Draft map; every cell has a source or `UNRESOLVED` |
| D1.5 | Reconciliation and review | FILE + RO | Compare the map with the database (symbols, `provider_token`s, universe membership); list every mismatch; AI-assisted technical review; owner spot-check of the sample | Reconciliation report; **review labelled NON-INDEPENDENT** unless a human reviewer is named |
| D1.6 | Proposal and approval | FILE | Per-instrument change list and the additive schema proposal; owner approves, amends or rejects each | Signed-off list (owner decision) |
| D1.7 | Controlled write (only if approved) | **DB** | See §7 | Post-write manifest comparison; evidence |

Each step's outputs are hashed; a corrected run is a new, dated report (no edits). Stop and report on any unexplained mismatch.

### 6.1 Validation rules for the identity map

1. Exactly 50 rows, one per NIFTY 50 instrument in the database; no row added or dropped silently.
2. ISIN: 12 characters, valid ISIN checksum, unique across the 50, taken from a cited source; `UNRESOLVED` if absent.
3. Symbol history: contiguous, non-overlapping date ranges; the current symbol matches `instruments.trading_symbol` and the Kite provider ref; every change cites a circular.
4. Listing date not later than the first candle of that instrument in the database; if the first candle is earlier, the discrepancy is listed.
5. A demo placeholder (the `2000-01-01` snapshot, the `DEMO` provider ref, `DEMO` candles) is classified DEMO and is never counted as real data.
6. A candle is REAL only if its data source mode is `PERSONAL` and its ingestion run is recorded; otherwise it is excluded from research input until classified.
7. Nothing is inferred from the symbol alone (`RELIANCE` in the demo seeder is not evidence of real data).
8. No conflict is resolved silently: conflicts go to a list with both values and sources.

### 6.2 Read-only queries (reference; run only in D1.1 and D1.2)

All run in a read-only session (`default_transaction_read_only=on`), counts and keys only:

```sql
-- Q1 identity completeness
SELECT count(*) AS n, count(isin) AS with_isin, count(listed_on) AS with_listing, count(*) FILTER (WHERE is_demo) AS demo FROM instruments;
-- Q2 candle sources per instrument
SELECT i.trading_symbol, i.is_demo, ds.mode, ds.provider, c.timeframe, count(*) AS bars, min(c.trade_date), max(c.trade_date)
FROM candles c JOIN data_sources ds ON ds.id = c.data_source_id JOIN instruments i ON i.id = c.instrument_id
GROUP BY 1,2,3,4,5 ORDER BY 1,3,5;
-- Q3 stray cross-mode candles
SELECT i.trading_symbol, i.is_demo, ds.mode, c.timeframe, count(*) FROM candles c
JOIN data_sources ds ON ds.id = c.data_source_id JOIN instruments i ON i.id = c.instrument_id
WHERE (ds.mode = 'DEMO') <> i.is_demo GROUP BY 1,2,3,4;
-- Q4 snapshots and placeholders
SELECT instrument_id, effective_from, tick_size FROM instrument_snapshots WHERE effective_from = DATE '2000-01-01';
-- Q5 provider refs and membership
SELECT provider, count(*), count(DISTINCT instrument_id) FROM instrument_provider_refs GROUP BY 1;
SELECT u.code, count(*), min(effective_from), max(effective_from) FROM universe_memberships um JOIN universes u ON u.id = um.universe_id GROUP BY 1;
-- Q6 history of changes (should be empty)
SELECT action, count(*) FROM audit_logs WHERE entity_type ILIKE '%instrument%' GROUP BY 1;
```

## 7. Rollback and safeguards

Steps D1.0 to D1.6 change **no database**; there is nothing to roll back except files.

If the owner approves D1.7, all of these apply:
1. **Fresh backup first:** repeat the D0 backup procedure (dump, ciphertext, hashes) and verify the pre-write manifest equals the D0 baseline or explain the difference. This uses the recovery key, so [T-I165](orb-d0-review-package.md#21-recovery-caveat-trailing-space-and-a-proposed-correction-not-yet-adopted) should be decided first.
2. **Rehearse on the disposable restore** (a scratch container made from the backup), never first on the development database. The result is compared with the plan.
3. **Additive only:** new columns or tables (a Laravel migration, ARC-03 updated, a down-migration that drops only what was added). No change to candle rows, ever. No UPDATE of `candles`.
4. **Per-instrument changes only**, each tied to an evidence id and an owner-approved list; each in one transaction with an `audit_logs` row; a dry-run diff is shown before the write.
5. **Single writer:** the table owner's path is used (Laravel migration for schema; the engine for instrument rows, per ARC-01 §6); no ad-hoc SQL as `postgres`.
6. **After:** manifest comparison (only the approved rows differ), the test suites against `priceaction_test`, and the evidence report.
7. **Abort rule:** any difference from the approved list stops the work; the rollback is the down-migration plus restore of the changed rows from the pre-write backup, rehearsed on the scratch copy first.

## 8. Decisions that still need explicit owner approval

| # | Decision | Needed for |
|---|---|---|
| OD-D1-1 | Accept, amend or reject the proposed **DR-11** (§2): AI-assisted plus owner review for D1 only, labelled NON-INDEPENDENT, DR-7 and DR-7a unchanged for D2-D6; or name an independent human reviewer instead | D1.5 sign-off |
| OD-D1-2 | **Authorise D1 start**, step by step: D1.0-D1.2 (read-only), D1.3-D1.6 (files, with network), D1.7 (database write) are separate authorisations | Every step |
| OD-D1-3 | Authorise **network retrieval** of public NSE documents (DR-1) and the storage location of the evidence pack | D1.3 |
| OD-D1-4 | **Identity key**: ISIN plus symbol history (proposed) | D1.4 |
| OD-D1-5 | **Classification policy** for the 29 mixed instruments: candle-level source (DEMO versus PERSONAL) is authoritative; the instrument `is_demo` flag is informational until changed per instrument with evidence | D1.2, D1.6 |
| OD-D1-6 | Disposition of the 4 test-artifact instruments and the stray `DEMO` bar: leave, mark, or remove (removal is a database write and needs a separate approval) | D1.6 |
| OD-D1-7 | Approve an **additive schema change** for provenance (`basis`, source, mode) or keep D1 as a mapping file only; schema work needs a migration and ARC-03/ARC-04 updates | D1.6/D1.7 |
| OD-D1-8 | **T-I165** (recovery-script correction): adopt or not, before any step that needs the key | D1.7 |
| OD-D1-9 | When the stopped services may restart (D1 itself does not need the backend, queue, scheduler or engine) | Not needed for D1.0-D1.6 |
| OD-D1-10 | Whether the D1 acceptance criterion "reviewer sign-off" is met by OD-D1-1 | D1 acceptance |

## 9. What this plan does not do

It authorises nothing. D1 is not started; no source was fetched; no database row, service, strategy, ruleset, PAQS rule or B0/`ORB-MG-02` text changed; no P0-1/P0-1b, backtest or ORB implementation was run. D2-D6 are untouched. The review above is **AI-assisted and NON-INDEPENDENT**.
