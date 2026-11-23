# Phase 1 — Engineering Stabilization

| Item | Value |
|---|---|
| Status | **Engineering work complete. Owner decisions D-1 to D-4 recorded and implemented 2026-11-23 (T-I150, uncommitted). Phase 2 not started and waits for explicit approval** |
| Date | 2026-11-23 |
| Scope | Make the existing engine consistent, reliable, testable and auditable without changing the trading methodology. No strategy was designed, tuned or added; no entry rule, exit methodology, PAQS weight, PAQS threshold or risk parameter changed |
| Branch | `feat/phase1-stabilization` (not committed; awaiting the owner) |

## 1. Workstream status

| ID | Workstream | Status | Result |
|---|---|---|---|
| P1 | Exit execution consistency | Done | One rule, `evaluate_bar_exit`, now drives backtest and live monitor; 2 behavioural discrepancies fixed. [Spec](../trading/exit-execution-specification.md) |
| P2 | Ruleset consistency | Done, 1 decision open | Differences documented to the key; roles and a live-only API guard; hash recorded in every backtest. [Comparison](../trading/ruleset-comparison.md) |
| P3 | Configuration integrity | Done, 1 decision open | 3 dormant keys verified (2 obsolete, 1 missing guard), none deleted; hardcoded and duplicated parameters listed. [Inventory](../trading/configuration-inventory.md) |
| P4 | API and strategy consistency | Done | One registry, a CI check, validators and the frontend map aligned. [Contract](../architecture/api-strategy-contract.md) |
| P5 | Rule-level decision logging | Done as a read-only layer | Records and a replay hook; detector-internal rules and persistence are not done. [Spec](../trading/rule-evaluation-logging.md) |
| P6 | Risk and execution integrity | Verified and documented | Defaults pinned by tests; no parameter changed; live-cost gap and placeholders documented (§4) |

## 2. Engineering decisions and rationale

| ID | Decision | Rationale |
|---|---|---|
| E-1 | The backtest's `evaluate_bar_exit` is the authority for exits; the monitor was changed to call it, not the reverse | It already encoded TRD-06 §4.2 and every historical backtest used it, so no backtest result changes |
| E-2 | The monitor reports a structure exit at the CHoCH bar's close, not the next open | Live code cannot see the next bar; same decision, no behaviour change (spec §2) |
| E-3 | Research and retired rulesets are refused by the API (`RULESET_NOT_LIVE`); roles live in code and a test forces every new file to declare one | Prevents a research configuration (structure exit off, extra strategies) being presented as live. Does not change the default `0.1.0` |
| E-4 | Rulesets were not merged and no key was deleted | Released rulesets are immutable (ADR-008); every difference is deliberate research design |
| E-5 | Unsupported identifiers are rejected with 422 rather than returning an empty list | An empty list is a misleading answer. Cost: one stricter validator, no known client |
| E-6 | Decision records are derived from the existing result objects, not emitted by instrumenting the decision code | Guarantees the decision mechanism is untouched; the trade-off is that detector-internal rules are not visible |
| E-7 | `ruleset_hash` was added to `RunRecord` with a default, and printed in the report header | Backward compatible with stored chunks; identifies the exact configuration |

No ADR was required: no architectural or product decision changed (CLAUDE.md §8).

## 3. Test and regression report

All numbers are real runs on 2026-11-23.

| Suite | Before | After | New tests |
|---|---|---|---|
| Engine, local venv (`pytest`) | 438 passed, 3 skipped | **483 passed, 3 skipped** | +45: `test_audit.py` 11, `test_ruleset_integrity.py` 15, `test_risk_defaults.py` 14, `test_position_monitor.py` 5 |
| Engine, Docker (`make test-engine`) | not run before | 480 passed, 6 skipped | the 6 skips are environmental: 3 need `SCHEMA_DIFF_DATABASE_URL`, 3 need the compose file outside the container (run in the local venv) |
| Laravel (`make test-backend`, own database) | 194 (the count in CURRENT.md; not re-run before the change) | **195 tests, 2,924 assertions, OK** | +1 method (scanner filter follows the registry) and 3 new assertions in the trade-plan validation test |
| Frontend (Vitest) | 88 | **89 passed, 19 files** | +1 (the old "unknown type" test, which asserted the defect, was rewritten into two) |
| Contracts (`unittest`) | 15 | 19 passed | +4 (`test_check_strategy_registry.py`) |
| Contract checks | n/a | `check_ruleset_hash.py` OK, `check_strategy_registry.py` OK | |
| ruff, mypy (`app`) | clean | clean (113 files) | |

`tsc --noEmit` reports only duplicate-identifier errors in `.next/types/* 2.ts` (iCloud copies of build output, unrelated to this change); there is no error in `src`. Redocly lint of the edited OpenAPI file was not run locally (CI runs it); the change is one enum value and a description. ESLint on the frontend was started but did not finish in this session, so it is not reported as passing.

Failed tests: one, expected and fixed: `scanner.test.ts` "falls back safely for a setup type the frontend does not know" asserted that `LIQUIDITY_SWEEP_REVERSAL` maps to `range-bound`, which is the audit finding itself.

Not tested: real-bar equivalence of the live monitor and the backtest (the grid test is synthetic); Docker end-to-end through the running stack; a browser check of the new labels.

## 4. Risk and execution integrity (P6)

Verified against the code and `pa-intraday 0.1.0`, on the planning account (₹1,00,000):

| Constraint | Intended | Configured and enforced | Match |
|---|---|---|---|
| Capital | ₹1,00,000 | Laravel `TRADING_CAPITAL_DEFAULT` 100000 | Yes |
| Risk per trade | 0.5% (₹500) | `risk.default_risk_per_trade_pct` 0.5; sizing binds at ₹500 | Yes |
| Max position value | ₹50,000 | `risk.default_max_position_value` 50000; binds first on tight stops (stop under 1% gives risk below ₹500) | Yes |
| Min reward/risk | 2.0 | `risk.min_rr` 2.0, checked at signal, at risk check and again at fill | Yes |
| Stop distance | 0.15% to 2.0% | `risk.min/max_stop_distance_pct` | Yes (TRD-05 value, hypothesis) |
| Daily loss limit | placeholder 1.5% (₹1,500) | 1.5; trips at ₹1,500, size shrinks to the remaining budget before that | Matches the placeholder, **not owner-approved** |
| Losing streak | placeholder 3 | 3, trips at 3 | placeholder |
| Max open positions | placeholder 2 | 2 | placeholder; two full positions equal 100% of capital and no margin model exists |
| Max open risk | placeholder 1.0% | 1.0; two ₹500 positions exactly reach it | placeholder |
| Per-request risk override | registry range 0.1 to 2.0% | `RiskCalculateRequest` and `TradePlanRequest` accept up to 5% | **No** (decision D-3) |

Backtest and live use the same `calculate_risk`, `derive_account_state` and `simulate_entry`, so sizing and limits behave the same on both sides (the single-strategy research mode deliberately lifts them).

**Costs and slippage.** The backtest models brokerage, STT, exchange charge, SEBI, stamp duty and GST (schedule `nse-intraday-assumed-0`, unverified; the Groww-published schedule matched within +0.005R per trade in DX-6) and adverse slippage 0.05% on entries and stop exits only (unverified). Live plans have **no cost estimate**: `RiskResult.est_round_trip_costs` and `rr_after_costs` are always `None`.

**Resolve before paper or live use:**
1. Show estimated round-trip charges and R:R after costs on every plan (the schedule exists; wiring it into the risk result and the contract is a change to ARC-04, OpenAPI and the engine schema). At a 1% stop, friction is about 0.3R, so a 2.0R plan is closer to 1.7R net.
2. Owner approval of the four placeholder limits (OQ-TRD-04) and a decision on whether a margin model or a trades-per-day limit is needed (not specified in TRD-05).
3. Measure real slippage, and confirm historical charge rates for 2024-2025 (OQ-BT-02).
4. Decide D-3 (per-request risk cap).

## 5. Owner decisions (recorded 2026-11-23)

The owner reviewed this report and decided D-1 to D-4 on 2026-11-23 ([DEC-024](../../DECISIONS.md)). T-I150 implemented them on 2026-11-23 (see §5.1); no released ruleset was modified.

| ID | Decision | Status |
|---|---|---|
| D-1 | **Approved.** `pa-intraday 0.1.0` stays the canonical live ruleset. Research rulesets stay separate and must never be silently selected for live execution | Already enforced by the ruleset roles and the `RULESET_NOT_LIVE` guard (E-3); the hash of every released ruleset is now pinned by a test |
| D-2 | **Approved.** Retire `score.min_display`, `setup.rejection_min_wick_ratio` and `zone.max_width_pct` in the next ruleset version, subject to compatibility checks. Released rulesets are never modified | **Implemented:** `pa-intraday 0.5.0` = `0.1.0` minus the three keys, role RESEARCH, output equal to `0.1.0` (tested). Promotion to LIVE additionally requires independent strategy validation, out-of-sample evidence, paper-trading evidence, risk and execution validation and a separate owner approval with an ADR (owner, 2026-11-23) |
| D-3 | **Approved.** Default risk per trade 0.5%; maximum configurable 2%; requests above 2% are rejected; position risk is never raised automatically. **2% is a technical ceiling, not a recommended trading risk** | **Implemented:** Laravel `lte:2` on both overrides, engine `risk_pct` validator (422) and `calculate_risk` ceiling check, OpenAPI and TRD-05 wording; default stays 0.5% |
| D-4 | **Approved with conditions.** Keep slippage configurable; apply adverse assumptions to the entry and to every exit type (stop, target, session-end, structure); keep the assumptions separately identifiable by execution type; never describe them as measured slippage; support sensitivity runs; report gross, estimated net and measured net as distinct figures | **Implemented:** `SlippageModel` with entry, stop, target, session-end and structure values; `adverse-all` default for new runs, `legacy-stop-only` preserved, `--sensitivity`, report with gross before slippage / after slippage / estimated net / measured net NOT AVAILABLE |

### 5.1 T-I150 implementation (done 2026-11-23, uncommitted)

**D-2.** `python-engine/rulesets/pa-intraday/0.5.0.json` and the byte-identical seeder copy; role RESEARCH in `RULESET_ROLES`; TRD-01 Appendix B and `rulesets/CHANGELOG.md`. Compatibility checks: no code reads the keys; `test_0_5_0_gives_the_same_analysis_as_0_1_0_on_the_same_bars` runs `analyse` on the same bars under both and compares the results; the ruleset hash check passes; every ruleset has a seeder copy; `test_released_rulesets_have_not_been_modified` pins the six hashes. The optional load-time guard was not added (the key no longer exists in `0.5.0`).

**D-3.** `RiskCalculateRequest` and `TradePlanRequest` `lte:2`; `PositionSizeRequest.risk_pct` validator (0 < v <= 2, so 422); `MAX_RISK_PER_TRADE_PCT` and `RISK_PCT_ABOVE_CEILING` in `calculate_risk`; `contracts/engine/PositionSizeRequest.json` regenerated; OpenAPI descriptions; TRD-05 §2. Tests: 2 accepted, 2.01 / 3 / 5 / 0 rejected at all three layers, the 0.5% default sent when no override is given. The stored profile was already limited to 0.1 to 2.0 and the frontend settings form to 0.1 to 2.  The analysis plan dialog takes a rupee risk budget; I did not trace how it reaches the engine, so confirm it cannot exceed 2% of capital (follow-up).

**D-4.** `app/backtest/slippage.py` (`SlippageModel`, `adverse-all`, `legacy-stop-only`, custom per-type, `from_options`); `ExitConfig.slippage`, `step_position`, `close_trade` (new `Trade.slippage_cost`), `replay_session`, `BacktestConfig.slippage`, `RunRecord.slippage`, saved chunks and merge compatibility, `report.py` (`performance_basis`, `sensitivity_table`, "ASSUMED, not measured" and "measured net NOT AVAILABLE"), `run_backtest.py` (`--slippage-model`, `--slippage`, `--sensitivity`) and `run_chunks.py`. Default for new CLI runs: `adverse-all` at `backtest.slippage_pct` (0.05%); library default and old chunks: legacy, so earlier results reproduce exactly (the existing 400+ engine tests that pin hand-computed legacy values pass unchanged). TRD-06 §4.2 and new §5.1, and the exit specification, are updated.

Not done in T-I150: the research simulators in `diagnostics/daily*.py` and `screen.py` keep their own legacy slippage copies (published research reproduces; moving them is T-4); live plans still have no cost estimate (B-2, which will reuse this model); no CLI run was made against the stored database (no backtest was executed in this task, so no result changed or was produced).

## 6. Remaining blockers and technical debt

| ID | Item |
|---|---|
| B-1 | Closed by D-1 (`0.1.0` canonical). Open: whether the new version from D-2 is ever promoted to live |
| B-2 | Live cost estimate missing on plans (§4, item 1) |
| B-3 | Risk placeholders unapproved (OQ-TRD-04); no margin model; no trades-per-day limit |
| B-4 | Cost schedule and slippage unverified (OQ-BT-02); no point-in-time universe (OQ-BT-01); NSE holidays not loaded |
| T-1 | Detector-internal rules are not in decision records; no persistence or API for them |
| T-2 | `FAILED_BREAKDOWN_RECLAIM` missing from the database `setup_type` CHECK constraints (gate before any live use) |
| T-3 | Frontend filter dropdowns list demo-only setup types |
| T-4 | Live monitor vs backtest not compared on real bars; duplicated research constants (`SLIPPAGE_PCT`, `PIVOT`, `OR_BARS`) |
| T-5 | Open items already in CURRENT.md that Phase 1 did not touch: scanner signal vs risk rejection (T-I135), gap check at analysis time (T-I136), previous-day levels (T-I138) |

## 7. Phase 2 readiness

D-1 is answered (`0.1.0`). Phase 2 (strategy validation) can start from an engineering standpoint: live and backtest exits agree, every backtest records the exact configuration, strategy identifiers cannot drift, and any decision can be explained from a record. The D-4 slippage model has landed, so net results will use the new assumption; costs and slippage still stay unmeasured (B-4). Phase 2 does not begin automatically.

## 8. T-I150 test report (2026-11-23)

| Suite | Result |
|---|---|
| Engine, local venv | **500 passed, 3 skipped** (was 483; +17: slippage 8, ruleset integrity 6, chunks 1, risk ceiling 1 domain and 1 API) |
| Engine, Docker (`make test-engine`) | 496 passed, 7 skipped (environment skips: 3 need a database URL, 3 need the compose file, 1 needs the backend seeder directory) |
| Laravel (`make test-backend`) | **196 tests, 2,936 assertions, OK** (+1 method for the 2% ceiling, +1 assertion in the trade-plan test) |
| Frontend (Vitest) | 89 passed (no frontend change) |
| Contracts | 19 unit tests, `check_ruleset_hash.py` (six rulesets), `check_strategy_registry.py`, engine schema export `--check` all OK |
| ruff, ruff format, mypy | clean (114 files) |

Failures: none. Limitations: no backtest was run against the stored bars, so the new default `adverse-all` has no published results yet; Redocly lint of the two OpenAPI description additions runs in CI only; `scripts/run_backtest.py` was import-checked and unit-covered through the library, not executed against the database.
