# Framework Diagnosis Plan

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Status | Pre-registered, 2026-11-22. Fixed before any result was seen (2026-11-22); a change after that is a new, separately logged experiment. DX-0..DX-5 and DX-7 have run, see [the report](framework-diagnosis-report.md) |
| Owner decision | 2026-11-22: pause new strategy stages and diagnose why every tested rule set loses before costs |
| Related | [Experiment registry §4](experiment-registry.md#4-framework-diagnosis-experiments) · [Independent backtesting standards](independent-backtesting-standards.md) · [Validation criteria](validation-criteria.md) · [TRD-06](../trading/06_BACKTESTING_METHODOLOGY.md) · [Strategy roadmap](../development/strategy-development-roadmap.md) |

Hypothetical, simulated results only (TRD-06 BT-06). The repository is public, so only aggregates are recorded here; raw output stays outside it.

## 1. Why this exists

Every rule set tested so far loses money **before costs**:

| Run | Trades | Avg R gross | Avg R net | Source |
|---|---|---|---|---|
| `pa-intraday 0.1.0`, 2026-09-01..11-19 (combined) | 176 | −0.20 | — | registry PRE-001 |
| Variant D, 2026-01-01..08-31 (combined) | 164 | −0.08 | −0.18 | registry PRE-003 |
| Strategy 01, 4a in-sample, 2024-01-02..2025-09-23 | 11,363 | −0.16 | −0.33 | registry §1.1 |

Strategy 01 is negative in every anchor, every 15m regime, every half hour and all 21 months. Different entry ideas failing this uniformly suggests a cause **shared by all strategies** (the execution and exit model, friction, the market itself, or a simulator defect) rather than a weakness of each entry rule. Building strategies 03 to 12 on top of an unexplained shared loss would repeat the result. This plan finds the cause first.

## 2. Hypotheses (fixed now)

| ID | Hypothesis | What would support it |
|---|---|---|
| H1 | **Entries carry no edge.** The setups pick moments no better, or worse, than random | Setup trades are not better than matched random entries under the same exits (DX-4); forward returns after signals are not above the unconditional drift (DX-2) |
| H2 | **Friction is large relative to the stop.** Slippage (0.05% on every entry and on stop exits) and charges (about 0.06% to 0.08% of position value per round trip under `nse-intraday-assumed-0`) are fixed in price terms, so their cost in R grows as the stop shrinks. With the minimum stop of 0.15%, friction can reach most of 1R | Loss per trade concentrated in the small stop-distance buckets; R before friction near zero or positive (DX-3) |
| H3 | **The exit model cuts winners.** Targets of at least 2R (`risk.min_rr`) are rarely reached before the session-end exit, and a bar that touches both stop and target counts as a stop (BT-04) | Most exits are session-end or stop; the optimistic collision bound or fixed-horizon exits change the sign of gross R (DX-5) |
| H4 | **Long-only intraday drift is negative** for today's NIFTY 50 over the period | Mean return from the post-opening-range bar to the session exit is negative (DX-1) |
| H5 | **The fill rule selects against the trade.** Entry is at the next bar's open plus slippage, and the fill is skipped when the gap or the reduced R:R breaks a limit (`simulate_entry` in `app/domain/risk/fill.py`; `SKIPPED_RR_DEGRADED` 7,556 times in Strategy 01). The trades that remain may be mostly those where price did not follow through (adverse selection), and each pays the fill gap | The fill gap takes a large share of the stop distance (DX-3); signals skipped by the fill rule have better forward returns than the filled ones (DX-2, where the skipped signals can be recovered) |
| H6 | **The cost schedule is wrong** (unverified, OQ-BT-02, D-6) | Contract notes differ from `CostSchedule` (DX-6) |
| H7 | **The simulator has a defect** (fills, stops, P&L, gaps T-I136, previous-day levels T-I138) | Hand-checked trades disagree with the raw bars (DX-7) |

The hypotheses can hold together; the tests are designed to measure each one's share, not to pick one.

## 3. Data rules

- **In-sample only:** the 427 in-sample sessions 2024-01-02..2025-09-23 ([registry §1.1](experiment-registry.md#11-pre-registration-strategy-01-experiment-4a-in-sample-registered-2026-11-21-before-any-chunk-ran)). The out-of-sample (2025-09-24..2026-04-24) and holdout (2026-04-27..2026-11-19) segments are not used by any DX test, so a framework change chosen from these results can still be validated on unseen days.
- **Exception, DX-0:** the `pa-intraday 0.1.0` baseline on 2026-01-01..08-31 (the remaining part of T-I134) was started before this plan, on days already used by PRE-003. It is recorded as a pre-framework run for context and **no decision in this plan may rest on it**.
- Same universe (today's NIFTY 50, `--members-on 2026-11-19`, `survivorship_bias_risk`), special-session and previous-day exclusions, sizing (FIXED, ₹500 risk unit, no account limits, as experiment 4a), costs (`nse-intraday-assumed-0`) and slippage (0.05%) as §1.1, except where a test changes one item on purpose and says so.
- Inputs are the stored Kite 5m and 1D bars and the saved Strategy 01 and Strategy 02 4a chunk files. Strategy 02 results are used only once its pre-registered 4a run (registry §1.2) has finished, and they do not change that run's decision rule.

## 4. Tests

Run in this order. Each test records its code commit, input hashes, seeds and exclusions in the registry.

| ID | Test | Method | Output |
|---|---|---|---|
| DX-0 | `0.1.0` baseline (context) | Combined run, `pa-intraday 0.1.0`, 2026-01-01..08-31, the same 4 chunks as PRE-003 | PRE-005 in the registry; D vs baseline. Context only (§3) |
| DX-3 | **R decomposition** | From the Strategy 01 trades (and Strategy 02 when available): per trade, R before slippage, slippage in R (entry and stop exit), charges in R, and the fill gap (fill price minus signal-bar close) in R. Bucketed by stop distance: 0.15–0.30%, 0.30–0.50%, 0.50–1.00%, 1.00–2.00% | Table of avg R gross, net and before-friction per bucket; share of the loss from each friction item. Tests H2, H5 |
| DX-1 | **Drift baseline** | Every in-sample instrument-session: buy at the open of the first bar after the opening range (09:30), sell at the session-exit bar (15:15); no stop, no target. Repeated at seeded random entry bars inside the entry window (seed 1) | Mean and median return % with a 95% CI; by month and by 15m context. Tests H4 |
| DX-4 | **Matched random-entry control** | For each Strategy 01 trade, 5 controls (seeds 1–5) on the same symbol and session, at a uniformly random 5m signal bar inside the same entry window (after the opening range, before the entry cutoff), filled at the next bar's open by the same fill rule (`simulate_entry`: cutoff, gap and R:R checks, slippage; a skipped control is redrawn up to 20 times and the redraw count reported), with the same stop distance in % and the same target in R, and the same exit code (`app/backtest/trade.py`: session exit, BT-04 collision, slippage, charges). One open trade per symbol as in 4a. Repeated for Strategy 02 | Avg R gross and net of strategy vs controls with a 95% CI. Tests H1, and separates the entry from the exit and friction machinery |
| DX-2 | **Signal forward returns** | For each strategy trade, return from the fill price to the close 3, 6 and 12 bars later and at the session exit, with no stop or target, in % and in units of the trade's stop distance. Compared with the same horizons from random bars of the same symbol and session (DX-4's seeds). Signals skipped by the fill rule are measured separately if they can be recovered from the run; if not, this is recorded as a limitation | Mean forward return, strategy minus random, with a 95% CI. Tests H1 without any exit-model effect |
| DX-5 | **Exit-model bounds** | On the Strategy 01 entries: (a) the optimistic collision rule (target first) as an upper bound against BT-04; (b) fixed-horizon exits at 6 and 12 bars and at the session exit, with the original stop; (c) no slippage on stop exits | Avg R gross under each variant. Diagnostic bounds only, **not a parameter choice**. Tests H3 |
| DX-7 | **Simulator spot check** | 20 Strategy 01 trades drawn with seed 1: recompute fill, stop, exit and P&L by hand from the raw bars; count instrument-sessions with missing 5m bars (`missing_bar_starts`) in the in-sample data | Agreement table; gap count. Tests H7 |
| DX-6 | **Charges check** | The owner supplies 3 to 5 Zerodha intraday contract notes; each is recomputed with `CostSchedule` | Per-item difference; Strategy 01 net R recomputed if the schedule changes. Tests H6. Waits for the owner (D-6) |

**Statistics.** Confidence intervals by bootstrap over sessions (whole sessions resampled, so trades on one day stay together), 10,000 resamples, seed 1. A difference is "material" when its 95% CI excludes zero **and** it is at least 0.05R (or 0.02% for DX-1 returns). No other threshold is used.

### 4a. Implementation amendments (2026-11-22, written before any DX-1..DX-7 test ran)

Found while reading the saved chunks and the replay code. They narrow the method only where the saved data cannot support the text above; no result had been seen.

1. **The target is not in the saved trades** (a trade stores entry, exit, quantity, risk amount and costs, not the target). The stop is recoverable (`entry - risk_amount / qty`); the target is not. So DX-4, DX-2 and DX-5 use one **common target of 2.5R** (R measured from the entry reference) for the strategy entries *and* for the controls, and compare like with like. The strategies' own recorded result is shown beside it. 2.5R is fixed from the saved target exits (median 2.3R for Strategy 01, 2.3R for Strategy 02, which are biased low because near targets are hit more often) and because a target of exactly 2.0R can never pass the fill rule after 0.05% slippage. It is not tuned on any result.
2. **Controls use the stop distance of the matched trade in % of the fill price** (the saved entry includes slippage; the entry reference is not stored). Stops are not rounded to the tick.
3. **DX-1 by 15m context is not reported**: it needs a per-bar structure analysis. DX-1 is reported by month only.
4. **DX-2 cannot measure signals the fill rule skipped**: skipped signals are not in the saved chunks (counts only). Recorded as a limitation, as the plan allows.
5. **DX-3 fill gap** is the fill bar's open minus the previous bar's close (the signal bar close), taken from the stored bars; the entry reference is not stored.
6. **DX-5 (a)-(c) run on the common 2.5R exit**, with the baseline being the same entries under the same common exit (not the recorded exits), so each variant isolates one change.
7. **DX-6 uses the broker's published schedule** (added 2026-11-23): the owner has never traded on Kite and has no contract notes. The charge items are compared with Groww's published schedule (the planned broker) and the saved trades are recomputed. Slippage cannot be checked this way.

## 5. Decision rules (fixed now)

The result is a report, not a rule change. Whatever it finds, a framework change goes to the owner, then into a new ruleset version (or an engine change with tests), and is validated on data this plan did not use.

| Finding | Conclusion | Next step (owner decides) |
|---|---|---|
| DX-4 controls lose about as much gross as the strategies (difference not material) | The loss comes from the shared machinery, not the entries | Fix or re-specify the shared part named by DX-3, DX-5, DX-6, DX-7 (for example the minimum stop, slippage model, exit rules or a defect), then re-run DX-4 before resuming strategies |
| Controls near 0R gross and strategies materially worse | The entries select bad moments (adverse selection) | Entry research. Strategy work resumes only with a hypothesis about entry timing |
| Strategies materially better than controls but still negative | Entries have some edge that friction or exits remove | Act on the largest drag found by DX-3 / DX-5, then re-test |
| DX-1 drift materially negative | Long-only intraday faced a headwind in this period | Owner decision on scope (direction, timeframe, universe); any change to long-only actionability needs a superseding ADR (ADR-014) |
| DX-7 finds a defect | Results so far may be wrong | Fix with a test first; re-run the affected experiments before anything else |
| DX-6 changes the schedule | Net figures change; gross do not | Update `CostSchedule` with its source, record the new version, re-state the net results |

## 6. Implementation

- Code goes under `python-engine/app/backtest/diagnostics/` with unit tests (entry-window sampling, matched controls, R decomposition, bootstrap), and a runner `python-engine/scripts/run_diagnostics.py`. It reuses the existing exit and cost code and changes **no** detector, ruleset or replay behaviour; the engine suite must stay green and the isolation proof must still show 0 differences.
- DX-1, DX-3, DX-4, DX-2 and DX-5 need only stored bars and saved trades, no new strategy analysis, so each should run in minutes. DX-0 is the only long run.
- Results: `docs/research/framework-diagnosis-report.md` (aggregates only) and one registry row per test. Raw output in the research directory outside the repository.

## 7. Status

| Item | State |
|---|---|
| Strategy programme | New strategy stages paused (owner, 2026-11-22). The pre-registered Strategy 02 4a in-sample run (registry §1.2) finished and the strategy was parked; Stages 4b and later wait for the owner's decision on this report |
| DX-0 | Done 2026-11-22: 570 trades, -0.18R gross, -0.37R net, net -₹50,433 ([log §7](../trading/backtests/2026-11-20-pa-intraday-0.1.0-nifty50.md#7-baseline-pa-intraday-010-on-2026-01-01-to-2026-08-31-t-i134-dx-0)). Context only |
| DX-1..DX-5, DX-7 | Done 2026-11-22: [report](framework-diagnosis-report.md); registry §4. Implementation amendments in §4a |
| DX-6 | Done 2026-11-23 against the broker's published schedule (§4a item 7): charges match within +0.005R per trade; slippage still unverified ([report §6](framework-diagnosis-report.md#6-dx-6-charges-check-published-schedule)) |
