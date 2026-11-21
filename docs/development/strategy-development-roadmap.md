# Strategy Development Roadmap and Master Tracker

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Status | Current, approved 2026-11-21 ([ADR-018](../adr/ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md)) |
| Last verified | 2026-11-21 against `main` at `967da8e` |
| Related | [Process](strategy-development-process.md) · [Strategy pages](../strategies/README.md) · [Research index](../research/README.md) · [Future architecture](future-architecture.md) |

## 1. Official sequence

The order is fixed. It changes only for a documented technical dependency and with owner approval.

| # | Strategy | Starting position (verified) |
|---|---|---|
| 01 | [Liquidity Sweep / Reversal](../strategies/liquidity-sweep-reversal.md) | Implemented (long), requires validation |
| 02 | [Failed Breakout](../strategies/failed-breakout.md) | Partially detected, requires independent implementation |
| 03 | [Trend Following / Pullback](../strategies/trend-following-pullback.md) | Specified, requires implementation |
| 04 | [CHoCH Reversal](../strategies/choch-reversal.md) | Structure detection exists, requires independent trade setup |
| 05 | [Support & Resistance Reversal](../strategies/support-resistance-reversal.md) | Zone detection exists, requires trade setup |
| 06 | [Supply & Demand Trading](../strategies/supply-demand.md) | Zone engine exists, requires trade setup |
| 07 | [Range Trading / Mean Reversion](../strategies/range-trading.md) | Range classification exists, requires trade setup |
| 08 | [BOS Trading](../strategies/bos-trading.md) | Structure detection exists, requires independent trade setup |
| 09 | [Opening Range Breakout](../strategies/opening-range-breakout.md) | Long implemented; short side requires completion |
| 10 | [Previous Day High/Low Breakout](../strategies/previous-day-high-low-breakout.md) | Long implemented; short side requires completion |
| 11 | [Breakout & Retest](../strategies/breakout-retest.md) | Long implemented; historical performance requires investigation |
| 12 | [VWAP Pullback](../strategies/vwap-pullback.md) | `DEFERRED` pending methodology approval |

Strategy 01 is the next authorised task. Strategy 02 does not start until Strategy 01 has a recorded decision and the owner has reviewed it.

## 2. Methodology decision: VWAP

The methodology is pure price action ([TRD-01 MP-01](../trading/01_TRADING_METHODOLOGY.md): only OHLCV of confirmed candles, no derived indicators). VWAP is a volume-weighted derived value, so Strategy 12 is `DEFERRED`. It stays on the roadmap. It can start only after the owner approves a methodology change recorded as a superseding ADR or an amended MP-01. No other strategy may use VWAP or any indicator.

## 3. Why this order: dependencies that were checked

The sequence is the owner's. These are the technical dependencies found in the code and specification, recorded so that none of them forces a reorder without a decision.

| Dependency | Affects | Finding |
|---|---|---|
| Reuse of neutral infrastructure only | all | Swings, structure events, zones and levels are shared data. No strategy may import another strategy's trade rules |
| Strategy 03 vs 08 | 03, 08 | The draft `TREND_CONTINUATION` rule (TRD-04 §6) starts from a 5m BOS. BOS Trading (08) must therefore be specified as its own rule set, not as a part of 03, or the two will not be independent |
| Strategy 04 vs 08 | 04, 08 | Both are built on `StructureResult.events` (CHoCH and BOS). Each needs its own entry, stop and invalidation rules |
| Strategy 05 vs 06 | 05, 06 | The only zone engine is a swing-pivot cluster support/resistance builder (`zone_build.py`). No supply/demand (base and impulse) definition exists in the specification. 06 needs a definition that differs from 05, or it is the same strategy |
| Strategy 07 | 07 | "Range classification" today is only the structure state `SIDEWAYS` (`structure.py`, TRD-02 §5.2). There is no range box, boundary or mean-reversion rule. OQ-SD-01 (a separate range type) is open |
| Strategies 09-11 shorts | 09, 10, 11 | Short setups are built for 09 and 10 but never executable (§6). 11 has no short mirror at all |
| Strategies 02, 11 | 02, 11 | `FAILED_BREAKOUT` exists only as an end reason inside Breakout-Retest (`breakout_retest.py`). Strategy 02 needs its own definition and must not reuse that code path as a filter |
| Backtest isolation | all | The engine's shared selection, scoring gate and slot-limited replay change which trades exist ([standards §3](../research/independent-backtesting-standards.md#3-single-strategy-run-mode)). A single-strategy run mode is needed before the first backtest, so it belongs to Strategy 01's task |
| Data limits | all | See [research data limitations](../research/research-data-limitations.md) |

## 4. Status vocabulary

`NOT_STARTED` · `SPECIFICATION_IN_PROGRESS` · `SPECIFICATION_APPROVED` · `IMPLEMENTATION_IN_PROGRESS` · `IMPLEMENTED` · `FUNCTIONAL_TESTING` · `BACKTESTING` · `NEEDS_IMPROVEMENT` · `VALIDATION_FAILED` · `RESEARCH_VALIDATED` · `PAPER_TRADING_READY` · `DEFERRED`. Criteria for each: [process §3](strategy-development-process.md#3-statuses-and-acceptance-criteria).

**IMPLEMENTED ≠ FUNCTIONALLY TESTED ≠ BACKTESTED ≠ ROBUSTNESS VALIDATED ≠ PAPER_TRADING_READY.** The columns below are separate on purpose. A stage reads `NOT_STARTED` unless evidence exists.

## 5. Master strategy tracker

Verified against source and tests on 2026-11-21. "Independent backtest" is `NOT_STARTED` for every strategy: no single-strategy backtest exists, and every earlier run was a combined run ([experiment registry](../research/experiment-registry.md)).

| # | Strategy | Specification | Implementation | Functional tests | Independent backtest | Robustness | Acceptance status | Directions (executable) | Timeframes | Last milestone | Known blockers | Next action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | Liquidity Sweep / Reversal | Approved by the owner 2026-11-21 (P-1..P-4 as written; OQ-SD-08 resolved, OQ-SD-07 left open and outside isolated runs) | Long, merged (T-I141, PR #66) | 13 tests incl. look-ahead; not yet checked against the full Stage 3 list | `NOT_STARTED` | `NOT_STARTED` | `IMPLEMENTED` (spec `SPECIFICATION_APPROVED`; Stage 2 run mode built) | Long | 5m setup; 5m and 15m swing levels; PDL, OR low, zones | 2026-11-21 Stage 2 run mode built | Stage 3 test gaps; real-bar isolation proof; special-session exclusion and 2024 daily bars (D-7); short side unsupported; data limits | [Stage 3 tests (page §18), then the 4a and 4b runs](../strategies/liquidity-sweep-reversal.md) |
| 02 | Failed Breakout | None | None; only the end reason `FAILED_BREAKOUT` inside Breakout-Retest | None | `NOT_STARTED` | `NOT_STARTED` | `NOT_STARTED` | None | Not defined | — | Needs a specification | Wait for Strategy 01 decision |
| 03 | Trend Following / Pullback | Draft: TRD-04 §6 `TREND_CONTINUATION` (long, "after validation"); not approved | None (`SetupType` has no such member) | None | `NOT_STARTED` | `NOT_STARTED` | `SPECIFICATION_IN_PROGRESS` | None | 5m setup, 15m context (draft) | — | Overlap with 08; no short mirror | Wait |
| 04 | CHoCH Reversal | None | CHoCH events detected (`structure.py`); used only for invalidation and exits | None for a setup | `NOT_STARTED` | `NOT_STARTED` | `NOT_STARTED` | None | Not defined | — | Needs a specification | Wait |
| 05 | Support & Resistance Reversal | None; zones specified in TRD-03 | Zone engine (`zone_build.py`, `zone_break.py`, `zone_strength.py`); no reversal setup. The `setup.rejection_min_wick_ratio` parameter is unused | Zone tests only | `NOT_STARTED` | `NOT_STARTED` | `NOT_STARTED` | None | Not defined | — | Needs a specification | Wait |
| 06 | Supply & Demand Trading | None; no supply/demand definition in the TRDs | Only the S/R zone engine | None | `NOT_STARTED` | `NOT_STARTED` | `NOT_STARTED` | None | Not defined | — | Definition distinct from 05 | Wait |
| 07 | Range Trading / Mean Reversion | None (OQ-SD-01 open) | Structure state `SIDEWAYS` only; no range box | None | `NOT_STARTED` | `NOT_STARTED` | `NOT_STARTED` | None | Not defined | — | Needs a range definition | Wait |
| 08 | BOS Trading | None | BOS events detected (`structure.py`); no setup | None for a setup | `NOT_STARTED` | `NOT_STARTED` | `NOT_STARTED` | None | Not defined | — | Independence from 03 | Wait |
| 09 | Opening Range Breakout | TRD-04 §3 | Long merged; short built but informational | In `test_setups_session.py` (11 tests shared with 10); not reviewed against Stage 3 | `NOT_STARTED` (13 trades inside a combined run) | `NOT_STARTED` | `IMPLEMENTED` (long) | Long | 5m, 15m context | — | Short infrastructure; session hours (L-4); PDH is a target candidate (L-5) | Wait |
| 10 | Previous Day High/Low Breakout | TRD-04 §4, §4.1 | Long merged; PDL built but informational | In `test_setups_session.py` (shared with 09) | `NOT_STARTED` (inside combined runs) | `NOT_STARTED` | `IMPLEMENTED` (long) | Long | 5m, 15m context, daily levels | — | Reliable daily PDH/PDL; short infrastructure | Wait |
| 11 | Breakout & Retest | TRD-04 §5 | Long merged; no short mirror | `test_setups_retest.py`, 5 tests | `NOT_STARTED` (130 trades inside a combined run, −0.48R net) | `NOT_STARTED` | `IMPLEMENTED` (long) | Long | 5m, 15m context and zones | — | Combined result not attributable; needs independent investigation | Wait |
| 12 | VWAP Pullback | None | None | None | `NOT_STARTED` | `NOT_STARTED` | `DEFERRED` | None | — | — | Methodology approval (MP-01) | None until approved |

## 6. Decisions and unresolved dependencies

Owner decisions of 2026-11-21 are recorded below. Nothing else is resolved by assumption.

| ID | Item | Decision / state |
|---|---|---|
| D-1 | Roadmap, [ADR-018](../adr/ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md) and the isolation rules | **Approved** by the owner, 2026-11-21 |
| D-2 | Validation thresholds ([criteria](../research/validation-criteria.md)) | **Approved** as written (the TRD-08 §6 starting values, fixed before any result exists). Not to be refined after seeing Strategy 01 results without a recorded decision |
| D-3 | Is `RESEARCH_VALIDATED` allowed on the survivorship-biased universe? | **Recommendation agreed, to be confirmed at Strategy 01 Stage 5:** allowed only if labelled `survivorship_bias_risk` (an upper bound). `PAPER_TRADING_READY` needs the owner's explicit written acceptance of the residual bias |
| D-4 | Short side: research-only short simulation while actionability stays long-only (ADR-014, C-12) | **Deferred.** Needed before Strategies 04, 08, 09, 10. Recommendation agreed in principle: simulate shorts for research only; any change to actionability needs a superseding ADR. Strategy 01 is long-only |
| D-5 | Quality score (PAQS) and 15m context filter (SD-05) in isolated runs | **Approved.** PAQS is excluded from isolated runs. The 15m filter is allowed only when the strategy's specification names it as its own rule |
| D-6 | Verified NIFTY 50 membership history (OQ-BT-01) and charge schedule (OQ-BT-02) | **Deferred.** Membership cannot be fixed now: every result keeps the `survivorship_bias_risk` flag. Verify the cost schedule against Zerodha contract notes **before Strategy 01 Stage 5** |
| D-7 | Daily bars from 2024 for reliable PDH/PDL; special-session handling | **Approved** as part of Strategy 01's task (T-I142): backfill daily bars from 2024-01-01 and exclude the five partial or evening sessions (a verified holiday calendar is not required to start) |
| D-8 | Technical: single-strategy run mode in the research harness (no primary-signal selection, no score gate, no slot limit in experiment 4a) | **Built 2026-11-21** (T-I142 Stage 2, on branch `docs/strategy-01-specification`, not yet merged); isolation test passes on a synthetic fixture only, to be repeated on real bars before the first backtest |
| D-9 | Technical: short-side replay support | Open; follows D-4 |
| D-10 | Technical: Strategy 12 methodology | Open; after the owner reviews MP-01; not scheduled |

## 7. Maintenance

Update the tracker only with evidence, in the same change as the work. Keep the per-strategy pages and CURRENT.md consistent with it. If this table and a strategy page disagree, fix whichever is wrong and note it in the page's "Outstanding issues".
