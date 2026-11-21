# Strategy Development Process

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Status | Current ([ADR-018](../adr/ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md)) |
| Date | 2026-11-21 |
| Related | [Roadmap and tracker](strategy-development-roadmap.md) · [Independent backtesting standards](../research/independent-backtesting-standards.md) · [Validation criteria](../research/validation-criteria.md) · [Strategy template](../strategies/STRATEGY_TEMPLATE.md) |

This document is the repeatable procedure for every strategy in the library. A new Claude Code session needs only this file, the roadmap and the strategy's own page to continue the work.

## 1. Rules that apply to every strategy

1. **One strategy per task.** Never implement or validate two strategies in one task.
2. **Isolation.** A strategy never depends on another strategy for its signals, confirmation, filtering, ranking or exits. Details: [standards §2](../research/independent-backtesting-standards.md#2-isolation-rules).
3. **Specification before code.** No implementation starts before the specification is approved by the owner.
4. **Evidence before status.** A status changes only when the evidence named in §3 exists in the repository. Code existence alone moves nothing past `IMPLEMENTED`.
5. **No silent skipping.** A poorly performing strategy gets a recorded decision, not a quiet omission.
6. **No new data-snooping.** Never tune against the final out-of-sample or holdout segment. Every variant is logged in the [experiment registry](../research/experiment-registry.md).
7. **Production behaviour is protected.** A strategy task may add code, tests and a ruleset version. It must not change the behaviour of other strategies, the risk rules or the live scanner without a separate decision (CLAUDE.md §4, §8).
8. **Methodology.** Pure price action ([TRD-01 MP-01](../trading/01_TRADING_METHODOLOGY.md)). No indicators, including VWAP, until the owner changes the methodology through an ADR.

## 2. Lifecycle

| Stage | Output | Gate to the next stage |
|---|---|---|
| 1. Research and specification | The strategy page filled from the [template](../strategies/STRATEGY_TEMPLATE.md), plus the TRD update that makes it authoritative | Owner approves the specification (`SPECIFICATION_APPROVED`) |
| 2. Independent implementation | Code under `python-engine/app/domain/`, a strategy-specific ruleset version, a single-strategy run mode | Implementation matches the approved specification; ruff and mypy clean |
| 3. Functional testing | Automated tests (§4) | All critical tests pass |
| 4. Independent backtest | Two experiments: trade-level quality, then the risk and position-sizing model ([standards §4](../research/independent-backtesting-standards.md#4-the-two-experiments)) | Results recorded in the registry with configuration, commit, data range, exclusions |
| 5. Robustness validation | IS, OOS, walk-forward, regime, sensitivity, cost and selection-bias analysis ([criteria](../research/validation-criteria.md)) | Criteria evaluated against the approved thresholds |
| 6. Acceptance decision | An explicit status and a written rationale | Owner reviews before the next strategy starts |

Specification detail (Stage 1) must be precise enough to test: every condition is a comparison on named bars and parameters. Phrases such as "strong rejection" or "clear trend" are not rules until they are defined.

### 2.1 Strategy interface

Follow the existing project conventions rather than adding an abstraction for its own sake. Conceptually each strategy exposes the following, and the specification states how each maps to the code:

| Concept | Meaning | Existing counterpart (verified 2026-11-21) |
|---|---|---|
| `evaluate()` | Strategy-only detection over closed bars up to *t*, returning candidates | `detect_*` functions in `app/domain/setups/` returning `list[Setup]` |
| `validate()` | Is the candidate still valid at *t* (not invalidated, not expired, before the cutoff) | The lifecycle in `setups/common.py` (`end_of_life`, `replay_simple`) |
| `get_entry()` | Entry reference and trigger | `entry_reference()` in `app/domain/levels.py` |
| `get_exit()` | Stop and target | `trade_levels()` in `levels.py`; exits in `risk/exits.py` |
| `get_invalidation()` | What cancels the setup | End reasons such as `SWEEP_FAILED`, `FAILED_BREAKOUT` |
| `get_metadata()` | Strategy id, ruleset version, parameters, direction support | `Setup` fields and the ruleset registry |

Today's `trade_levels()` is shared by all setups (it contains setup-specific branches). A strategy specification must say which of its stop, target and exit rules are its own and which are shared infrastructure.

### 2.2 Candidate output

Each strategy emits standardised candidates (symbol, direction, setup time, entry reference, stop, target, invalidation level, strategy id, ruleset version, reasons). Candidates carry no cross-strategy score. This is what a future adaptive engine consumes ([future architecture](future-architecture.md)).

## 3. Statuses and acceptance criteria

The statuses are not a single completion flag. The [tracker](strategy-development-roadmap.md#5-master-strategy-tracker) shows each stage separately; the acceptance status is the furthest state with evidence.

| Status | Meaning | Evidence required to enter it |
|---|---|---|
| `NOT_STARTED` | No specification work has begun | n/a |
| `SPECIFICATION_IN_PROGRESS` | A draft exists or is being written | The strategy page exists with draft sections |
| `SPECIFICATION_APPROVED` | The owner approved the rules | Page sections 1-16 complete, no unresolved `OQ-*` that changes a rule, owner approval recorded in the page and tracker |
| `IMPLEMENTATION_IN_PROGRESS` | Code is being written against the approved specification | Branch or PR open |
| `IMPLEMENTED` | The code exists on `main` and matches the specification | Merged PR; page §17 filled; ruff and mypy clean |
| `FUNCTIONAL_TESTING` | The Stage 3 test set is being completed or run | Test plan listed in page §18 |
| `BACKTESTING` | Functional tests pass and independent experiments are in progress or complete without a decision | All critical tests green; at least one registry entry with `strategy_id` |
| `NEEDS_IMPROVEMENT` | Results are inconclusive or fixable weaknesses were identified | Failure analysis with root cause and a justified change proposal |
| `VALIDATION_FAILED` | The criteria were evaluated and not met | Completed evaluation with the failing criteria named; previous results preserved |
| `RESEARCH_VALIDATED` | The research criteria are met on out-of-sample and walk-forward data, with data limitations recorded | [Validation criteria](../research/validation-criteria.md) §3 met; report in the registry; owner sign-off |
| `PAPER_TRADING_READY` | Also eligible for forward paper logging | Criteria §4 met (bias flags cleared or accepted by the owner, verified costs, short history flag cleared) |
| `DEFERRED` | Parked by a decision | The decision and its reason are recorded |

Transitions out of `VALIDATION_FAILED` and `NEEDS_IMPROVEMENT` follow §6.

## 4. Functional testing standard (Stage 3)

Tests live beside the existing trading tests (`python-engine/tests/trading/`) and use the same bar builders. Each strategy needs automated tests for all of the following, or an explicit note that one does not apply:

| Area | Required tests |
|---|---|
| Setups | Valid setups; invalid setups; the bullish and, where supported, bearish form |
| Levels | Entry, stop and target calculations; tick rounding; minimum and maximum stop distance |
| Lifecycle | Invalidation, expiry, entry cutoff, duplicate signal prevention (one per anchor) |
| Data | Missing candles; data gaps; market (opening) gaps; session boundaries |
| Boundaries | Exact-threshold cases at, just above and just below each parameter |
| Look-ahead | A setup found at bar *k* is identical when the data after *k* is removed (the sweep tests are the model: `tests/trading/test_setups_sweep.py`) |
| Replay | A bar-by-bar replay gives the same signals as a fresh run at each bar |
| Isolation | The strategy's candidates are unchanged when every other strategy is disabled ([standards §3](../research/independent-backtesting-standards.md#3-single-strategy-run-mode)) |

Do not proceed to historical performance work while a critical functional test fails. TRD-08 test vectors (`TV-*`) are added for each new rule.

## 5. Acceptance checklist

Copy into the strategy page §27 and tick only with evidence (link or command output).

- [ ] Specification approved by the owner (date recorded)
- [ ] Implementation merged; no change to other strategies' outputs (isolation tests green)
- [ ] Functional tests pass; look-ahead and replay tests included
- [ ] ruff, mypy and the engine test suite pass
- [ ] Single-strategy run mode verified (no other detector, no cross-strategy ranking or filter)
- [ ] Trade-level experiment recorded in the registry
- [ ] Risk-model experiment recorded, same costs and data
- [ ] Data limitations and exclusions recorded for each run
- [ ] In-sample, out-of-sample and walk-forward reports present
- [ ] Parameter, regime, cost and period sensitivity recorded
- [ ] Gross and net results compared; selection bias and overfitting discussed
- [ ] Every variant tried is in the registry
- [ ] Decision recorded with rationale; tracker, CURRENT.md and TASKS.md updated
- [ ] Owner has reviewed the results

## 6. When validation fails

1. Document the failure and which criteria failed.
2. Identify the root cause (entry quality, exits, costs, data, regime dependence, sample size).
3. Propose improvements with a hypothesis for each.
4. Apply only justified changes, as a new strategy ruleset version.
5. Re-test using data that was **not** used to choose the change (new periods, or the forward log).
6. Preserve all previous results in the registry.
7. Record the final decision (`NEEDS_IMPROVEMENT`, `VALIDATION_FAILED` or `RESEARCH_VALIDATED`).

Do not keep optimising on the same in-sample data. A limit of improvement rounds per strategy is proposed in [validation criteria §5](../research/validation-criteria.md#5-improvement-rounds).

## 7. Sequential rule

Strategy *n+1* does not start until strategy *n* has a recorded decision, its outstanding blockers have been reviewed, and the owner has approved moving on. The starting task for the library is [Strategy 01](../strategies/liquidity-sweep-reversal.md).

## 8. Updating documentation

At the end of every strategy task, apply CLAUDE.md §7 and §9 and also update: the tracker, the strategy page, the [experiment registry](../research/experiment-registry.md), CURRENT.md, TASKS.md, and (if rules changed) the TRD documents and the ruleset version.
