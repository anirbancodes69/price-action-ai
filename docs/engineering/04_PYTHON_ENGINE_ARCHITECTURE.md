# Python Engine Architecture

| Field | Value |
|---|---|
| Document ID | ENG-04 |
| Version | 0.1.0 |
| Status | Specification ready (not implemented) |
| Owner | Trading Engine Lead |
| Last updated | 2026-11-15 |
| Related | [Trading specs TRD-01..08](../trading/01_TRADING_METHODOLOGY.md) · [ARC-08 §5 Internal API](../architecture/08_INTEGRATION_ARCHITECTURE.md#5-internal-engine-api-laravel--engine) · [ARC-07](../architecture/07_AI_AND_LLM_ARCHITECTURE.md) · [ADR-003](../adr/ADR-003-PYTHON-QUANTITATIVE-ENGINE.md) · [ADR-008](../adr/ADR-008-DETERMINISTIC-TRADING-ENGINE.md) |

## 1. Purpose

Defines the structure of the `python-engine` codebase: the pure domain library, the FastAPI internal service, the arq workers, ruleset handling, schemas and testing boundaries.

## 2. Layout

```
python-engine/
  pyproject.toml, uv.lock
  app/
    domain/                 # PURE: no I/O, no clock, no randomness, no DB, no network
      types.py              # Candle arrays, SwingPoint, Zone, Setup, ... (frozen dataclasses)
      params.py             # RulesetParams (validated from ruleset JSON)
      candles.py            # validation, adjustment application, canonical serialisation + hash
      pivots.py             # TRD-02 §3
      structure.py          # TRD-02 §4–8 state machine, events
      zones.py              # TRD-03
      liquidity.py          # TRD-03 §6, TRD-04 §7 sweeps
      setups/               # breakout_retest.py, support_rejection.py, trend_pullback.py, liquidity_sweep.py
      levels.py             # target ladder, rounding
      scoring.py            # PAQS
      signal.py             # primary setup + signal mapping
      evidence.py           # deterministic evidence templates
      risk.py               # TRD-05 (Decimal)
      execution.py          # TRD-05 §7 gap rules, TRD-06 §4 exits, costs
      analyse.py            # analyse(snapshot, params) -> AnalysisResult (orchestrates the above)
    backtest/               # bar replay, portfolio simulation, metrics (uses domain only)
    paper/                  # EOD paper processing (uses domain.execution)
    explain/                # LLM context builder, prompts/, provider adapters, validator, fallback
    providers/              # MarketDataProvider interface; demo/, kite/
    ingestion/              # jobs: instrument sync, daily, backfill; quality checks
    db/                     # SQLAlchemy Core tables (read model of Laravel schema; tables.py, T-104), repositories (tenant_id mandatory)
    api/                    # FastAPI app: routers for /internal/v1/*, auth dependency (service token)
    workers/                # arq WorkerSettings, job functions, queues: ingest, analysis, backtest, paper, ai
    schemas/                # Pydantic request/response models → exported to contracts/engine/
    settings.py             # pydantic-settings
    logging.py              # structlog JSON, redaction processors
  tests/
    trading/                # TRD-08 catalogue (TV-*)
    fixtures/candles/*.csv, golden/*.json
    unit/, integration/ (DB + Redis), contract/
```

## 3. Domain library rules

| ID | Rule | Enforcement |
|---|---|---|
| PE-01 | `app/domain` imports only stdlib, numpy and `app.domain.*`. | import-linter contract in CI |
| PE-02 | Functions are pure: same inputs ⇒ same outputs; no global mutable state. | Determinism tests (TV-NLA-04), code review |
| PE-03 | Every derived object carries `index` and `confirmed_at_index`. | Types require the fields |
| PE-04 | Candle access in replay goes through an accessor that forbids reading beyond the current bar (raises `LookAheadError`). | TV-NLA-03 |
| PE-05 | Money/price arithmetic in `risk.py`/`execution.py` uses `Decimal` with explicit quantisation. | Unit tests, mypy types |
| PE-06 | Parameters only via `RulesetParams`; no hard-coded thresholds in rule code. | Grep check for numeric literals in `setups/` (allow-list) |
| PE-07 | Output serialisation is canonical (sorted keys, fixed decimal strings) so `result_hash` is stable. | Golden tests |

## 4. Core function signatures

```python
def analyse(snapshot: CandleSnapshot, params: RulesetParams) -> AnalysisResult: ...
def detect_pivots(c: CandleArrays, left: int, right: int) -> list[SwingPoint]: ...
def run_structure(c: CandleArrays, pivots: list[SwingPoint], p: RulesetParams) -> StructureResult: ...
def build_zones(c: CandleArrays, pivots: list[SwingPoint], t: int, p: RulesetParams) -> list[Zone]: ...
def detect_setups(ctx: AnalysisContext, p: RulesetParams) -> list[Setup]: ...
def position_size(inp: RiskInput, p: RulesetParams) -> RiskResult: ...
def simulate_fill(open_price: Decimal, plan: PlanLevels, p: RulesetParams, ...) -> FillResult: ...
def simulate_exit(bar: Bar, position: OpenPosition, ...) -> ExitResult | None: ...
```

`AnalysisResult` fields map 1:1 to `analysis_runs` + child tables (ARC-03 §7).

## 5. Ruleset versioning

- Rulesets are seeded rows in `ruleset_versions` (ARC-03 §7.1) **and** a JSON file in `python-engine/rulesets/pa-core/0.1.0.json`; CI checks they are identical (hash). *Status (T-105):* `python-engine/rulesets/pa-core/0.1.0.json` exists, the seeded row comes from the byte-identical `backend/database/seeders/data/pa-core-0.1.0.json`, and `contracts/scripts/check_ruleset_hash.py` (in `contracts-ci.yml`) checks both against each other and against TRD-01 §6. `RulesetParams` (`app/domain/params.py`) is not built yet (M3). History: `python-engine/rulesets/CHANGELOG.md`.
- The engine loads the active ruleset at startup and caches by id; requests may pin a version (backtests, reproductions).
- Any change to rule code that alters golden outputs requires a new ruleset version (or patch version when fixing a bug with an explicit changelog entry in `rulesets/CHANGELOG.md`).
- `engine_version` (package version) is recorded separately.

## 6. FastAPI service

- Internal only; bound to the Docker network; `Authorization: Bearer` service token dependency on all routes except `/health`.
- Sync endpoints (`/analyse`, `/risk/*`) run domain functions in a thread pool with timeouts.
- Validation errors return 422 with Pydantic details (Laravel treats as contract errors).

## 7. Workers (arq)

| Queue | Concurrency (default) | Jobs |
|---|---|---|
| `ingest` | 2 | `instrument_sync`, `ingest_daily`, `backfill` |
| `analysis` | CPU count | `analyse_batch` (fan-out per instrument in-process) |
| `paper` | 1 | `paper_eod(data_source, trade_date)` |
| `backtest` | 1 | `run_backtest(run_id)` (checkpoints progress) |
| `ai` | 2 | `explain(request)` |

Jobs are idempotent (keys: run ids, `(data_source, trade_date)`), retried with backoff for transient errors, and emit events to Laravel on completion.

## 8. Input/output schemas

Pydantic models in `app/schemas/` are the source of the engine contract (implemented in M1, T-104: 13 models in `EXPORTED_MODELS`: analyse, risk sizing and level validation, jobs, explanations, engine events, the JIT provider token); `scripts/export_engine_schemas.py` writes JSON Schema to `contracts/engine/`. CI fails if the exported files are stale (`python-engine-ci` runs `--check`; `make export-schemas` regenerates them). The contract is validation-mode JSON Schema, one file per model, `additionalProperties: false`; money and prices are decimal strings.

`app/db/tables.py` lists the 34 tables the engine reads or writes (32 in M1, plus `candle_revisions` and `analysis_run_inputs` from the intraday migration) (the `app_engine` grants) with column names, types, nullability and primary keys, and no constraints, defaults or foreign keys (the database enforces those). `tests/integration/test_schema_diff.py` compares it with a database migrated by Laravel and fails on any difference; CI sets `REQUIRE_SCHEMA_DIFF=1` so the test cannot silently skip. When a migration changes one of these tables, update `tables.py` in the same PR.

## 9. Testing boundaries

| Layer | Test type | Dependencies |
|---|---|---|
| `domain/` | Unit, property-based, golden, TRD-08 catalogue | none |
| `backtest/`, `paper/` | Unit with in-memory candles; TV-GAP/COL/UNI | none |
| `providers/` | Recorded HTTP fixtures (respx); no live calls in CI | none |
| `db/`, `workers/` | Integration | PostgreSQL + Redis service containers |
| `api/` | FastAPI TestClient + contract tests | DB optional (mocked repositories) |
| `explain/` | Validator unit tests; stubbed provider | none |

Quality gates: Ruff lint + format check, mypy (strict on `domain/`, gradual elsewhere), pytest. See [ENG-07](07_TESTING_STRATEGY.md).
