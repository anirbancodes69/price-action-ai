# ORB Historical Data Remediation: Decisions, D0 Specification and Plan

| Field | Value |
|---|---|
| Version | 1.6.0 (2026-11-25, owner approval of the NON-INDEPENDENT D0 self-review recorded; key procedure and review tooling prepared; review not yet executed) |
| Status | **D0 is ACCEPTED WITH CAVEATS (owner, 2026-11-25, [DEC-035](../../DECISIONS.md)); the D0 review is NON-INDEPENDENT (DEC-033 / DR-10).** D0 evidence and DEC-032 are preserved. Engine and Laravel test isolation verified (§2.6, §2.7). The off-device backup requirement is WAIVED BY OWNER (DR-9, §2.8), not completed. Caveats: the official clipboard script did not pass (trailing whitespace; manual decryption passed); all backup copies are on one Mac; the key exists only in the password manager; R5 is owner attestation; DR-7 and DR-7a still apply to D1-D6. **Acceptance does not authorise D1-D6, P0-1/P0-1b, backtests, ORB implementation, service restarts, database changes or Git operations.** Database writers remain stopped. No development data, B0, `ORB-MG-02`, PAQS, ruleset or strategy changed** |
| Related | [ORB specification](../strategies/opening-range-breakout.md) · [Validation plan](../research/orb-validation-plan.md) · [Decisions and readiness](orb-phase2-decisions-and-readiness.md) · [DEC-028](../../DECISIONS.md) · [Research data limitations](../research/research-data-limitations.md) |
| Origin | The P0-1 counts-only scan (run 2026-11-23, accepted with limitations in its independent review) showed that the historical development data cannot yet be trusted for ORB B0 validation: tick-size reference data is placeholder, corporate actions and the exchange calendar are unrecorded, and instrument metadata mixes data modes |

## 1. Owner decision register (2026-11-23)

Ids `DR-n` are new. Earlier ids (`OD-n`) are unchanged: **OD-8, OD-15 and OD-16 remain open**, OD-14 stays approved, and nothing in this page changes B0.

| ID | Decision | Status | Conditions and notes |
|---|---|---|---|
| **DR-1** | Public official exchange circulars are the primary source for historical reference data; paid NSE data products are permitted where needed | **APPROVED** | Any paid product needs a recorded review of source authority, licensing and provenance **before** purchase or use. No purchase or subscription has been made or authorised by this record. Secondary sources (broker bulletins, news) are leads only and never the authority |
| **DR-2** | Prepare a formal `ORB-MG-02` amendment proposal (hard tick validation only when the historical effective tick is known and the price basis is unadjusted; unknown ticks become `UNKNOWN`/`UNVERIFIABLE`, not failed OHLC; provider-adjusted prices not subjected to the original tick grid unless the adjustment basis makes that valid) | **SUBSTANTIVE POLICY FORMALLY APPROVED (owner, 2026-11-23).** Basic OHLC validity stays hard; tick validation only when the historical effective tick is known and the price basis is unadjusted; four statuses `TICK_VERIFIED_PASS`, `TICK_VERIFIED_FAIL`, `TICK_UNKNOWN`, `TICK_UNVERIFIABLE`; only `TICK_VERIFIED_FAIL` is a tick-based hard failure | **Owner decisions of 2026-11-23: no adjusted-price tick-validation exception is approved; "known historical tick" requires verifiable instrument identity, effective period, source provenance and applicable price basis; a provider-dump observation alone is insufficient without documented historical semantics; the seven extra vectors remain proposed, not approved** (§4.3, §4.10). The text is **not yet adopted into the ORB specification** and nothing is implemented. **Frozen B0 and the existing `ORB-MG-02` are unchanged** |
| **DR-3** | Corporate-action coverage includes **material price-affecting events**; **unreconciled material events exclude the affected instrument-sessions from Stage A** | **APPROVED (rule)** | Open sub-decision **DR-3a**: the definitions of "material" and of "affected instrument-session" are proposed in §5 (D2) but are **not approved**; D2 cannot be accepted until the owner approves them |
| DR-3a | Definitions of "material" and "affected instrument-session" | **APPROVED WITH CLARIFICATION (owner, 2026-11-23)** | Approved text in §5 ("Approved definitions for DR-3a"). No arbitrary universal five-session exclusion. D2 may now be prepared, but D0 acceptance and D1 come first |
| **DR-4** | Separate instrument identity, market-data source and demo environment; **no bulk update of existing `is_demo` values without provenance evidence** | **APPROVED** | No `is_demo` value is changed now. Any change is per instrument, with provenance evidence and an audit record, and needs owner approval of the write. Design is part of D1 |
| **DR-5** | Read-only provider re-fetch of the five missing opening-range sessions, with immutable raw-response archiving; **no candle overwrites** | **APPROVED, NOT RUN** | Not to run before D0 is complete and the archive (D5) exists. Needs a valid broker session (daily login). Results are recorded beside the stored bars; stored candles are never changed |
| **DR-6** | **D0**: dedicated test database, complete baseline of relevant tables, verified restoration before any remediation | **D0 ACCEPTED WITH CAVEATS (owner, 2026-11-25, DEC-035).** (Earlier, 2026-11-23: not accepted.) Test-isolation safeguards for the engine and Laravel are done and verified (§2.6, §2.7); the off-device requirement is **waived by the owner as a risk exception (DR-9)** | **Done:** key stored, recovery verified by a manual decryption, local key removed (owner attestation); NON-INDEPENDENT review recorded; formal acceptance. **Still open:** the independent reviewer for D1-D6 (DR-7a). Services stay stopped. D1-D6 are NOT authorised by the acceptance |
| **DR-7** | Curated reference data requires a **preparer** and a separate **independent human reviewer** | **APPROVED** (requirement unchanged; for the DR-12 scope its independent-reviewer element is covered by the solo-research exception of §2.11, DEC-045) | Ownership matrix in §3. No independent reviewer is named (DR-7a): the AI session cannot be the reviewer. Outside the DR-12 scope the earlier restriction (the owner cannot review data they prepared themselves) still applies |
| DR-7a | Name of the independent human reviewer | **No independent reviewer is named: the independent-review requirement is NOT completed.** Waived for the D0 review by DR-10 (owner, 2026-11-25). **From 2026-11-25 an OWNER-APPROVED SOLO-RESEARCH EXCEPTION is in force for the defined scope of local, exploratory research ([DR-12](#211-dr-12-dr-7a-solo-research-exception-owner-approved-2026-11-25), [DEC-045](../../DECISIONS.md)); it is an exception, not an independent review.** | No reviewer is named or assumed. The AI session is never a reviewer. Under the exception the owner approves curated data and research decisions with the controls of §2.11; such approval is labelled owner-approved, never independently reviewed. DR-7 itself is unchanged |
| DR-9 | Off-device backup requirement for D0 | **WAIVED BY OWNER (documented risk exception, 2026-11-23). NOT completed; NOT equivalent to an off-device backup** | Conditions: the encrypted copies stay in separate directories; both pass their recorded SHA-256 ciphertext checks; the restore evidence stays preserved; the key is stored in the owner's password manager (pending); the local plaintext key file is removed only after password-manager recovery is verified (pending). **Residual risk accepted by the owner:** A physical failure, theft, loss or destruction of this Mac could destroy both backup copies. Record in §2.8 and [DEC-032](../../DECISIONS.md) |
| DR-10 | Waive the independent-human-review requirement of DR-7a **for the D0 review only**; the owner completes checklist R1-R14 as an owner self-review, labelled **NON-INDEPENDENT** | **APPROVED (owner, 2026-11-25), D0 only. The self-review was executed and recorded 2026-11-24/25** | Conditions and the residual-risk statement in §2.9. Preserves DEC-032 and all original D0 evidence. DR-7 still applies to D1-D6. D0 acceptance remains a separate, explicit act |
| **DR-12** | **Solo-research exception to DR-7a** (owner-operated project, no independent human reviewer available): for local, exploratory research the owner accepts responsibility for research approvals under the controls of §2.11 | **APPROVED (owner, 2026-11-25, [DEC-045](../../DECISIONS.md)); exception, not an independent review** | Does not certify the strategy, convert AI review into independent review, waive technical or data-integrity validation, or approve commercial use, live trading, deployment, frozen-spec amendments or any specific backtest. DR-11 is unchanged (D1 only) |
| DR-11 | For **D1 only**, an AI-assisted technical review plus the owner's review replaces the independent human reviewer of DR-7 / DR-7a; every such review is labelled **NON-INDEPENDENT** | **APPROVED (owner, 2026-11-25, [DEC-036](../../DECISIONS.md)), D1 only** | Not independent human verification. DR-7 and DR-7a remain applicable to D2-D6. No earlier decision or review is changed or relabelled. D1.0-D1.6 authorised and completed ([results](orb-d1-results.md)); **D1.7 (any database write or schema change) is not approved** |
| **DR-8** | A new post-remediation counts-only P0-1 scan | **APPROVED CONDITIONALLY, NOT RUN** | Conditions, all required: remediation (D1-D5) complete, a freeze of the reference data and the scan specification, and an independent review of the preparation. A new counts-only contract, with the tick statuses of §4.5, needs owner approval first. Not authorised to run now |

**Superseded state of the first scan.** P0-1 (OD-19) was executed on 2026-11-23, reconciled by an independent review, and the original artifacts are immutable. Its `or_invalid_ohlc`, `valid_ranges` and width-band counts are not to be relied on until the post-remediation scan (DR-8).

## 2. D0: backup and restoration specification (not implemented)

**Purpose.** Before any remediation, capture a complete, verified, restorable baseline of the development database and give tests their own database so they can no longer write to development data.

### 2.1 Facts that shape the specification (read-only, 2026-11-23)
PostgreSQL 17.12 (container `postgres`, database `priceaction`, 1,042 MB, of which `candles` is 1,030 MB and about 3.5 million rows). Extensions: `plpgsql`, `citext`, `btree_gist` (needed by the no-overlap exclusion constraint on `instrument_snapshots`), `pgcrypto`. Roles: `app_migrator`, `app_engine`, `app_backend` (grants are part of the design). The Docker VM shows about 157 GB free, but the macOS host volume that holds backups has about 21 GiB free (89% used), which is the real limit. Integration tests currently write to whichever database `SCHEMA_DIFF_DATABASE_URL` names, and the lifetime counters indicate they have written to the development database.

### 2.2 Scope: relevant tables
A **full database logical dump** is the baseline (it preserves constraints, triggers, grants and extensions). The **content manifest** below is computed for these relevant tables: `instruments`, `instrument_provider_refs`, `instrument_snapshots`, `universes`, `universe_memberships`, `data_sources`, `corporate_actions`, `market_calendar`, `ingestion_runs`, `data_quality_issues`, `candles`, `candle_revisions`, `candle_snapshots`, `ruleset_versions`, `backtest_runs`, `backtest_trades` and `migrations`. Tables holding credentials or user data (for example `provider_connections`, users) are in the dump but are **not** printed, hashed into a shared report, or committed; the dump is treated as a secret.

### 2.3 Procedure (to be executed only after approval of the implementation task)

| Step | Action | Evidence recorded |
|---|---|---|
| 1. Quiesce | Stop every writer: engine worker, backend queue and scheduler jobs, ingestion cron (`INGEST_ENABLED` off), and any manual session; confirm no active writing connections | `pg_stat_activity` snapshot; list of stopped services; timestamps |
| 2. Manifest | Record before dumping: PostgreSQL version, extensions, roles, the migration list, git commit, `pg_dump --schema-only` sha256, row counts of every table, and a content hash of each relevant table (canonical ordered text; `candles` hashed in chunks by instrument, timeframe and calendar month) | `baseline_manifest.json` (counts and hashes only, no data) |
| 3. Dump | `pg_dump` custom format of the whole database; `pg_dumpall --globals-only` for roles and grants (contains password hashes: secret) | File paths, sizes, sha256 of each file |
| 4. Store | Write to a restricted-permission directory outside the repository, set files read-only, keep **two copies** on separate storage, encrypt at rest; the manifest (not the dump) may be committed | Copy checksums verified against the originals |
| 5. Verify restoration | Restore both files into a **separate scratch database or instance** (never the development database); recompute the manifest with the same procedure; compare | `restore_report.json`: every count and hash equal; schema hash equal; constraints, the exclusion constraint, triggers, extensions and grants present; restore duration |
| 6. Release | Restart writers only after the owner accepts the restore report | Owner acceptance recorded |
| 7. Test isolation | Create a dedicated `priceaction_test` database with its own role and URL; point `SCHEMA_DIFF_DATABASE_URL` only at it; add a guard that makes integration tests refuse to run against any database not named as a test database | The guard's test; a run that is rejected when pointed at the development database |
| 8. Rollback plan | A documented restore procedure, tested in step 5, to be used only into a scratch instance first and into development only with the owner's approval | The procedure text |

### 2.4 Acceptance criteria for D0
1. Baseline manifest complete for all relevant tables and the whole database, with hashes.
2. Both dump files restore into a scratch database with **byte-for-byte equal manifest results** (counts, hashes, schema hash) and all structural objects present.
3. Two verified copies exist; checksums match; the dump is encrypted and outside the repository.
4. Tests can no longer write to the development database (guard test passes; a deliberate attempt fails).
5. The report is reviewed by the independent human reviewer of DR-7 and accepted by the owner.
6. No development data changed during D0 (post-D0 manifest equals pre-D0 manifest).

**Estimated effort (estimate):** 1-2 engineer-days. **Executed 2026-11-23 (D0 scope as authorised); evidence below.** Note: criterion 3 and the "separate storage" wording of §2.3 step 4 are **waived by the owner as a documented risk exception** (DR-9, §2.8); the waiver does not make the copies off-device.

### 2.5 D0 execution record (2026-11-23; evidence produced, awaiting owner acceptance)

All steps used read-only access to the development database except the stop of the application services. Evidence files are in the scratchpad `d0/evidence/` and copied to `~/priceaction-backups/d0-20261123/evidence/` with `SHA256SUMS`.

| Step | What was done | Result |
|---|---|---|
| Quiesce | Stopped `backend`, `backend-queue`, `backend-scheduler`, `engine`; PostgreSQL and Redis untouched | Only the checking session was connected; write counters sampled 20 s apart were identical (ins 3,759,906, upd 382,454, del 20,340) |
| Baseline | Content manifest for all 53 public tables (rows and sha256 of canonical row text; `candles` in 10,830 chunks by source, instrument, timeframe and month), structure manifest (extensions, roles, ACLs, columns, constraints, indexes, triggers, functions, sequences), schema-only dump | Written before the dump; identical after it (byte-for-byte) |
| Dump | `pg_dump` custom format of the whole database (65,520,549 bytes, sha256 `b9f0b4b7…`) and `pg_dumpall --globals-only` (1,496 bytes, sha256 `3e3a6fb4…`; contains password hashes, never printed) | Taken from the quiesced database |
| Encrypt | Two copies, `openssl enc` AES-256-CBC with PBKDF2 (600,000 iterations) and a random salt per file; ciphertext sha256 recorded in `SHA256SUMS` per copy | Both copies decrypt to the original hashes. Plaintext, decrypted verification files and the work directory were deleted |
| Restore | A separate disposable `postgres:17-alpine` container (17.12, no published ports), globals first, then `pg_restore --create --exit-on-error` from copy B | Restore ran in 24 s with no errors |
| Compare (data) | Manifest of the restored database against the pre-dump baseline | **Byte-for-byte identical** (53 tables, all `candles` chunks) |
| Compare (schema) | `pg_dump --schema-only`, with the per-run `\restrict` token lines removed | **Identical** |
| Compare (structure) | Structure manifest | **Identical except two benign representation effects:** (1) column ordinal numbers differ in two tables because the development database has dropped columns and a restore renumbers them (logical column order, types, nullability and defaults are identical); (2) the `migrations` table's owner-only ACL is stored explicitly in development and as the default in the restore (same effective privileges). Not raw byte-identical |
| Roles | The three application roles (`app_migrator`, `app_engine`, `app_backend`) restored with the same attributes and grants as in the structure manifest | Matched |
| No change | Development manifest after the whole procedure against the baseline | **Identical; lifetime counters unchanged. No development data changed** |
| Cleanup | Scratch container removed | Done |

**D0 acceptance criteria (§2.4) against the evidence**

| # | Criterion | Result |
|---|---|---|
| 1 | Baseline manifest complete for all relevant tables and the whole database | **Met** (53 tables hashed; full dump) |
| 2 | Restore equals baseline (counts, hashes, schema hash, structure) | **Met for data and schema; structure identical after two documented representation effects.** The owner decides whether that satisfies "byte-for-byte" for the structure manifest |
| 3 | Two verified copies, checksums match, encrypted, outside the repository | **Partly met.** Two encrypted copies verified and outside the repository and the iCloud-synced folders, **but both are on the same physical disk** (the machine has one volume, `Macintosh HD`), and the key file is on that disk in a separate 0600 directory. Separate storage is **not** achieved: the owner must move a copy and the key off this device |
| 4 | Tests can no longer write to the development database | **NOT MET.** See below |
| 5 | Report reviewed by the independent human reviewer and accepted by the owner | **Pending:** the reviewer is unnamed (DR-7a) |
| 6 | No development data changed during D0 | **Met** |

**Test isolation (criterion 4), exact finding.** The three engine integration test modules run only when `SCHEMA_DIFF_DATABASE_URL` is set (otherwise they skip, confirmed by a harmless run with no network); nothing in the compose files, Makefile, `.env.example` or scripts sets it; the engine container's environment had only the development `DATABASE_URL`; CI uses an ephemeral `priceaction_test`; `make test-backend` uses the separate `priceaction_test` database (it exists). But **nothing checks which database a supplied URL names** (a second run showed the tests simply attempt the connection), the engine role has write privileges on development tables, and the lifetime counters show tests have written to the development database. A direct `phpunit` run in the backend container bypasses the Makefile override. **No guard exists, and none was implemented because it needs a code or configuration change outside the authorised D0 scope.** Options for the owner (each needs its own approval): (a) a guard in the test code that refuses to run unless the database name is a designated test database; (b) a dedicated test role with no privileges on the development database, with configuration that forces its use; (c) both. Until one is approved D0 cannot be called complete.

**Operational state left behind.** `backend`, `backend-queue`, `backend-scheduler` and `engine` are **stopped** (following §2.3 step 6: restart only after the owner accepts the restore report); `backend-nginx` reports unhealthy because its upstream is stopped; PostgreSQL, Redis and the frontends are running. To restart: `docker compose up -d backend backend-queue backend-scheduler engine` (add `-f docker-compose.dev.yml` as in your usual workflow). Restarting before acceptance would let the application write to the development database again; the baseline would then be a point-in-time record, which is its purpose, but the owner should say so first.

**Secrets handling.** The key file (`~/priceaction-backups/keys/d0-20261123.key`, 0600) and the encrypted globals file are secrets: not printed, not committed, not in the repository. The owner should store the key in a password manager and keep it off this disk.

### 2.6 D0 remaining acceptance gates (2026-11-23, after the owner declined acceptance)

The completed evidence of §2.5 is preserved unchanged. Authorised work done here: a fail-closed test-code guard and a dedicated test database role, with their evidence. Evidence files 11 to 14 are in the scratchpad `d0/evidence/` and were copied, with the helper scripts, into `~/priceaction-backups/d0-20261123/evidence/` under a separate `SHA256SUMS.remaining-gates`; the original `SHA256SUMS` for files 00 to 10 is untouched.

**What was implemented (and only this)**
- **Test-code guard** (`python-engine/tests/integration/db_guard.py`, new; the three integration modules now use it; `python-engine/tests/test_db_guard.py`, new, 36 tests). The URL in `SCHEMA_DIFF_DATABASE_URL` is checked **before any connection**. Approved: database name `priceaction_test` optionally followed by `_` and lowercase letters or digits; a named role that is not `postgres`, `app_engine` or `app_backend`; no `dbname`, `service` or `options` URL parameters; PostgreSQL only. Anything else raises `DatabaseGuardError`, so the module fails at import and no test in it runs. A missing URL **skips** the database tests without connecting (so everyday `make test-engine` still passes); with `REQUIRE_SCHEMA_DIFF=1` (CI) a missing URL is an error. Before the first write each fixture also asserts the live `current_database()` and `current_user`. Error messages carry only database and role names, never the URL or password. (Interpretation note: "fail closed when the URL is missing" is implemented as "no connection and an explicit skip", and as an error under `REQUIRE_SCHEMA_DIFF=1`; the owner may prefer a hard failure everywhere.)
- **Dedicated role** `app_test`: `LOGIN`, not superuser, no create-database, no create-role, no inherit, no replication, connection limit 8, no memberships. Created at **cluster level** (a role is not part of any database; no development table or row was touched). Password: random, stored only as `DB_TEST_PASSWORD` in the gitignored `.env` (mode 0600), never printed. In `priceaction_test` only: `CONNECT`, schema `USAGE`, and `SELECT/INSERT/UPDATE/DELETE` on all 53 tables plus sequence use, with default privileges so tables created later by `app_migrator` inherit them; no `CREATE`, `TRUNCATE` or `TRIGGER`. In the development database `priceaction`: **nothing was granted**; its ACL (`CONNECT` for `postgres`, `app_migrator`, `app_backend`, `app_engine` only) already excludes everyone else, and was not changed.

**Evidence A: guard behaviour** (file 11; throwaway container, no network, code read-only). Guard unit tests: pass. No URL: integration tests skip with no connection. `REQUIRE_SCHEMA_DIFF=1` and no URL: collection error (`DatabaseGuardError`). URL naming the development database `priceaction`: collection error, refused before any connection. URL naming `priceaction_test` with the live role `app_engine`: refused. URL with a `dbname` override in the query string: refused.

**Evidence B: role privileges and rejected development access** (file 12). Catalog check: `app_test` has no `CONNECT`, `TEMP` or `CREATE` on `priceaction` and no privilege on any of its 53 tables or on any sequence. **Real connection attempt** from a separate client container with the role's password: `FATAL: permission denied for database "priceaction", User does not have CONNECT privilege`. The same role connects to `priceaction_test`; there a zero-row insert succeeds, while `CREATE TABLE` (`permission denied for schema public`), `CREATE ROLE` and `CREATE DATABASE` are denied.

**Evidence C: tests executed against the dedicated test database** (file 13). With `SCHEMA_DIFF_DATABASE_URL` naming `priceaction_test` as `app_test` and `REQUIRE_SCHEMA_DIFF=1`: **52 passed**: 16 integration tests, of which 12 insert and delete rows (4 in `test_ingestion_repository`, 8 in `test_ingestion_wiring`) and 4 only read the schema (`test_schema_diff`), plus the 36 guard tests; none skipped. The test database's write counters rose while the development counters did not move, and the fixtures left the test database clean. Full engine suite with no URL: 532 passed, 5 skipped, 0 failed. `ruff check` passes on all engine tests.

**Evidence of no change to development.** After role creation, the guard work and the test runs, the development **data manifest is byte-identical** to the pre-D0 baseline; the structure manifest differs by exactly one line, the new cluster role `app_test` (file 14). The baseline `globals.sql` was taken before the role existed; restoring it into a fresh instance would not recreate `app_test`, which is recreated by the statements above.

**Evidence D: off-device backup.** **Not done; owner action pending.** The machine has one volume (`Macintosh HD`) and no other volume is mounted. Both encrypted copies and the key file are still on this device. When the owner has moved one encrypted copy to separate storage and stored the key in a password manager, `d0/verify_offdevice.sh <directory> [key file]` (read-only; the key is never printed) checks the ciphertext hashes against the recorded values and, if a key file is given, that each file decrypts to the recorded plaintext hash. It has been self-tested against the on-device copy B (ciphertext hash match, no key used). The owner should remove the key file from this disk after storing it.

**Residual risks (recorded, not fixed)**
- The guard covers the **engine integration tests only**. The Laravel suite is protected by the Makefile override to `priceaction_test` and by `app_backend` having no DDL rights, but a direct `phpunit` run in the backend container still targets the development database and is not guarded.
- `make test-engine` and `docker-compose` do not set the URL, so the integration tests still skip by default; to run them, supply `SCHEMA_DIFF_DATABASE_URL` for `app_test` and `priceaction_test` (as the evidence runner did). Wiring this into the Makefile, `.env.example` and `scripts/setup-env.sh`, and a matching guard for Laravel, are possible follow-ups needing separate approval.
- A person holding the `app_engine` or `postgres` credentials can still write to development by other means; the guard governs the tests, the role governs the test credentials.

**D0 acceptance matrix (updated 2026-11-23; D0 is NOT accepted)**

| # | Criterion | Status | Basis |
|---|---|---|---|
| 1 | Baseline manifest complete | **Completed** | §2.5 |
| 2 | Restore equals baseline | **Completed** (data and schema identical; structure identical after two documented representation effects) | §2.5 |
| 3 | Two verified encrypted copies, outside the repository, on **separate storage** | **Pending (owner)** | Copies verified; both on one device; key on the device; off-device copy and password-manager key not yet done (evidence D) |
| 4 | Tests cannot write to the development database | **Completed for the engine integration tests**, with the residual for Laravel above | Evidence A, B, C |
| 4a | Dedicated test role cannot connect to or write to development | **Completed** | Evidence B |
| 4b | Tests run against the dedicated test database | **Completed** | Evidence C |
| 5 | Independent human review of the D0 report, owner acceptance | **Pending** | Reviewer unnamed (DR-7a); owner has not accepted |
| 6 | No development data changed | **Completed** | Manifest byte-identical after all D0 work |
| 7 | Application services restarted only after acceptance | **Not done by design** | Still stopped |

Nothing in this section claims D0 acceptance.

### 2.7 D0 remaining gates, part 2: Laravel/PHPUnit isolation and secure provisioning (2026-11-23)

The owner accepted the engine integration-test isolation (§2.6) on the reported evidence and authorised the same fail-closed isolation for Laravel/PHPUnit. All earlier D0 evidence (files 00 to 14) is preserved unchanged. New evidence is files 15 to 20.

**What was implemented (and only this)**
- **PHPUnit guard** with three checks, each before anything is written:
  1. `backend/tests/bootstrap.php` (new; `phpunit.xml` now names it as the bootstrap) checks the **process environment before the application boots**: `DB_CONNECTION=pgsql`, `DB_URL` empty, `DB_DATABASE` matching `priceaction_test` optionally followed by `_` and lowercase letters or digits, `DB_USERNAME` named and not `postgres`, `app_backend`, `app_engine` or `app_migrator`. An unset value is a refusal. On failure it prints which rule failed (database and role names only, never a password) and **exits with status 2: no test runs**.
  2. `Tests\TestCase::createApplication` checks the **resolved default connection configuration** before any connection.
  3. `Tests\TestCase::setUpTraits` checks the **live connection** (`select current_database(), current_user`) before any test trait runs, so before `RefreshDatabase` migrates, seeds, cleans up or writes. (An override of `beforeRefreshingDatabase` on the base class would be shadowed by the trait's own empty method, so the hook is `setUpTraits`.)
  4. `backend/tests/Support/DatabaseGuard.php`, `DatabaseGuardException.php` and `backend/tests/Unit/DatabaseGuardTest.php` (21 tests, 36 assertions) implement and test it.
- **Dedicated Laravel test role** `app_test_schema`: `LOGIN`, not superuser, no create-database, no create-role, no inherit, no replication, connection limit 8, no memberships. It **owns `priceaction_test`** (database, 53 tables, 4 sequences, 4 application functions) because `migrate:fresh` must drop and recreate tables; it holds **no privilege at all on the development database `priceaction`**. The engine role `app_test` keeps its DML-only access (default privileges give it access to tables that Laravel recreates). `app_migrator` is no longer used for tests and is refused by the guard.
- **Makefile** `test-backend` now runs `scripts/provision-test-db.sh` and then phpunit as `app_test_schema` with `DB_TEST_SCHEMA_PASSWORD` from `.env`.
- **`scripts/provision-test-db.sh`** (new): idempotent provisioning, described below.

**Evidence E: provisioning** (file 15). The script ran twice. Run 1 generated the missing secret in `.env` (value not shown), kept the existing `app_test`, created `app_test_schema`, transferred ownership inside the test database and set default privileges; run 2 changed nothing ("exists (password unchanged)").

**Evidence F: role privileges and rejected development access** (file 16). Catalog: `app_test_schema` has no `CONNECT`, `TEMP` or `CREATE` on `priceaction` and no privilege on any of its 53 tables. **Real connection attempt** to `priceaction` with the role's password: `FATAL: permission denied for database "priceaction", User does not have CONNECT privilege`. In `priceaction_test` it connects, creates and drops a table (rolled back), but cannot create roles or databases. Observation: like any role, it can connect to the maintenance database `postgres` (default public `CONNECT`) with no privileges there; that database is not the development database.

**Evidence G: guard behaviour** (file 17; throwaway container, **no network**, code read-only, so a failed guard could not have reached a database). Guard unit tests: OK. The backend container's own default environment (`DB_DATABASE=priceaction` as `app_backend`): refused, **exit 2, no test executed**. Also refused with exit 2 and no PHPUnit banner: `DB_DATABASE` unset; the development database with the dedicated role; the test database with `app_migrator`, `app_engine` or `postgres`; `DB_URL` set; the sqlite driver; `DB_USERNAME` unset.

**Evidence H: successful execution against the dedicated test database** (file 18). `make test-backend`: **217 tests, 2,972 assertions, OK**, exit 0, run twice (before and after a Pint style fix, so the evidence matches the final code). The development write counters did not move; the test database's counters were reset by `migrate:fresh`, which is expected.

**Evidence I: cross-checks** (file 19). The engine integration suite still passes as `app_test` after Laravel recreated the tables (52 passed); `app_test_schema` owns all 53 tables and `app_test` has DML on all 53; **the development data manifest is byte-identical to the pre-D0 baseline after every D0 step including both test suites**; the structure manifest differs only by the two new cluster roles `app_test` and `app_test_schema`; Pint passes on the touched files.

**Evidence J: CI** (file 20). The CI environments (backend: `priceaction_test` as `ci`; engine: `priceaction_test` as `ci` with `REQUIRE_SCHEMA_DIFF=1`) pass the guards. CI itself was not executed.

**Secure provisioning of the test roles, separate from the historical `globals.sql` baseline**
- *Why separate.* The D0 baseline (`globals.sql`, taken before the roles existed) is a historical record of the cluster at that moment and must stay immutable. The test roles are operational, disposable and have their own secrets, so they are provisioned by `scripts/provision-test-db.sh`, not by editing or re-taking the baseline. Restoring the baseline into a fresh instance does not recreate them; run the script afterwards.
- *Procedure.* (1) `.env` must exist (mode 0600, gitignored). (2) Run `./scripts/provision-test-db.sh` (also run by `make test-backend`). (3) For each missing secret (`DB_TEST_PASSWORD`, `DB_TEST_SCHEMA_PASSWORD`) it generates a 48-hex-character value with `openssl rand`, appends it to `.env` and prints only the variable name. (4) It creates a missing role with the password sent on **stdin** to `psql`, never on a command line, never echoed; an existing role's password is **never changed** (to rotate a password, change it deliberately with `ALTER ROLE` and update `.env`, outside the script). (5) Roles are created with no superuser, create-database, create-role, inherit or replication attributes. (6) It touches only cluster roles and the one database named by `TEST_DB`, which must match the approved name pattern; it never connects to, grants on or alters the development database. (7) It is safe to run repeatedly.
- *Secret handling.* Passwords live only in `.env`; they are not in repository files, logs, evidence files or chat. Evidence runners read them at run time into temporary 0600 files that are deleted on exit. A password manager should hold copies if the owner wants recovery; `.env` can be regenerated by running the script on a fresh machine (new roles get new passwords).
- *Verification after provisioning.* The catalog queries and the real rejected-connection attempt of evidence F; the guard runs of evidence G.
- *Not done (needs separate approval):* adding the two variables to `.env.example` and `scripts/setup-env.sh`, so that a new clone creates them automatically; until then a new clone gets them from the provisioning script on its first `make test-backend`.

**Residual risks (recorded, not fixed)**
- Anyone holding the `app_engine`, `app_backend`, `app_migrator` or `postgres` credentials can still write to development by other means; the guards govern the test suites and the roles govern the test credentials.
- The development `backend` container's default environment still points at the development database, but a direct `phpunit` run there is now refused by the bootstrap (exit 2).
- The guards depend on the process environment and the framework configuration; a test that opens its own connection to another database by hand would not be covered (none exists).
- The test roles can connect to the maintenance database `postgres` (public default); this is outside the development database and was not changed.

**D0 acceptance matrix (updated 2026-11-23; D0 is NOT accepted)**

| # | Criterion | Status | Basis |
|---|---|---|---|
| 1 | Baseline manifest complete | **Completed** | §2.5 |
| 2 | Restore equals baseline | **Completed** (data and schema identical; structure identical after two documented representation effects) | §2.5 |
| 3 | Two verified encrypted copies on **separate storage**; key in a password manager | **Pending (owner action)** | Copies verified; both and the key file still on this device; nothing moved (no other volume mounted when last checked) |
| 4 | Tests cannot write to the development database | **Completed for the engine integration tests (accepted by the owner) and for Laravel/PHPUnit** | Evidence A-C; E-J |
| 4a | Dedicated test roles cannot connect to or write to development | **Completed** (`app_test`, `app_test_schema`) | Evidence B, F |
| 4b | Tests run against the dedicated test database | **Completed** (engine 52 passed; Laravel 217 passed) | Evidence C, H, I |
| 4c | Test-role provisioning documented separately from the historical baseline | **Completed** | §2.7 |
| 5 | Independent human review of the D0 report; owner acceptance | **Pending** | Reviewer unnamed (DR-7a); owner has not accepted |
| 6 | No development data changed | **Completed** | Manifest byte-identical after all D0 work |
| 7 | Application services restarted only after acceptance | **Not done by design** | Still stopped |

Nothing in this section claims D0 acceptance.

**Acceptance package (2026-11-23).** The matrix above is restated, with each row classed as verified by automated checks, owner action, independent review or formal acceptance, in [orb-d0-review-package.md](orb-d0-review-package.md#1-acceptance-matrix), together with the owner's exact off-device and key instructions ([§2](orb-d0-review-package.md#2-owner-instructions-password-manager-key-and-local-key-removal-exact-steps)), the independent reviewer checklist ([§3](orb-d0-review-package.md#3-independent-reviewer-checklist-dr-7a-open)) and the remaining blockers ([§5](orb-d0-review-package.md#5-remaining-items-after-d0-acceptance)). Status on 2026-11-23: both encrypted copies re-checked (ciphertext hashes match); **no off-device copy exists and the key is not in a password manager (owner actions, not done)**; the independent reviewer is **not named (DR-7a open)**; the development manifest, the evidence sums and the secret scan were re-verified; D0 is **not accepted**.

### 2.8 Backup exception record (owner-approved, 2026-11-23)

**Owner decision ([DEC-032](../../DECISIONS.md), DR-9).** The owner explicitly waives the requirement for an off-device backup for D0. The two encrypted copies may remain on this Mac provided that: they stay in separate directories; both pass their recorded SHA-256 ciphertext verification; the restore evidence stays preserved; the decryption key is stored securely in the owner's password manager; and the local plaintext key file is removed only after password-manager recovery is verified.

**Residual risk, accepted by the owner:** A physical failure, theft, loss or destruction of this Mac could destroy both backup copies. This is a **documented risk exception, not equivalent to an off-device backup**. The off-device requirement is recorded as **WAIVED BY OWNER, not completed**. The same event could also destroy the Desktop duplicate (below) and, until it is in the password manager, the key.

**Same-device copies, verified 2026-11-23 (evidence file 21, sum file `SHA256SUMS.backup-exception`; no key was used)**

| Copy | Location | Ciphertext SHA-256 vs recorded | Directory |
|---|---|---|---|
| A | `~/priceaction-backups/d0-20261123/copy-a/` | Match (copy A) | Separate |
| B | `~/priceaction-backups/d0-20261123/copy-b/` | Match (copy B) | Separate |
| B duplicate (the owner's "Desktop copy") | `~/Desktop/D0-Backup-Copy/copy-b/` | Match (copy B); **byte-for-byte identical** to the original copy B (`cmp` on both files) | Separate; files mode 0600 |

All three are on the same physical device (`/dev/disk3s5`), so none is off-device. The original copies, the restore evidence (files 06 to 10) and the other evidence files are unchanged; the three evidence sum files still verify (0 failures). The local key file still exists and was not read, printed or deleted.

**iCloud observation (unverified, not relied on).** The Finder "Desktop & Documents" iCloud setting is on, so the Desktop duplicate may be uploaded to iCloud as ciphertext. I did not verify upload state, and an iCloud copy would be encrypted with the same key that is still pending in the password manager. It is **not** treated as an off-device backup and does not change the waiver. The original copies in `~/priceaction-backups/` are outside the synced folders.

**What is NOT claimed.** No off-device copy exists. The key is not confirmed to be in the password manager and its recovery is not verified. The local key file has not been removed. D0 is not accepted.

**D0 acceptance matrix (recalculated 2026-11-23; D0 is NOT accepted)**

| # | Criterion | Status | Class |
|---|---|---|---|
| 1 | Baseline manifest complete | **Verified** | Automated checks |
| 2 | Restore equals baseline | **Verified** (documented representation effects) | Automated checks |
| 3a | Two encrypted copies exist, in separate directories, outside the repository, with matching recorded SHA-256 ciphertext hashes | **Verified** (copy A, copy B, and the Desktop duplicate of B) | Automated checks |
| 3b | Copy on separate storage (off-device) | **WAIVED BY OWNER** (risk exception DR-9; not completed; not equivalent) | Owner decision |
| 3c | Decryption key in the owner's password manager, recovery verified | **PENDING (owner action)** | Owner action |
| 3d | Local plaintext key file removed after 3c is verified | **PENDING (owner action)**; the file still exists | Owner action |
| 3e | Residual risk accepted in writing | **Done** (DEC-032, this section) | Owner decision |
| 4 | Engine integration tests cannot write to the development database | **Verified** (accepted by the owner) | Automated checks; owner accepted |
| 5 | Laravel/PHPUnit tests cannot write to the development database | **Verified** | Automated checks |
| 6 | No development data changed (manifest byte-identical, re-checked) | **Verified** | Automated checks |
| 7 | Secret scan clean | **Verified** | Automated checks |
| 8 | Evidence sums verify | **Verified** | Automated checks |
| 9 | B0, `ORB-MG-02`, PAQS, rulesets, strategies and P0-1 artifacts unchanged | **Verified** | Automated checks |
| 10 | Test-role provisioning documented separately | **Verified** | Automated checks |
| 11 | Independent human review | **AWAITING a reviewer** (DR-7a OPEN, unnamed) | Independent review |
| 12 | Services restarted only after acceptance | **Not done, by design** | Owner acceptance |
| 13 | Formal owner acceptance of D0 | **AWAITING** | Owner acceptance |

Full detail and the reviewer checklist: [orb-d0-review-package.md](orb-d0-review-package.md#1-acceptance-matrix).

### 2.9 D0 review waiver approved: owner self-review, NON-INDEPENDENT (approved 2026-11-25)

**Status: APPROVED by the owner, for the D0 review only ([DEC-033](../../DECISIONS.md), DR-10). The self-review was executed by the owner on 2026-11-24/25 and recorded in [package §3.4](orb-d0-review-package.md#34-owner-self-review-record-recorded-2026-11-25) (R1-R14 recorded; R13 approved and R14 confirmed on 2026-11-25). D0 is NOT accepted.**

**Decision.**
1. The independent-human-review requirement of DR-7a is waived **for the D0 review**.
2. The owner performs checklist R1 to R14 ([package §3](orb-d0-review-package.md#3-independent-reviewer-checklist-dr-7a-open)) **personally**, as an owner self-review, and records Pass, Fail or Query for each item.
3. The review is **explicitly labelled NON-INDEPENDENT** in the register, the package, the matrix and any acceptance record. It is never described as an independent review.
4. **Residual risk (recorded and accepted by the owner):** A separate human reviewer did not verify the D0 preparation, the evidence, or the owner's own decisions. The person performing the review commissioned the work, set its scope and approved its design, so errors or blind spots shared by the preparer and the owner would not be caught by a second person.
5. The original D0 evidence (files 00 to 21) and [DEC-032](../../DECISIONS.md) (the off-device waiver and its residual risk) are preserved unchanged.
6. **DR-7 remains applicable to D1-D6** unless the owner separately changes it: curated reference data still needs a preparer and a separate independent human reviewer. Errors in curated data matter more than errors in D0, so this should be revisited before D2 and D3 if the owner wants a different rule.
7. D0 acceptance is a separate, later, explicit owner decision.

**Conditions.**
- *Owner-executed evidence only counts when the owner ran it.* The review tooling records who ran it (`RUN_BY=owner` or `RUN_BY=ai-assisted`); AI-run results are labelled, kept as AI-generated evidence, and do not make any item PASS in the owner's review. Items R5, R13 and R14 are manual attestations by nature.
- *Key handling (R5)* is self-attested.
- *Record.* The completed review is recorded with the template of [package §3.2](orb-d0-review-package.md#32-self-review-record-template), dated, and kept with the evidence. The owner's execution sheet is [package §3.3](orb-d0-review-package.md#33-owner-self-review-execution-sheet-r1-r14).
- *Optional compensating controls (not conditions).* Let a day pass between completing the review and accepting D0; ask any trusted person to read the record.

**What this does not change.** No development data, B0, `ORB-MG-02`, PAQS, ruleset or strategy; the D0 safeguards; the same-device backup exception; the stopped services; the rule that D1-D6 do not start before D0 is accepted.

**Matrix effect.** Row 11 reads **WAIVED BY OWNER (independence), replaced by a NON-INDEPENDENT owner self-review, which is PENDING** until the owner executes and records R1 to R14. Independent review is not met; it is waived, with the risk accepted in writing.

**Final acceptance gate:** [package §6](orb-d0-review-package.md#6-final-d0-acceptance-gate) (D0 was recommended for acceptance with caveats and **accepted with caveats by the owner on 2026-11-25**, DEC-035).

### 2.10 R13: proposed minimum-sufficient remediation (APPROVED, approach only)

**Status: APPROVED by the owner on 2026-11-25 ([DEC-034](../../DECISIONS.md)) as the remediation approach only. It does NOT authorise executing D1-D6 and does not change any D1-D6 definition (§5). D1-D6 start only after D0 is formally accepted and the owner separately authorises each.** It restates the existing D1-D6 scope and DR-3a/DR-5/DR-8 decisions in minimum-sufficient form; where it differs from §5 in wording, §5 governs. Principles preserved: D1-D5 complete before D6; D6 needs a frozen dataset and the required independent human review (DR-7 applies); unresolved material corporate actions exclude the affected instrument-sessions from Stage A; unknown or unverifiable tick sizes are not failures.

**Limitations the owner understands (package §4).** Historical tick-size coverage is incomplete. Corporate-action records are absent. Historical market-calendar coverage is incomplete. Instrument provenance and `is_demo` labels are inconsistent. Five sessions miss the opening bar and need a disposition. Survivorship bias remains. Transaction costs and slippage are unverified. Minute-level history is unavailable. Test-activity churn in the development data is inferred, not proven.

| Step | Minimum-sufficient approach |
|---|---|
| D1 Instrument identity and provenance | Establish source, instrument identity, environment and provenance. **No bulk `is_demo` update**; change an individual record only with evidence |
| D2 Corporate actions | Cover material price-affecting events from authoritative sources. Exclude affected instrument-sessions from Stage A while material events stay unreconciled (DR-3, DR-3a) |
| D3 Historical tick sizes | Prefer official historical exchange circulars. Unknown and unverifiable ticks are **not** failed validation. Formal MG02-A1 adoption stays a separate owner decision |
| D4 Market calendar | Reconstruct authoritative trading dates and session timings, including special sessions and holidays. Do not assume every weekday traded |
| D5 Opening-range integrity | Resolve the five missing-bar sessions individually. Keep the four known provider-rejection explanations and the unresolved ITC (2025-01-06) case as recorded. Use the already-approved read-only re-fetch (DR-5). Preserve raw provider responses. Never overwrite existing candles |
| D6 Post-remediation P0-1 | Only after D1-D5. Freeze the data first. Obtain the required independent review (DR-7 still applies). Use the approved counts-only contract and the four tick statuses. Produce new hashes and evidence |

**Limitations that remain (D1-D6 are not claimed to resolve them):** survivorship bias; unverified costs and slippage; no minute-level history; the inferred (unproven) test-activity churn.

**Owner decision (2026-11-25).** Approved as the R13 assessment. R13 is recorded APPROVED in the [review record](orb-d0-review-package.md#34-owner-self-review-record-recorded-2026-11-25). The remaining limitations are documented limits, not resolved by D1-D6.

### 2.11 DR-12: DR-7a solo-research exception (owner-approved 2026-11-25)

**Status: APPROVED by the owner on 2026-11-25 ([DEC-045](../../DECISIONS.md)). DR-7a is recorded as an owner-approved solo-research exception. It is NOT an independent-review completion and no independent reviewer exists.**

**Decision.** The project is owner-operated and currently has no independent human reviewer. For the defined scope below, the owner accepts responsibility for research approvals and decisions without one, and the project may proceed through the agreed research stages under these controls:
1. Owner approval is explicit and recorded (a dated decision or record; silence or momentum is not approval).
2. Automated tests and deterministic validation remain mandatory.
3. Independent test oracles are used where applicable; an oracle must not simply reproduce the implementation under test.
4. Reproducibility, data provenance, reference-data SHA-256 hashes and run evidence are retained.
5. Every AI-assisted review is labelled `AI-ASSISTED — NON-INDEPENDENT`; AI is never represented as an independent human reviewer.
6. Every research result is labelled `EXPLORATORY — SOLO RESEARCH — NOT INDEPENDENTLY VALIDATED`.
7. No claim of independently validated profitability or strategy performance is made.

**Scope.** Local, exploratory, non-commercial research under the agreed solo-research workflow (development and reserve data, the staged ORB plan).

**Limitations (explicit).** The exception does not: convert AI-assisted review into independent review; certify the strategy or its profitability; waive technical validation or data-integrity requirements; approve commercial use, live trading or deployment; approve frozen-specification amendments; approve any specific backtest execution. DR-7 is unchanged as a requirement; DR-10 (D0 only) and DR-11 (D1 only) are unchanged and are not broadened by this decision.

**What stays open (each needs its own evidence and owner approval; none is completed by this exception):** (1) reviewed, provenance-backed, SHA-256-pinned tick reference data; (2) the same for session reference data; (3) the same for corporate-action and event reference data; (4) any required frozen-specification amendment (MG02-A1, session facts, 0.6.0 metadata) and its approval; (5) OD-15 and OD-16; (6) the final B0 pre-registration with its thresholds and validation criteria; (7) the remaining technical and sample-size readiness checks; (8) a separate explicit owner authorisation to execute the original B0 backtest.

**Technical consequences.** (a) **Implemented (2026-11-25, T-I178; synthetic tests only).** A table approved under this exception must never carry `INDEPENDENTLY_REVIEWED`, because that would misstate what happened. The loader therefore has two distinct statuses, never converted into one another: `INDEPENDENTLY_REVIEWED` (an actual, evidenced independent human review; unchanged meaning and path) and `OWNER_APPROVED_SOLO_RESEARCH` (owner approval under DEC-045 / DR-12; independent review has not occurred). A solo table is accepted only if the caller opts in explicitly (`allow_solo_research`, CLI `--solo-research-exception`), the table metadata has `decision_ref` equal to `DEC-045` or `DR-12`, and `owner_approval` carries `approved_by` = `owner`, an ISO `approved_on` and a `record`; metadata claiming an independent review is refused, and so are missing, unknown, AI-assisted or malformed statuses. The status is a governance basis, not a data-quality certification: SHA-256 pins, schema, non-empty row provenance, date coverage and conflict checks apply unchanged. Every run record and evidence record carries the approval basis, the decision references, each table's own status and hashes, and, for a solo basis, the exact label `EXPLORATORY — SOLO RESEARCH — NOT INDEPENDENTLY VALIDATED` (it cannot be omitted or replaced: a record with a missing, altered or contradictory label cannot be constructed). If tables differ, the weakest basis governs the run (one solo table makes the run solo-labelled) and no table's status is upgraded or downgraded. See [the readiness report](orb-b0-phase1-backtest-readiness.md#11-reference-table-approval-statuses-and-the-result-label-dec-045). (b) The methodology is unchanged: original B0 first, the fill-based variant deferred, frozen B0 rules unchanged, no criterion lowered after results, an insufficient sample reported as `INCONCLUSIVE / INSUFFICIENT_SAMPLE`, no optimisation to manufacture a positive result. (c) "Independent" in [independent-backtesting-standards](../research/independent-backtesting-standards.md) means isolated strategy runs, not a second person, and is unchanged.

## 3. Proposed reference-data ownership matrix (for owner review)

Runtime writers follow the single-writer rule (ARC-01 §6, ARC-03 §2). "Preparer" curates from the authority and produces the file; the **independent human reviewer** (DR-7) is a different person who checks the preparer's output against the source before load. Names are not assigned (DR-7a).

| Dataset | Authority (source of truth) | Preparer | Independent reviewer | Runtime writer | Provenance recorded | Change control |
|---|---|---|---|---|---|---|
| Historical tick-size rules (price bands, dates, reference price) | NSE circulars (DR-1); security master files if licensed | Engineer (AI-assisted allowed) | Human, not the preparer | Engine (`instrument_snapshots` family) via a reviewed loader | circular id, URL, retrieved date, document sha256 | Reviewed pull request; new effective-dated rows only, no overwrite |
| Instrument identity and symbol history (ISIN, listing, renames) | NSE security master and symbol-change circulars | Engineer | Human reviewer | Engine | Same | Same |
| Corporate actions (material events) | NSE corporate-action announcements and circulars; paid NSE data if approved | Engineer | Human reviewer | Engine (`corporate_actions`) | Same, plus the reconciliation report hash | Same; reconciliation gate (D2) |
| Exchange calendar (holidays, special and Muhurat sessions, segments) | NSE holiday, special-session and timing circulars | Engineer | Human reviewer | Laravel (`market_calendar`, ARC-03 §6.9; a schema change is a Laravel migration) | Same | Same; `verified` only with a reference per row |
| Raw provider-response archive | The provider's response itself | Engine job (automatic) | Human spot-check of hashes | Engine, append-only | Response hash, request parameters, fetch time | Immutable; no edit path |
| Data-source and demo separation metadata | The data source of each candle and ingestion run | Engineer | Human reviewer | Laravel for `data_sources`; engine for instruments | Per-instrument evidence for any flag change | Owner-approved write with an audit record |
| Reconciliation reports (D2, D4, D5) | Computed from the above | Tool output | Human reviewer signs the dispositions | Written once to the repository or archive with a hash | Report sha256, input hashes | Immutable; a corrected run is a new report |
| D0 baseline and restore report | The database | Engineer | Human reviewer | None (files) | Hashes, manifest | Immutable |

## 4. Formal `ORB-MG-02` amendment proposal (approved in principle; formal adoption pending)

**Proposal id:** MG02-A1. **Status:** the substantive policy was formally approved by the owner on 2026-11-23 (earlier recorded as approved in principle; direction: basic OHLC hard; tick check only when the tick is known and the basis unadjusted; four statuses; only `TICK_VERIFIED_FAIL` fails). The exact wording and vectors were verified against the policy in §4.10; **adoption into the specification under CLAUDE.md §8 is still pending and nothing is implemented.** **Frozen text is unchanged** and remains the text of the approved B0 until that adoption.

### 4.1 Current frozen text (specification §7.1.2)
`ORB-MG-02`: exactly `K` complete 5m candles on the expected grid, none missing or duplicated, every candle closed and valid. The *Valid OHLC* check includes: "each price is a multiple of the tick when the tick is known". A failure is `OR_INVALID_OHLC`.

### 4.2 Problem
The tick clause was evaluated against reference data that is a placeholder or absent, and against provider-adjusted prices. In the P0-1 scan it produced 860 of 865 invalid ranges (99.4%), all tick misalignment and no basic OHLC defect (see [limitation summary](../research/research-data-limitations.md) and the P0-1 review). The failures say nothing reliable about bar validity, and sessions with an unknown tick were silently unchecked.

### 4.3 Proposed rule
Split the *Valid OHLC* check into two parts.

1. **Basic OHLC validity (unchanged, hard):** prices finite and positive; `H ≥ max(O, C)`, `L ≤ min(O, C)`, `H ≥ L`. Failure: `OR_INVALID_OHLC`.
2. **Tick-grid check (conditional):** evaluated **only if both** hold for the instrument-session:
   - (T1) **the effective tick size for that date is known**, which requires **all four** of: a *verifiable instrument identity* (stable identity key and symbol history, D1); an *effective period* that covers the date; *source provenance* (a document reference and hash for an official exchange rule or notice, per DR-1); and an *applicable price basis* (D2). A provider-dump observation alone, a demo placeholder, a provider default (for example the `0.05` the Kite adapter substitutes when the field is empty) or a value inferred from a later or current observation is **never** sufficient unless its historical semantics are documented and approved; and
   - (T2) **the stored price basis is unadjusted** for that date, as established by the corporate-action reconciliation (D2) (the session lies outside every provider adjustment window). **No exception for adjusted prices is approved** (owner, 2026-11-23).

   If (T1) and (T2) hold and any of the four prices of any range bar is not a multiple of the tick, the range fails with sub-reason `TICK_MISALIGNED` (a member of `OR_INVALID_OHLC`). Otherwise the check **does not fail the range**; it returns a status.

### 4.4 Status vocabulary

| Status | Meaning | Effect on range validity |
|---|---|---|
| `TICK_VERIFIED_PASS` | (T1) and (T2) hold, all prices on the grid | none |
| `TICK_VERIFIED_FAIL` | (T1) and (T2) hold, a price is off the grid | **Invalid** (`OR_INVALID_OHLC`, `TICK_MISALIGNED`) |
| `TICK_UNKNOWN` | (T1) fails: the historical effective tick is not established | none |
| `TICK_UNVERIFIABLE` | The tick is known but (T2) fails: the price basis is adjusted or undetermined (no reconciliation). There is no exception | none |

Default when the basis is undetermined: `TICK_UNVERIFIABLE` (conservative: never a failure). A default value such as 0.05 is never substituted for an unknown tick.

### 4.5 Reporting
Every run and every integrity scan reports the four status counts, by class and month, beside the range-validity counts. A range is "valid" with respect to the tick clause unless the status is `TICK_VERIFIED_FAIL`. The counts-only contract of the post-remediation scan (DR-8) is extended with these four counts (no price content), which needs the owner's approval of that contract.

### 4.6 Impact
- **P0-1 counts:** the 860 failures would be re-labelled `TICK_UNKNOWN` or `TICK_UNVERIFIABLE` where they rest on placeholder ticks or adjusted prices; the exact new numbers are known only after D1-D3 and the post-remediation scan. No reclassification is done now.
- **B0:** the definition changes only in the validity of a range under the tick clause; B0's range, breakout, stop, target and exits are unchanged. The Stage A candidate set may grow by the sessions currently failed on placeholder ticks.
- **Specification:** `ORB-MG-02` text and §7.1.2 change; the rule inventory, the counts contract (plan §3), the readiness page (E3) and `TRD-04 §3` (at implementation) need matching edits.
- **Implementation:** engineering item E3 would implement the amended rule; nothing is built.

### 4.7 Alternatives considered
(a) Keep the clause unchanged: rejected, because it fails sessions on invalid grounds. (b) Remove the tick check: simplest, loses a real defect detector where the tick is known and prices unadjusted. (c) Demote to an advisory flag: low cost, never invalidates. The proposal (conditional hard check) keeps the detector only where it is sound.

### 4.8 Adoption process (not started)
Owner decision recorded in `DECISIONS.md` and the decision register; specification version 1.1.0 of the ORB page with the amended `ORB-MG-02`; the freeze notice updated; the validation plan §3 contract updated; test vectors for each status (below) added at implementation. Until then B0 and `ORB-MG-02` stay as frozen.

### 4.9 Proposed test vectors (specified, not implemented)
1. Tick known (exchange basis), unadjusted, all prices on grid: `TICK_VERIFIED_PASS`.
2. Same with one price off grid: `TICK_VERIFIED_FAIL`, range invalid.
3. Tick from a demo placeholder: `TICK_UNKNOWN`.
4. Tick unknown (no row): `TICK_UNKNOWN`.
5. Tick known, session inside an adjustment window: `TICK_UNVERIFIABLE`.
6. Tick known, adjustment status undetermined: `TICK_UNVERIFIABLE`.
7. Basic OHLC defect with an unknown tick: `OR_INVALID_OHLC` (basic) regardless of tick status.
8. Boundary dates of a tick-rule change (day before, day of, day after).

### 4.10 Verification of the wording and test vectors against the approved policy (2026-11-23)

The owner's approved policy: **(P1)** basic OHLC validity stays hard; **(P2)** tick validation applies only when the historical effective tick is known and the price basis is unadjusted; **(P3)** four statuses, `TICK_VERIFIED_PASS`, `TICK_VERIFIED_FAIL`, `TICK_UNKNOWN`, `TICK_UNVERIFIABLE`; **(P4)** only `TICK_VERIFIED_FAIL` creates a tick-based hard failure. Checked against §4.3 to §4.9 (nothing changed in this page's proposal text):

| Policy clause | Where the proposal states it | Result |
|---|---|---|
| P1 | §4.3 part 1 (unchanged hard check); vector 7 | **Matches** |
| P2 | §4.3 part 2 (T1 known tick, T2 unadjusted basis); vectors 1, 2, 5, 6 | **Matches in substance; two wording points below** |
| P3 | §4.4 (the four names exactly); vectors 1 to 6 cover all four statuses | **Matches** |
| P4 | §4.4 effect column, §4.5 ("valid unless `TICK_VERIFIED_FAIL`") | **Matches** |
| Unknown tick never a failed OHLC, never defaulted | §4.4 and the default sentence under it; vectors 3, 4 | **Matches** |

**Wording points: resolved by the owner (2026-11-23), and §4.3 updated to match.**
1. *Adjusted-basis exception:* **not approved.** `TICK_VERIFIED_*` requires an unadjusted basis in every case; an adjusted or undetermined basis is `TICK_UNVERIFIABLE`.
2. *Meaning of "known":* a known historical tick requires verifiable instrument identity, an effective period covering the date, source provenance and an applicable price basis. A provider-dump observation alone is insufficient without documented historical semantics.

**Test-vector coverage against the policy.** Vectors 1 to 8 cover P1 to P4 once each. The seven proposed additions below **remain proposed, not approved** (owner, 2026-11-23); none is added to §4.9 and none is implemented:

| ID | Vector | Why |
|---|---|---|
| 9 | A range whose status is `TICK_UNKNOWN` (or `TICK_UNVERIFIABLE`) **with off-grid prices is valid** and counted in the status coverage | Asserts P4 directly; vectors 3 to 6 only imply it |
| 10 | A provider default tick (empty provider field), or a provider-dump observation without documented historical semantics, is `TICK_UNKNOWN`, not `TICK_VERIFIED_*` | The Kite adapter's silent `0.05` fallback; the owner's rule on provider dumps |
| 11 | Three range bars, one off the grid, tick known and unadjusted: `TICK_VERIFIED_FAIL` for the session; all on grid: `TICK_VERIFIED_PASS` | Defines the session-level status |
| 12 | Basic OHLC defect **and** `TICK_VERIFIED_FAIL` together: one invalid range, both reasons recorded, basic reason first | Precedence |
| 13 | Day before, day of and day after a corporate-action ex-date (adjustment-window boundary): `TICK_VERIFIED_*`, then `TICK_UNVERIFIABLE` inside the window | Boundary of the unadjusted condition |
| 14 | *Moot as drafted, because no adjusted-price exception is approved.* Proposed replacement for the owner's decision: an adjusted or undetermined price basis is always `TICK_UNVERIFIABLE`, with no override | Locks in the owner's decision that there is no exception |
| 15 | The four status counts are reported by class and month and sum to the number of evaluated sessions | §4.5 reporting |

**Conclusion.** The proposal's substance equals the approved policy, and §4.3 now carries the owner's decisions on the tick basis. Nothing in B0, the current `ORB-MG-02`, the specification page, the validation plan or any code was changed; adopting the amendment (specification 1.1.0, freeze notice, plan §3 contract, `TRD-04 §3` at implementation) and implementing it (engineering item E3) remain unstarted.

## 5. D1-D6: dependency and acceptance-criteria matrix

None is started. A preparer and an independent human reviewer (DR-7) apply to every curated dataset. **Sequence:** D0 → D1 → (D2 and D4 in parallel) → D3 (needs D1, D2) → D5 (needs D1, D4; D0 and the archive for the re-fetch) → D6 (needs D1-D5, a freeze and an independent review).

| ID | Scope | Depends on | Key deliverables | Acceptance criteria | Mandatory before Stage A |
|---|---|---|---|---|---|
| **D0** | Test database; baseline; verified restore (§2) | none | Manifest, dumps, restore report, test guard | §2.4 | **Yes** |
| **D1** | Identity, data source and demo environment separated (DR-4); symbol history and identity keys for the 50 instruments | D0 | Identity key (for example ISIN plus symbol history), recorded mode and source per instrument, `basis` and provenance columns on shared reference rows, a documented mapping; **no bulk `is_demo` change**; any per-instrument change has evidence and an audit record | For each of the 50: stable identity, symbol history, listing date, data source and mode recorded; no demo placeholder is readable as real data; the owner accepts the mapping; reviewer sign-off | **Yes**, as an accepted mapping (correcting flags is recommended, not mandatory) |
| **D2** | Corporate actions for material price-affecting events (DR-3) | D1 | Curated events with source references and hashes; adjustment-factor derivation from the provider's daily bars against an unadjusted official close series; two-way reconciliation; `adjustment_windows`; list of unreconciled events | Every curated material event has a source and hash; zero unexplained factor steps or unmatched events, **or** each remaining one is listed and **its affected instrument-sessions are excluded from Stage A (DR-3)**; report hash reproducible; reviewer sign-off; **DR-3a definitions approved** | **Yes** (reconciled, or the exclusion rule applied) |
| **D3** | Historical tick rules (price bands, effective dates, reference price) | D1, D2 | Effective-dated rule table with circular ids and hashes; a resolver returning `RESOLVED` or `UNKNOWN`; a test of the rule's predicted grid against observed grids with every disagreement listed; status vocabulary of §4.4 | Rule rows trace to circulars; unknown ticks never default; no unreviewed disagreement; the owner's decision on MG02-A1 recorded | **Decision: yes. Full remediation: only if the tick check stays hard** (it does under MG02-A1 where resolvable) |
| **D4** | Authoritative exchange calendar | D0 | Calendar rows with circular references; a segments table for multi-window sessions; classification of every date against the data (trading with data, trading without data, closed, closed with data); dispositions for the 39 weekdays and 6 weekend dates | Every date in scope referenced to a circular; no unreviewed conflict; reviewer sign-off; `verified` set only with a reference per row | **Yes** |
| **D5** | Opening-range integrity: cause and disposition of the five missing-bar sessions; raw-response archive; completeness check at ingestion; closure reporting | D1, D4, D0 | **Read-only re-fetch (DR-5)** of the five instrument-sessions with immutable raw-response archive; comparison recorded beside stored bars; **no candle overwrites**; `MISSING_BAR` issues recorded for history; `OR_NOT_CLOSED` reported `NOT_TESTABLE` for backfilled data | Each of the five has a recorded cause and disposition; archive immutable and hashed; stored candles unchanged (manifest equal); reviewer sign-off | **Yes** (disposition); archive and ingestion check recommended |
| **D6** | Post-remediation counts-only scan and revalidation (DR-8) | D1-D5, freeze, independent review | A new counts-only contract (with tick statuses), scan run only on the owner's instruction, independent reconciliation | Contract approved first; freeze recorded; independent review of the preparation done; the scan reproduces by a second implementation; tick statuses and coverage reported | **Yes** |

**Approved definitions for DR-3a (owner, 2026-11-23, with clarification).**
- *Material event:* an event capable of affecting **price continuity, instrument identity, historical OHLC interpretation or strategy-derived features**. It includes splits, bonuses, demergers, mergers, material rights issues, symbol and instrument-identity changes, and other relevant adjustment events.
- *Dividends:* recorded **separately**, with their adjustment treatment documented (whether and how the provider adjusts for them).
- *Affected instrument-session:* an instrument-session is affected if the event date, or the event's price-adjustment impact, **intersects the actual strategy input and lookback dependencies** of the configuration being run.
- *No arbitrary universal exclusion window:* in particular, **no fixed five-session exclusion**.
- *Consequence:* **unreconciled material events exclude the affected instrument-sessions from Stage A** (DR-3).

**Implication for D2 (analysis, not a decision; D2's reviewer must confirm).** Because "affected" depends on the actual input and lookback dependencies, D2 must record a **dependency map** per configuration before applying any exclusion. For frozen B0 the inputs are the same-session 5m bars (range, breakout window, exits to the session-end exit) and, if MG02-A1 is adopted, the tick rule; B0 has no previous-day, 15m or daily input. A uniform multiplicative adjustment (split, bonus) rescales every price of a session by one factor and leaves percentage quantities (range width, stop distance, R) unchanged, so for B0 its effect is on the tick grid and on any session in which a discontinuity occurs (for example the ex-date session of an unadjusted demerger). Configurations with cross-session inputs (CUR's 15m context and lookback) have wider dependencies. These statements are to be verified in D2, not assumed.

## 6. Project status and blockers

| Item | Status |
|---|---|
| Phase 2 (ORB specification, B0) | Approved and frozen (unchanged) |
| P0-1 scan | Executed 2026-11-23 and independently reconciled; its tick-dependent counts are not reliable; superseded for decisions by DR-8 |
| `ORB-MG-02` / MG02-A1 | Frozen text unchanged; amendment approved in principle, formal adoption pending |
| D0 | **ACCEPTED WITH CAVEATS (owner, 2026-11-25, [DEC-035](../../DECISIONS.md)).** Evidence preserved; guards and dedicated roles verified (§2.6, §2.7); off-device copy waived (§2.8); key stored, recovery verified by a manual decryption (the official script did not pass), local key removed (owner attestation); NON-INDEPENDENT owner self-review R1-R14 recorded ([package §3.4](orb-d0-review-package.md#34-owner-self-review-record-recorded-2026-11-25)) |
| D1-D6 | **NOT STARTED as remediation steps.** D0 is accepted (2026-11-25), but that does not authorise them; each needs the owner's separate authorisation. No independent reviewer is appointed (DR-7a); the DR-12 solo-research exception (§2.11, DEC-045) replaces that appointment only within its stated scope and limits |
| Stage A, Phase 3 implementation, experiments, backtests, prospective validation | NOT STARTED |
| E1-E11 | NOT STARTED |
| Application services | Backend, queue, scheduler and engine stopped since 2026-11-23 14:29 UTC (restart on acceptance) |

**Blockers.**
1. D0 formal acceptance: **done** (owner, 2026-11-25, DEC-035; with caveats; NON-INDEPENDENT review). Off-device copy waived (§2.8), review independence waived (§2.9).
2. DR-7a: no independent reviewer is appointed and the requirement is not completed. Since 2026-11-25 the owner-approved solo-research exception DR-12 (§2.11, DEC-045) applies to the defined scope; it does not complete D1-D6, which still need the owner's separate authorisation and the controls of §2.11.
3. Adoption of MG02-A1 into the specification under CLAUDE.md §8: the policy is formally approved; two wording points and seven extra vectors await confirmation (§4.10).
4. Stage A is blocked by the mandatory items D1-D6 (§5).
5. A valid broker session is needed for the DR-5 re-fetch (daily login).
6. Open Phase 3 decisions: OD-8, OD-15, OD-16.
7. No source licence has been reviewed for any paid NSE product (DR-1 condition).
8. Costs and slippage remain unverified (D-6); the historical survivorship limitation remains.

**Estimate (an estimate, not a commitment).** D0 was done in a single session; D1 3-5 engineer-days; D2 6-10; D3 4-6; D4 4-6; D5 2-4; D6 2-3; remaining total about 21-34 engineer-days (about 4-7 calendar weeks), wide uncertainty.

## 7. What this page does not authorise
No database write, restore, dump, re-fetch, curation, schema change, code change, scan, backtest or experiment. No `is_demo` value, owner-decision status other than those in §1, B0, `ORB-MG-02`, PAQS, ruleset or strategy is changed. Each implementation step needs its own approval.
