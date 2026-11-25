# ORB B0 Phase 1: original B0 backtest readiness

Date: 2026-11-25 (updated after the technical-readiness implementation). **AI-ASSISTED — NON-INDEPENDENT.** This is the author's own review. It is not an independent human review (DR-7a is open; DR-11 covered D1 only; no reviewer and no written extension exists) and it satisfies no governance requirement. It is **not a backtest authorisation**. Scope fixed by the owner: strategy `orb_b0` only, ruleset `pa-intraday 0.6.0`, original signal-close target and original RC-04; the fill-based variant is deferred and was not implemented, configured or tested. Owner decisions applied from the 2026-11-25 technical-readiness authorisation: frozen exit and cutoff never move; shortened sessions are excluded and reported separately; B0 needs no previous-day bar; a B0-specific P0-3; `INSUFFICIENT_SAMPLE` is an acceptable outcome (P0-1b not approved, not run); OD-15 and OD-16 deferred until after Stage A; an unreachable 4b floor is `INCONCLUSIVE / INSUFFICIENT_SAMPLE`; no criterion is lowered after results.

**Correction to the earlier version of this report.** It named `scratchpad/d1/matrix_64.csv` as the price-basis matrix. That file is the 64-row instrument-identity table (ISIN, listing dates), not the per-session matrix. The per-session matrix (32,500 rows) is `price_scale_matrix_dev_v2.csv` in the read-only backup; it is now archived (§6). The hashes quoted earlier for `matrix_64.csv` and `matrix_raw.json` were of the wrong files and are withdrawn.

> **Governance update (DEC-045, 2026-11-25).** After this report was written the owner recorded an owner-approved solo-research exception to DR-7a ([DR-12](orb-data-remediation.md#211-dr-12-dr-7a-solo-research-exception-owner-approved-2026-11-25)). Statements below that "DR-7a is open" or "no extension exists" are as of the report date. The exception is not an independent review and completes none of the other gates: tables still need review, hashing and owner approval, spec amendments, OD-15/OD-16, the pre-registration and the run authorisation remain open, and the verdict stays blocked for those reasons.

## 1. Repository state and files changed

Verified now: branch `feat/phase1-stabilization`, HEAD `a33bb83`; 29 modified and 45 untracked paths, no deletions, nothing committed, stashed, reset, merged or pushed; no database write, service restart, reference-table load, backtest, scan, replay, control replicate or calibration was run.

Checks run now: **721 engine tests passed, 0 failed, 1 skipped** (`tests/integration` not run); `ruff check` and `ruff format --check` clean (220 files); `mypy app` clean (124 files); `check_ruleset_hash.py` OK; `check_strategy_registry.py` OK. The earlier baseline of this follow-up was 669; the 52 added tests are listed per file below. Released rulesets 0.1.0 to 0.6.0 unchanged (hash tripwire test); `pa-intraday 0.6.0` = `aaa4ab079aa1da614c26be3dde958598e514106dba42bbd07405d88f538fc426`. No frozen specification and no acceptance criterion was edited in this follow-up (the uncommitted edits already in `docs/strategies/` come from earlier work).

New code (`python-engine/`): `app/backtest/b0_run.py` (strict runner logic), `b0_accounting.py` (GAP-2), `controls.py` and `control_stats.py` (E6), `evidence.py` (E8), `scripts/run_orb_b0.py` (entry point, not executed).
Modified: `app/domain/levels.py` (`b0_levels`, one function shared by the detector and the controls), `app/backtest/b0_eligibility.py` (frozen-timing exclusion), `app/backtest/loader.py` (B0-path rules), `app/backtest/reference_tables.py` (price-basis loader), `scripts/check_strategy_isolation.py` (the `orb_b0` mapping I had added in Step 2 is removed).
Tests added: `tests/backtest/test_b0_phase1.py` (14), `test_controls_e6.py` (12), `test_control_stats_and_evidence.py` (14), `tests/trading/test_orb_b0_isolation.py` (12).
Evidence: `docs/research/evidence/od8/price_scale_matrix_dev_v2.csv` and `price_scale_matrix_dev_v2.MANIFEST.json`.

## 1.1 Reference-table approval statuses and the result label (DEC-045)

Implemented after the DR-12 exception was recorded; synthetic tests only (`tests/backtest/test_solo_approval.py`, 36 tests). No real table exists or was loaded.

| Status | Meaning | Accepted when |
|---|---|---|
| `INDEPENDENTLY_REVIEWED` | An actual independent human review occurred and is evidenced | Default path, unchanged. Solo-approval metadata on such a table is refused as contradictory |
| `OWNER_APPROVED_SOLO_RESEARCH` | Owner approval under DEC-045 / DR-12. Independent human review has **not** occurred | The caller opts in explicitly; `decision_ref` is `DEC-045` or `DR-12`; `owner_approval` has `approved_by` = `owner`, an ISO `approved_on` and a `record`; no independent-review claim keys |

Anything else (missing, unknown, `UNREVIEWED`, AI-assisted, malformed) is refused. The two statuses are never converted, mapped or inferred from owner approval, AI review or passing tests. Solo approval certifies neither data quality nor independent validation: hash pins, schema, row provenance, date coverage and conflicts are checked exactly as before. **Run label:** a run whose tables include any solo-approved table has basis `OWNER_APPROVED_SOLO_RESEARCH` and the exact result label `EXPLORATORY — SOLO RESEARCH — NOT INDEPENDENTLY VALIDATED`, stored in the run record's `reference_data`, in `EvidenceRecord` (`approval_basis`, `approval_decision_refs`, `table_review_status`, `result_label`) and at the top of the runner's output; an all-independent run carries no label. Mixed statuses: the weakest basis governs; each table's own status stays unchanged in the record. `EvidenceRecord` validates itself on construction, so a stripped, altered or contradictory label cannot be created.

## 1.2 Strict-runner exclusivity (audit and safeguards)

`orb_b0` and ruleset `pa-intraday 0.6.0` are reserved for `scripts/run_orb_b0.py`. The contract (`app/backtest/b0_contract.py`) is enforced where every replay path builds its configuration (`BacktestConfig.__post_init__`) and where evidence is built (`EvidenceRecord`): the strategy must be `orb_b0` on 0.6.0 with its released hash and RESEARCH role, and the run record must carry the SHA-256 and approval status of all four tables, the resolver version and a consistent approval basis (exact solo label when any table is owner-approved). A direct library call, a chunked run, a merge, a control replay or a hand-built configuration therefore cannot produce a B0 record without it; ruleset 0.6.0 with any other strategy is refused too, so a legacy result cannot be mistaken for B0. The legacy command lines (`run_backtest.py`, `run_chunks.py`, `scan.py`, `run_screen.py`, `run_diagnostics.py`, `check_strategy_isolation.py`) refuse both names with a message pointing to the strict runner, before settings or data are touched. The API already refuses research rulesets. Non-B0 backtests are unchanged. Tests: `tests/backtest/test_b0_exclusivity.py`.

## 1.3 Final execution-path and evidence-integrity audit (AI-ASSISTED — NON-INDEPENDENT)

**Search coverage.** Bounded searches of every source tree (`python-engine/app`, `scripts`, `tests`, `rulesets`, `contracts`, `infrastructure`, `.github`, `frontend/src`, `backend/{app,routes,database,tests,config}`, root `scripts/`, `Makefile`, compose files) for `orb_b0`, `0.6.0`, the detector, `BacktestConfig`, `EvidenceRecord`, `build_evidence`, `simulate_control_set`, the run, chunk and merge functions. Not searched: `node_modules`, `.venv`, `vendor`, `__pycache__`, `.git`; the compressed or generated `out/` baseline directory was listed, not read. The earlier timeout was a macOS shell without `timeout`, so those greps had silently returned nothing; they were redone without it.

| Path | Can invoke B0? | Contract enforced? | Can create evidence? | Assessment |
|---|---|---|---|---|
| `scripts/run_orb_b0.py` | yes (the only intended path) | yes, through `b0_run` | yes, with run digest verified against the result | Authoritative |
| `scripts/run_backtest.py` | refused at the command line; library layer also enforces | yes | no | Closed |
| `scripts/run_chunks.py` | refused before any directory or process | yes | no | Closed |
| `scripts/merge_backtests.py`, `app/backtest/chunks.py` | `save_chunk` and `merge_chunks` refuse B0 chunks | yes | no | Closed |
| `scripts/scan.py`, `run_screen.py`, `run_diagnostics.py`, `check_strategy_isolation.py` | refuse ruleset 0.6.0; B0 not selectable | yes | no | Closed |
| `app/backtest/strategy_run.py` (`strategy_config`, `run_strategy_backtest`) | yes (library) | yes, via `BacktestConfig` (needs execution context) | no | Enforced |
| `app/backtest/run.py` (`BacktestConfig`, `run_backtest`, `assemble_result`) | yes | yes; also refuses the B0 analysis step under another strategy's config | run digest set | Enforced |
| `app/backtest/controls.py` (`simulate_control_set`) | yes (controls) | yes, needs the reference and context; no caller in `app/` or `scripts/` | no | Enforced, not called |
| `app/backtest/b0_accounting.py` | analysis only, no result | n/a | no | No result path |
| `app/backtest/evidence.py` (`build_evidence`, `EvidenceRecord`) | no | yes, B0 evidence needs strict data and a run digest | yes | Enforced; sole caller `run_orb_b0.py` |
| `app/analysis/*`, `app/api/*` (scan, positions, risk) | no (default detectors, LIVE ruleset only) | the API refuses research rulesets | no | Closed |
| `app/workers/*`, `app/schemas/jobs.py` | no backtest job exists (enum value only) | n/a | no | Closed |
| Laravel (`backend/`) | no backtest or B0 reference | n/a | no | Closed |
| CI, compose, Makefile | no B0 or backtest invocation | n/a | no | Closed |
| Tests | yes, synthetic | fixtures only; the hash override seam is function-scoped | synthetic | Isolated |

A static test (`tests/backtest/test_b0_integrity_audit.py`) pins this inventory: a new module that mentions B0, builds a configuration, builds evidence, issues a context or saves chunks fails until it is audited.

**What the contract guarantees (and what it does not).** For `orb_b0` or ruleset 0.6.0, `BacktestConfig` accepts only: the released hash, RESEARCH role, complete strict-runner reference data (four table hashes, resolver version, per-table statuses, consistent approval basis and label) **and** an immutable `B0ExecutionContext` whose digest binds strategy, ruleset hash and those data; the reference data is then frozen read-only. The run record carries a run digest over its identity fields (inputs hash, reference data, slippage, costs, universe, span); B0 evidence must carry it and `verify_evidence_for_result` rejects evidence from another run, a result edited after it was built, a legacy result, and a record with no digest. Fabricated dicts, edited or mis-paired contexts, changed rulesets and reused evidence are refused. **It does not prove runner origin:** code that deliberately calls `issue_context` with well-formed evidence gets a context (a test states this limit). The structural defence is that a repository test fails if any module other than `b0_run` issues one; no secret or signing is used and none is claimed.

**Ruleset hash.** One definition (`b0_contract.B0_RULESET_HASH`), equal to the tripwire constant, the engine file and the seeder copy (tested). No environment or setting overrides it. The strict runner holds its own binding (`b0_run.B0_RULESET_HASH`), so the test fixture that pins a modified copy for synthetic tests (function-scoped, `tests/conftest.py`) cannot reach `b0_run.check_b0_ruleset`; a test proves it, and another proves the real constant is restored. `run_orb_b0.py` loads the released file and checks the hash before reading any table or candle.

## 2. Completion status

| Item | Status | What exists |
|---|---|---|
| **GAP-1** strict runner | **Implemented, not executed** | `b0_run.py`: refuses anything but `orb_b0` / `pa-intraday 0.6.0` with its released hash and the RESEARCH role; refuses if the registry maps `orb_b0` to anything but the B0 detector; builds the four tables from required, SHA-256-pinned, review-gated files (no defaults); loads sessions through the strict loader path (dated session table, historical tick table, event exclusions, no legacy special-session list, no 15:30 or 0.05 default); records all table hashes and the resolver version in the run record; `scripts/run_orb_b0.py` stops before any data is read if a table is unreviewed, unpinned or mismatched, never overwrites an existing result and writes a result only if the accounting reconciles |
| **GAP-2** rejection accounting | **Implemented** | `b0_accounting.py`: one measured outcome per evaluated instrument-session (`OR_TOO_NARROW`, `OR_TOO_WIDE`, `INVALID_RANGE:*`, `WHIPSAW`, `WINDOW_EXPIRED`, `CUTOFF_EXPIRED`, `NO_BREAKOUT`, `SIGNAL_NO_TRADE:*`, `SIGNAL_CANDIDATE`, `SNAPSHOT_INVALID:*`); `reconcile` checks outcomes against the eligibility map, the loader exclusions, and candidates against fills plus skips, and reports any mismatch instead of inferring counts |
| **GAP-3 / E6** matched controls | **Implemented, not executed** | `controls.py` (plan §4.2: same eligibility objects plus the width band, frequency per instrument-month, empirical signal-time bins, 20 time redraws then session redraw, redraw rate, `CONTROL_STRAINED`, seeded and sorted, replay through `run_backtest` with a forced signal and the same levels function), `balance_report` (counts, CDF gaps 0.01 / 0.03, stop-distance median flag), `control_stats.py` (month totals, edge, month-block bootstrap with the documented nearest-rank percentile, sampling error, supplementary p, thirds and stability, a generic calibration harness). It is not `draw_control` and does not reuse it. No replicate or 4b replay was run |
| **E8** run records | **Implemented** | `evidence.py`: `EvidenceRecord` (data class, UTC timestamp, variant number, commit, working-tree flag, ruleset hash, reference hashes, seeds, reproducibility metadata, AI label), `VariantLedger`, `PreRegistration` draft and `validate_for_freeze` that only reports problems and never fills a value. **No pre-registration was created**; thresholds and hashes stay unset |
| **AMB-1** | **Done** | below |
| **AMB-3** | **Done** | below |
| **P0-3 for B0** | **Done on synthetic bars** | below |
| Price-basis archive | **Done** | §6 |

## 3. P0-3 B0 isolation evidence (`tests/trading/test_orb_b0_isolation.py`, 12 tests, all pass)

The existing isolation proof covers today's opening-range detector (CUR) and is **not** claimed for B0; the `orb_b0` mapping was removed from `check_strategy_isolation.py` so that script cannot be read as a B0 proof. Shown instead, on hand-built and 600 seeded random sessions:
- the registry maps `orb_b0` to `detect_orb_b0` alone (not `detect_opening_range`, not in `ALL_DETECTORS`); the runner also checks this before every run, and a patched registry is refused;
- B0 setups and levels are identical, at every bar prefix, whether the other five detectors and the other strategies' ruleset flags are on or off;
- no other detector produces an `OrbB0Setup` (the default combined run contains none; CUR emits plain `Setup`s); every B0 setup is LONG and an `OrbB0Setup`;
- a full B0 run is unchanged when every other detector would raise if called;
- B0 output is identical for no previous-day levels, extreme previous-day levels and three different 15m series;
- the B0 signal stream equals an independent oracle of the frozen rules on 600 seeded sessions (all six outcome kinds seen);
- a ruleset without the B0 keys fails closed (no fallback to another detector).
Limit: it proves isolation of the code, not of results; no real bars were used.

## 4. AMB-1 and AMB-3 evidence (`tests/backtest/test_b0_phase1.py`)

- **AMB-1:** the frozen cutoff (close minus 45 minutes) and exit (close minus 15 minutes) are never moved. A session whose facts are not the regular 09:15 to 15:30 gets `FROZEN_TIMING_NOT_APPLICABLE` from the shared eligibility function and, in the loader, is dropped whole and reported as a separate whole-session exclusion; the loader's session close stays 15:30 for every session that is replayed. The 15:15 sessions from 2026-08-03 are therefore excluded. Combined with the special-session exclusions this is the only way sessions leave for timing reasons. Limit: it depends on the session table, which does not exist yet as a reviewed file.
- **AMB-3:** code inspection shows B0 never reads `prev_day` (the detector and `b0_levels` use only the validated range, the bars and the ruleset; `analyse` accepts `None`). On the B0 path the loader passes `prev_day=None`, never applies `MISSING_PREV_DAY_LEVELS` or `INCONSISTENT_PREV_DAY_LEVELS`, and refuses the legacy `skip_days` list. Tests: a session with no 1D bar is processed; the same input through the non-B0 path is still excluded; missing opening bars still exclude (`OR_NOT_CLOSED`, `OR_MISSING_BAR`); output is invariant to the previous-day value. `daily_levels`, if supplied, feeds only the optional provider-ratio safety net and its absence is not an exclusion.

## 5. Governance and reviewers

| Blocker | State |
|---|---|
| DR-7a | Independent-review requirement **not completed**; no independent reviewer. **Owner-approved solo-research exception recorded after this report (DEC-045 / DR-12).** The loader now has a distinct `OWNER_APPROVED_SOLO_RESEARCH` status, accepted only on explicit opt-in (§1.1). Tables still need preparation, provenance, SHA-256 pinning and recorded owner approval |
| DR-11 | Covered D1 only; not extended |
| OD-15 (matched-control method and interval) | Deferred until after Stage A (owner); E6 is built but not approved |
| OD-16 (prospective protocol) | Deferred until after Stage A (owner) |
| MG02-A1, 0.6.0 in spec metadata, session facts | Frozen-spec amendments blocked until independent review |
| Pre-registration | Not created (E8 supports a draft only) |

Work classes: **A (done)** inspection, code, tests, evidence archive, this report; **B (blocked)** DR-7a, spec amendments, real tables, OD-15/OD-16 approval; **C (needs separate authorisation)** P0-1, any run, replay, scan, control replicate, calibration, final pre-registration, database writes.

## 6. Reference tables and the price-basis archive

| Table | State | Hash |
|---|---|---|
| Tick table (D2) | Does not exist; loader, resolver and gate ready | none |
| Session-facts table (D6) | Does not exist; loader and gate ready | none |
| Corporate-event table (D5) | Does not exist; loader and gate ready | none |
| Price-basis matrix | **Archived, not approved.** `docs/research/evidence/od8/price_scale_matrix_dev_v2.csv` (32,500 rows: 50 instruments x 650 development sessions, 2024-01-01 to 2026-11-19; 23,509 `TRADED_SCALE_VERIFIED`, 8,991 `PROVIDER_ADJUSTED`) with `price_scale_matrix_dev_v2.MANIFEST.json` | SHA-256 `33f9a1d7afaf180ecb58764c3ae23c1d82a7352f9c9716565a10a0dadfea954b`, identical to the read-only original `~/priceaction-backups/d1-20261125/stage-a-evidence/analysis/price_scale_matrix_dev_v2.csv` (preserved) and to its `SHA256SUMS` entry |

The manifest records the original filename and location, the generating method and scripts (with their hashes), the generation timestamp, and states: development-only, **not independently reviewed, not approved for backtesting, not an approved reference table**. The loader refuses it by default (a test loads the real file and confirms the refusal and the counts). No table was loaded.

## 7. Sample size (decision note from the previous version, with the owner's rulings)

Rulings now recorded: `INSUFFICIENT_SAMPLE` is acceptable; P0-1b is neither approved nor run; the 1,000-trade gate stays as written; if the 4b floor is unreachable the result is `INCONCLUSIVE / INSUFFICIENT_SAMPLE`; no criterion is lowered after results. The arithmetic of the earlier version stands as context only (3.1% fills per instrument-session for 1,000 development fills; 3.3% for 100 in 60 prospective sessions; about 17% for a precision of the order of 1,000 at 120 sessions) and, with F-1, the first run is also the first measurement of the fill rate.

## 8. Remaining blockers

1. **DR-7a** (reviewer or written extension), then the three curated tables and the matrix reviewed and hash-pinned; the frozen-spec amendments after review.
2. Owner rulings still open: whether the `orb_b0` mapping removal and the B0-only P0-3 are accepted as the P0-3 definition (the plan's text was written for CUR); the D5 provider-ratio-step definition (F-3 of the Step 2 record).
3. Known limits of what was built: the accounting and controls were exercised only on synthetic bars; `scripts/run_orb_b0.py` was never run against a database; chunked B0 runs do not persist `reference_data` (the B0 runner is not chunked); the calibration protocol of plan §4.6 (generator and thresholds) is not defined, only a harness exists; E11 (runtime benchmark of 1,000 replicates) was not run; the control uses the same RC-04 fill rule as ORB, so under F-1 it is expected to be strained (reported by design).
4. After the above: a separate explicit authorisation to run.

## 9. Commands for the eventual run (NOT EXECUTED)

From `python-engine/`, after every blocker is cleared and the owner has authorised the run. The table paths and hashes below are placeholders: no real table exists.

```
.venv/bin/python scripts/run_orb_b0.py --from <FIRST> --to <LAST> --members-on <DATE> \
  --experiment 4a --data-class DEVELOPMENT \
  --tick-table <TICK.json> --tick-sha256 <SHA> --event-table <EVENTS.json> --event-sha256 <SHA> \
  --session-table <SESSIONS.json> --session-sha256 <SHA> \
  --price-basis <price_scale_matrix_dev_v2.csv> --price-basis-manifest <...MANIFEST.json> --price-basis-sha256 <SHA> \
  --variant-ledger <LEDGER.json> --out-dir <EVIDENCE_DIR>
# the same with --experiment 4b (a separate output file; a result is never overwritten)
```
Before it: `.venv/bin/python -m pytest tests --ignore=tests/integration -q`, `.venv/bin/ruff check .`, `.venv/bin/mypy app`, `python3 ../contracts/scripts/check_ruleset_hash.py`. The matched-control replicates and the statistics (`controls.py`, `control_stats.py`) have no script yet and are not authorised; a driver would be written and reviewed before OD-15.

## 10. Verdict

**BLOCKED — GOVERNANCE.** The technical prerequisites that the owner authorised are implemented and tested on synthetic data (GAP-1 to GAP-3, E6, E8, P0-3 for B0, AMB-1, AMB-3, the matrix archive). The project is **not** ready for backtest authorisation: DR-7a is open, the tick, session and event tables do not exist and nothing curated may be loaded without an independent reviewer or a written extension, the frozen-spec amendments are blocked, and OD-15 and OD-16 are deferred. `READY FOR GOVERNANCE REVIEW` applies to the code and the B0 specification conformance in my non-independent view; it does not apply to the run.
