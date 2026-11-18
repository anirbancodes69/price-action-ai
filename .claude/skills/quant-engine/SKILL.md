---
name: quant-engine
description: Implementation and review workflow for the PriceAction AI deterministic quant engine in python-engine/ - domain functions (pivots, structure, zones, setups, levels, scoring, risk sizing, execution), ruleset versions (pa-core), candle snapshots and result hashes, TRD-08 test vectors, golden and property-based tests, backtest replay and EOD paper-trade simulation. Use when writing, changing, reviewing or debugging code under python-engine/app/domain, app/backtest, app/paper, python-engine/rulesets or python-engine/tests/trading, or when a change could alter analysis output.
---

# Quant engine

Workflow for building the trading engine so that its output is deterministic, reproducible and free of look-ahead. **What** the rules are is owned by `docs/trading/` (see the `price-action-domain` skill). **How** the code is laid out and tested is owned by [ENG-04](../../../docs/engineering/04_PYTHON_ENGINE_ARCHITECTURE.md). This skill applies both.

> Current state: `python-engine/app/domain/` has types, `RulesetParams`, pivots, structure, alignment, session levels, zones, equal-level pools, the long intraday setups, levels, PAQS, signal mapping, `analyse` and intraday risk (`risk/`: sizing, account limits, fills, exits). The backtester library (`app/backtest`: replay, costs, metrics, splits, run record) exists; the API and persistence come next.

## Required context

1. CURRENT.md, then the milestone in [ENG-01](../../../docs/engineering/01_IMPLEMENTATION_ROADMAP.md) (scope, files, exit criteria).
2. [ENG-04](../../../docs/engineering/04_PYTHON_ENGINE_ARCHITECTURE.md) §2 layout, §3 rules PE-01..PE-07, §4 signatures, §5 ruleset versioning, §9 test boundaries.
3. The TRD section(s) for the rule being implemented ([rule map](../price-action-domain/references/rule-map.md)) and its test IDs in [TRD-08 §3](../../../docs/trading/08_TRADING_ENGINE_VALIDATION.md#3-mandatory-test-catalogue).
4. [ADR-008](../../../docs/adr/ADR-008-DETERMINISTIC-TRADING-ENGINE.md). For backtest or paper work, also read [references/backtest-and-paper.md](references/backtest-and-paper.md).

## Workflow

1. **Tests first, from the spec.** For each rule, write the TRD-08 vectors as hand-built CSV fixtures with hand-computed expected outputs (TV-R1). Include below/at/above boundary cases for every threshold (TV-R2). Cite the spec in each docstring, e.g. `"""TRD-02 §3.4"""` (TV-R5). Never derive expected values by running the code under test.
2. **Implement as pure functions** in `app/domain/` with the ENG-04 §4 signatures.
3. **Wire parameters** only through `RulesetParams`, loaded from `python-engine/rulesets/<code>/<version>.json` (active: `pa-intraday`). That JSON must stay hash-identical to the seeded `ruleset_versions` row.
4. **Add invariant tests:** a property-based test for no look-ahead (a fresh run on the series truncated at `t` equals the incremental state at `t`), determinism (same input gives byte-identical canonical output and `result_hash`), and rounding direction.
5. **Golden outputs.** If golden JSON changes, that is an output change: bump the ruleset version (or the patch version for a documented bug fix in `rulesets/CHANGELOG.md`), update the TRD docs, and record why.
6. **Run quality gates** (`quality-gate` skill): ruff, ruff format, mypy (strict on `domain/`), pytest.

## Hard rules

| Rule | Source |
|---|---|
| `app/domain` imports only stdlib, numpy and `app.domain.*`. No I/O, clock, randomness, DB, network or LLM | PE-01, MP-06 |
| Pure functions with no global mutable state | PE-02 |
| Every derived object carries `index` and `confirmed_at_index`. Evaluation at `t` uses only objects with `confirmed_at_index ≤ t` | PE-03, MP-04 |
| Replay reads candles through an accessor that raises `LookAheadError` beyond the current bar | PE-04 |
| Money and price arithmetic uses `Decimal` with explicit quantisation and the TRD-01 §5 rounding directions | PE-05 |
| No numeric literals as thresholds in rule code. Values come from `RulesetParams` | PE-06 |
| Canonical serialisation (sorted keys, fixed decimal strings) so `result_hash` is stable | PE-07 |
| Analysis consumes an **immutable candle snapshot** and records snapshot id, ruleset version and engine version. Never read live candle tables inside a domain function | C-08, ARC-03 §7.2 |
| Only closed bars (5m primary, 15m and daily context, higher-timeframe bars only once closed: TRD-01 MP-03, MP-10). Reject invalid snapshots (`INVALID_INPUT`) and short ones (`INSUFFICIENT_HISTORY` → `NO_TRADE`) | TRD-01 §4 |
| Backtests and paper trading call the **same** domain functions as live analysis. No re-implementation | TRD-06 BT-03 |
| Risk sizing is per user at plan time, not part of the shared analysis run | TRD-01 §3 |
| The engine writes only the tables ARC-01 §6 lists for it | ARC-01 §6 |

## Review checklist (use when reviewing engine PRs)

- [ ] Every new rule has its TRD-08 vectors with hand-computed expectations and boundary cases.
- [ ] No look-ahead path: grep for indexing like `c[t+1]` or `[i + k]` outside pivot right-side checks, and for slicing beyond `t`.
- [ ] No wall-clock (`datetime.now`, `date.today`), `random` or environment reads in `domain/`.
- [ ] No float arithmetic on money; quantisation is explicit.
- [ ] Parameters come from `RulesetParams` only.
- [ ] Golden diffs are explained, and the ruleset version is bumped if output changed.
- [ ] SHORT setups stay informational. NO_TRADE paths are tested.

## Deliverables

- Code plus tests (vectors, properties, golden) and real test output.
- The ruleset version and `rulesets/CHANGELOG.md` entry, if outputs changed.
- TRD and ENG-04 updates when behaviour or structure changed, then the `docs-sync` skill.
