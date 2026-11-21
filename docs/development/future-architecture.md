# Future Architecture: Independent Strategies and the Adaptive Engine

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Status | **Proposal / target design.** Not built and not scheduled. Nothing here changes the current system |
| Date | 2026-11-21 |
| Related | [ADR-018](../adr/ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md) · [ARC-01](../architecture/01_SYSTEM_ARCHITECTURE.md) · [ENG-04](../engineering/04_PYTHON_ENGINE_ARCHITECTURE.md) · [Roadmap](strategy-development-roadmap.md) |

**Boundary.** The adaptive engine, the confluence engine and any strategy combination are **not** built now. They start only after the individual strategy library has completed independent validation, and are researched separately ([standards §6](../research/independent-backtesting-standards.md#6-future-combination-research)).

## 1. Intended layers

```
 1 Market Data Layer              provider abstraction, candles, calendar, instruments       (exists)
 2 Structure and Feature Analysis swings, structure events, zones, session levels            (exists, neutral)
 3 Independent Strategy Engines   one module per strategy; emit candidates                   (library, in progress)
 4 Market Regime Classification   price-action features only                                 (future)
 5 Adaptive Strategy Selection    enables or disables strategies per regime                  (future)
 6 Signal and Confluence Engine   combines candidates; de-duplicates correlated evidence     (future)
 7 Risk Management Engine         sizing, limits, costs; independent of selection            (exists)
 8 Execution / Recommendation     plan creation for manual execution (ADR-010)               (exists, long-only)
 9 Monitoring and Analytics       trade monitor, journal, performance, per-strategy reports  (partly exists)
```

Layers 1, 2, 7, 8 and part of 9 exist in `python-engine/app/` and `backend/`. Layers 4 to 6 do not. Layer 3 exists only as four detectors that share a selector and a score (see below).

## 2. Principles

1. Each strategy is independently executable and testable, with its own ruleset version and identifier.
2. Each strategy emits **standardised trade candidates** ([process §2.2](strategy-development-process.md#22-candidate-output)). A candidate carries no cross-strategy score.
3. Strategies are not coupled: no strategy imports another strategy's rules.
4. **Confirmation modules are distinct from strategies.** A module that only adds evidence to someone else's trade (for example a context filter) is not a strategy and is never backtested as one.
5. Correlated confirmations must not be double-counted. Two strategies built on the same BOS are one piece of evidence, not two. Any confluence design must state how correlation is handled.
6. The adaptive layer selects or disables strategies **without modifying their implementations**.
7. Risk management does not depend on which strategy produced a candidate. It consumes candidates and applies the same limits (TRD-05).
8. Regime classification uses price action only (TRD-01 MP-01) unless the methodology is changed by ADR.
9. The LLM only explains (ADR-009). It never selects strategies or changes levels.

## 3. Gap between today's engine and the target

Verified in code on 2026-11-21. These are the places where isolation does not yet hold; they are what the single-strategy run mode and the later extraction must address. They are **not** changed by this documentation task.

| Current mechanism | Location | Why it blocks isolation |
|---|---|---|
| All detectors run in one `analyse()` call | `app/domain/analyse.py` | A strategy cannot be run alone without a different entry point |
| One primary setup per symbol is chosen by status, score and type order | `app/domain/setups/signal.py` (`choose_signal`, `_priority`) | One strategy's setup can suppress another's |
| A score threshold turns a setup into `NO_TRADE` (`LOW_SCORE`) | `signal.py`, `score.watch_threshold`; `setups/scoring.py` | The score mixes confluence items (zone, 15m context, setup-specific checklists) into the decision |
| 15m context filter inside each setup (SD-05) | `setups/common.py` (`htf_against`, `end_of_life`) | Structure context decides which setups survive; must be a declared per-strategy rule |
| Shared stop and target ladder with setup-specific branches | `app/domain/levels.py` (`trade_levels`) | Targets can borrow levels (PDH, session high, zones, 15m swings) that are another concept's output |
| Replay exits on a bearish 5m CHoCH | `app/backtest/replay.py`; `exit.structure_exit_enabled` | A structure-based exit is applied to every strategy |
| Slot-limited, score-ordered allocation | `app/backtest/replay.py` (order sorted by PAQS then symbol) | Which trades exist depends on other strategies' signals and on alphabetical order |
| Long-only risk and exits | `app/domain/risk/request.py`, `exits.py`, `fill.py`; `replay.py` | Shorts cannot be executed or backtested |

## 4. Migration outline (when the time comes)

1. Each strategy is validated in isolation first (the library).
2. A common candidate interface is extracted only if the validated strategies need it.
3. The regime classifier and selector are added as separate modules that read candidates and switch strategies on or off.
4. Combined and adaptive results are measured against the individual baselines on identical data, costs, risk assumptions and periods. They are reported separately and never overwrite the baselines.

Every step needs its own specification and, where it changes a decision, an ADR.
