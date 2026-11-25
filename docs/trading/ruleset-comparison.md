# Ruleset Comparison and Selection

| Item | Value |
|---|---|
| Status | Implemented (Phase 1 P2, 2026-11-23) |
| Rulesets on disk | `pa-core 0.1.0` (retired), `pa-intraday 0.1.0` (live), `0.2.0`, `0.3.0`, `0.4.0`, `0.5.0` (research) |
| Code | `python-engine/app/rulesets.py` (roles, `diff_rulesets`), `RulesetParams.content_hash` |

## 1. Differences, exactly

All four `pa-intraday` files share 41 identical parameters. Only these keys differ (verified by `test_documented_differences_between_pa_intraday_versions_are_exactly_these`):

| Key | 0.1.0 | 0.2.0 | 0.3.0 | 0.4.0 |
|---|---|---|---|---|
| `setup.liquidity_sweep_enabled` | absent (off) | true | true | true |
| `exit.structure_exit_enabled` | true | true | **false** | **false** |
| `setup.failed_breakout_enabled` | absent (off) | absent | absent | true |
| `setup.failed_break_max_bars` | absent | absent | absent | 6 |

Behavioural meaning:

| Version | Strategies that can fire | Structure exit | Intended use |
|---|---|---|---|
| 0.1.0 | ORB, PDH break, breakout-retest (PDL break informational) | on | Live scanner, paper trading, the baseline backtest |
| 0.2.0 | 0.1.0 + liquidity sweep | on | Exploration |
| 0.3.0 | same as 0.2.0 | off | Strategy 01 isolated research (single-strategy runs) |
| 0.4.0 | 0.3.0 + failed breakdown reclaim | off | Strategy 02 isolated research |

Because `0.3.0` and `0.4.0` switch the structure exit off, **their results are not comparable with `0.1.0` results** even for the same strategy, and the exit differences are not only a strategy difference. Account limits are also lifted in the single-strategy run mode (`strategy_run.py`), so a research backtest differs from the live system in sizing as well as exits.

`pa-intraday 0.6.0` (OD-8 Step 2, 2026-11-25, RESEARCH) is `0.5.0` with `exit.structure_exit_enabled` false and the six `orb.*` keys of the ORB B0 reference configuration; only the `orb_b0` strategy reads them ([changelog](../../python-engine/rulesets/CHANGELOG.md)).

`pa-intraday 0.5.0` (DEC-024 D-2, 2026-11-23) is `0.1.0` minus `score.min_display`, `setup.rejection_min_wick_ratio` and `zone.max_width_pct`. Strategies, exits and every value are identical to `0.1.0` and its analysis output is equal (tested); it exists so the dormant keys are retired without touching a released file. Role RESEARCH: promotion to LIVE needs independent strategy validation, out-of-sample evidence, paper-trading evidence, risk and execution validation, and a separate owner approval with an ADR. A test pins the hash of every released file.

## 2. Explicit selection

| Context | How the ruleset is chosen | Guard |
|---|---|---|
| Live scanner, analysis, positions, risk (`/internal/v1`) | `ACTIVE_RULESET` (default `pa-intraday@0.1.0`); a request may name another **live** version | `ruleset_for` returns 422 `RULESET_NOT_LIVE` for any research or retired ruleset, as the active setting or as a request value; 422 `UNKNOWN_RULESET_VERSION` for an unknown one |
| Paper trading | Same as live (the paper book is a Laravel concept on the live engine) | Same guard |
| Backtests and research scripts | `--ruleset code@version` (required for chunked runs; defaults in `scan.py` and `run_screen.py` are visible in the script) | Any role is allowed; the version is recorded |

Every ruleset file must have a role in `RULESET_ROLES` (`LIVE`, `RESEARCH`, `RETIRED`); `test_every_ruleset_on_disk_has_an_explicit_role` fails otherwise, so a new version can never become live by being dropped in a directory. Promoting a version to `LIVE` is a code change reviewed with its ADR.

`pa-intraday 0.4.0` must not become live before the schema and API enum accept `FAILED_BREAKDOWN_RECLAIM` ([api-strategy-contract](../architecture/api-strategy-contract.md) §4).

## 3. Recording the version

| Output | Records |
|---|---|
| Every API response (scan, analysis, positions, risk) | `ruleset_version` = `"<code> <version>"` (existing) |
| Backtest `RunRecord` and report header | `ruleset`, `ruleset_hash` and the slippage model (id and per-type values) (SHA-256 of the exact values, same canonical form as the seeder and `check_ruleset_hash.py`) |
| Chunked runs | `ruleset` is part of the chunk meta and chunks with different rulesets refuse to merge |
| Decision records | `ruleset` and `ruleset_hash` per record ([rule-evaluation-logging](rule-evaluation-logging.md)) |

## 4. Comparing

`diff_rulesets(a, b)` returns `{key: (value_in_a, value_in_b)}` for every differing key (`"<absent>"` for a missing key). A comparison report should print it next to the two hashes.

## 5. Not merged, and why

The rulesets were not merged into one configuration: each difference is a deliberate research setting (a strategy switch or an exit toggle) and merging would silently change `0.1.0` behaviour. **D-1 approved 2026-11-23:** `pa-intraday 0.1.0` is the canonical live ruleset and research rulesets stay separate. The new version created for D-2 (`0.5.0`) is RESEARCH and not live; the promotion conditions are above.
