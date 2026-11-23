# API Strategy Identifier Contract

| Item | Value |
|---|---|
| Status | Implemented (Phase 1 P4, 2026-11-23) |
| Source of truth | [`contracts/strategy-registry.json`](../../contracts/strategy-registry.json) |
| Enforced by | `contracts/scripts/check_strategy_registry.py` (CI step in `contracts-ci.yml`, unit tests in `test_check_strategy_registry.py`), Laravel validation tests, a frontend mapping test |

## 1. Identifiers and status

A "strategy" is a setup type. The identifier is the engine's `SetupType` value, used unchanged in the OpenAPI `SetupType` enum, Laravel validators and the database. The frontend maps each to a display key.

| Identifier | Status | Direction | Live ruleset 0.1.0 emits it | Scanner filter | Trade plan |
|---|---|---|---|---|---|
| `OPENING_RANGE_BREAKOUT` | IMPLEMENTED | LONG | yes | accepted | accepted |
| `PREV_DAY_HIGH_BREAK` | IMPLEMENTED | LONG | yes | accepted | accepted |
| `BREAKOUT_RETEST` | IMPLEMENTED | LONG | yes | accepted | accepted |
| `PREV_DAY_LOW_BREAK` | IMPLEMENTED_INFORMATIONAL | SHORT | yes, informational only | accepted | rejected (shorts are never actionable) |
| `LIQUIDITY_SWEEP_REVERSAL` | RESEARCH_ONLY | LONG | no (`0.2.0`+) | accepted | accepted |
| `FAILED_BREAKDOWN_RECLAIM` | RESEARCH_ONLY | LONG | no (`0.4.0`) | accepted | accepted |
| `TREND_CONTINUATION` | UNSUPPORTED | none | no detector exists | rejected | rejected |
| `SUPPORT_REJECTION`, `TREND_PULLBACK` | LEGACY (retired `pa-core`) | none | no | rejected | rejected |

Research-only identifiers are valid in the contract so a future live ruleset can emit them, but the API refuses research rulesets ([ruleset-comparison](../trading/ruleset-comparison.md) §2), so today a request for them returns an empty or "no such setup" result, never a research result presented as live.

## 2. What changed (2026-11-23)

| Layer | Before | After |
|---|---|---|
| Laravel scanner filter | accepted `TREND_CONTINUATION` (silently an empty list), lacked `FAILED_BREAKDOWN_RECLAIM` | engine types only; unsupported identifiers get 422 `VALIDATION_FAILED` |
| Laravel trade plan | accepted `TREND_CONTINUATION`; lacked `FAILED_BREAKDOWN_RECLAIM`; also lacked `PREV_DAY_LOW_BREAK` (kept out on purpose) | long actionable engine types only |
| OpenAPI `SetupType` | no `FAILED_BREAKDOWN_RECLAIM` | added; description states the research and unsupported statuses; `TREND_CONTINUATION` stays in the enum only because stored rows may carry it |
| Frontend `SETUP_TYPE` | sweep and failed-breakdown fell back to `range-bound`, a misleading label | each shown as itself (labels "Liquidity Sweep Reversal", "Failed Breakdown Reclaim") |

Backward compatibility: a client that sent `setup_type=TREND_CONTINUATION` used to get an empty 200 and now gets 422. No such client exists in the repository (the frontend filters the scanner client-side and never sends it). Clients that read stored rows still see the identifier.

## 3. Tests

- `contracts/scripts/test_check_strategy_registry.py`: the repository is consistent; unsupported types are absent from every validator; `FAILED_BREAKDOWN_RECLAIM` is in every layer; drift in a validator is detected.
- `ScannerTest::test_setup_type_filter_follows_the_strategy_registry` and `TradePlanTest` (rejection of `TREND_CONTINUATION`, legacy and informational types).
- `scanner.test.ts` (each engine type maps to itself; an unknown type still falls back safely).

## 4. Open items

- The database `setup_type` CHECK constraints (`detected_setups`, `backtest_trades`) do not list `FAILED_BREAKDOWN_RECLAIM`. Not needed while the type is research-only and nothing stores it; a migration is a gate before any ruleset that enables it can be live.
- `TREND_CONTINUATION` remains in the database CHECK and OpenAPI enum for immutable rows; removing it needs a migration and is not worth it.
- The frontend filter dropdowns list every key of `SETUP_TYPES` (`lib/labels.ts`), including demo-only types the engine never emits (`pullback-to-support`, `range-breakout`, `breakdown-retest`, `trend-continuation`, `range-bound`). The scanner filters client-side, so a choice of one of those shows an empty table rather than an error. Narrowing the dropdowns to the registry is a UI change left for the frontend phase; no backend strategy catalogue endpoint exists.
