# ORB F-1: dual target experiments, specification and implementation readiness

Date: 2026-11-25. **DRAFT, UNREVIEWED. AI-assisted and NON-INDEPENDENT.** It is a proposal for owner approval, not an implementation and not a backtest authorisation. No frozen document and no released ruleset is edited. Origin: finding F-1 of the [OD-8 Step 2 record](orb-od8-step2-record.md#3-findings); owner decision recorded as [DEC-042](../../DECISIONS.md).

## 0. Governance

DR-7a is open and DR-11 covered D1 only. This page adds a new strategy-definition amendment (variant B) without touching the frozen B0 text, so it can be drafted, but it cannot be approved, frozen or used for research until the independent-review requirement is met or the owner records a written extension. The same applies to the curated reference tables a run needs. Nothing here weakens that.

## 1. Notation (both variants)

For instrument-session with opening range low `L`, signal bar `c` (first close above `OR_HIGH x (1 + b)`), `E = C[c]`, next open `O = O[c+1]`, entry slippage `s = 0.0005` (`backtest.slippage_pct`), stop buffer `sb = 0.0005`, tick `tau` (the resolved tick on a traded-scale session, `None` on a provider-adjusted session; `down(x)` is `x` when `tau` is `None`).

- Stop (both variants, unchanged): `S = down(L x (1 - sb))`, independent of the fill.
- Fill (both, unchanged): `F = O x (1 + s)`, not tick-rounded (as implemented in `simulate_entry`).
- Fill skips (both, unchanged, in this order): bar starts at or after the cutoff; `O <= S` (`SKIPPED_GAP_BELOW_STOP`); `O > E x 1.003` (`SKIPPED_GAP_UP`); `rr_fill < 2.0` (`SKIPPED_RR_DEGRADED`).
- `rr_fill = (T - F) / (F - S)` for the variant's target `T`.

## 2. Experiment A: original B0 (frozen, unchanged)

`R_sig = E - S`, `T_A = down(E + 2 R_sig) = down(3E - 2S)`. Implemented today as strategy `orb_b0` on `pa-intraday 0.6.0`, immutable.

Consequences (derived, and pinned by `test_finding_f1_...`):
1. With `T_A = 3E - 2S` unrounded, `rr_fill >= 2` is equivalent to `F <= E`, that is `O <= E / (1 + s)`, an open at least about 0.05% below the signal close.
2. On a traded-scale session `E` and `S` are tick multiples, so `3E - 2S` is already a tick multiple: **the target rounding changes nothing** (`delta = 0`). On a provider-adjusted session `tau` is `None`: no rounding. Rounding can bite only if `E` itself is off-grid (corrupt data).
3. A filled trade therefore has `rr_fill >= 2` exactly or more, with `R_fill = F - S < R_sig`.
4. Worked example: `E = 1006`, `S = 999.50`, `T_A = 1019.00`. `O = 1005.40` gives `F = 1005.9027`, `rr = 2.046`, trades. `O = 1006` gives `F = 1006.503`, `rr = 1.784`, `SKIPPED_RR_DEGRADED`.

The skip rate is a primary output of A, not a defect to hide. A's selection (gap-down opens only) is the reason B is proposed.

## 3. Experiment B: fill-based B0 (new, separate amendment)

Same detection, eligibility, entry, slippage, stop and exits as A. The target is set from the actual fill:

`R_f = F - S` (positive, because `O > S` was checked), `X = F + 2 R_f = 3F - 2S`, `T_B = down(X)`, `delta = X - T_B` in `[0, tau)`.

`rr_B = (T_B - F) / R_f = 2 - delta / R_f`.

### 3.1 The rounding and RC-04 problem (must be decided, not hidden)

`S` is a tick multiple but `F = O x 1.0005` is almost never one, so `X` is almost never a tick multiple and `delta > 0`. Then `rr_B = 2 - delta / R_f < 2.0`. **If RC-04 is retained literally (actual rr at fill, minimum 2.0, adverse target rounding), nearly every trade is skipped as `SKIPPED_RR_DEGRADED`.** `X` is on the grid only when `0.0015 x O` is a tick multiple, about 1 opening price in 2,000 (for `tau = 0.05`, opens that are multiples of 100). Worked example: open 1006, `F = 1006.503`, `R_f = 7.003`, `X = 1020.509`, `T_B = 1020.50`, `rr_B = 1.99871 < 2`, skipped.

Worse, on provider-adjusted sessions `tau` is `None`, `delta = 0`, `rr_B = 2` and the trade passes. **Literal B would trade almost only provider-adjusted sessions**, a confound by price basis (limitation L-6 territory) that has nothing to do with the strategy hypothesis.

The shortfall is small when it is allowed: `2 - rr_B < tau / R_f`. For `R_f = 7`, `tau = 0.05` it is at most 0.0071R (0.36% of the 2R reward).

### 3.2 Options (owner decision OD-F1-B; the rule is not relaxed by this draft)

| Id | Rule | Effect |
|---|---|---|
| B-1 | Literal: actual `rr_B >= 2.0` after rounding | About zero trades on traded scale; basis confound. Not recommended as a research design; usable only as a documented demonstration |
| B-2 (proposed) | RC-04 for B tests the **nominal** ratio `(X - F) / R_f = 2` (before rounding), and the realised `rr_B` is recorded on every trade with `delta` and the shortfall; reports show the distribution and the bound `tau / R_f` | Same meaning as B0's own "rr = 2.0 by construction before rounding" (spec §12.4); no trade is admitted that the design says fails; the rounding cost is measured, not hidden |
| B-3 | Explicit tolerance `rr_B >= 2.0 - tau / R_f` | Equivalent in effect to B-2 for rounding but states a number; an owner-chosen relaxation |
| B-4 | Round the target **up** to the next tick | Contradicts "same adverse rounding"; not proposed |

Recommendation: B-2. It is an explicit amendment of the RC-04 measure **for variant B only**; A keeps RC-04 exactly. The minimum 2.0 stays the minimum; what changes is that it is evaluated before the adverse tick rounding, the same way spec §12.4 states for the signal-time check.

### 3.3 Other differences between A and B
- B's `R_f` can exceed `R_sig` when `F > E` (up to a 0.3% gap up), so a stop distance that passed RC-01 at `E` can be a little larger at the fill. RC-01 is not re-run at fill in either variant (unchanged); B records `(F - S) / F` as a diagnostic and the report counts fills above the 2.0% stop-distance limit.
- Position sizing already uses the fill (`F - S`) in both variants; no change.
- Exits are unchanged: stop, target (at `T`), session end, structure exit off (0.6.0 and later).
- The signal-time plan and the RC-02 check at signal use the nominal 2.0 in both variants; the stored signal-time target of B is provisional and replaced at the fill.

## 4. Versioning and ruleset proposals

| Item | A | B |
|---|---|---|
| Strategy id | `orb_b0` (exists, immutable) | `orb_b0_fill` (new) |
| Specification | [ORB spec](../strategies/opening-range-breakout.md) frozen 1.0.0 | New page `docs/strategies/orb-b0-fill-target.md` v0.1.0 DRAFT, "strategy-definition amendment AM-F1, not a correction of B0"; the frozen page gets a pointer only after review |
| Ruleset | `pa-intraday 0.6.0` (unchanged, hash `aaa4ab07...`) | New `pa-intraday 0.7.0` = `0.6.0` with `orb.target_method` `FIXED_R_FILL` and, under B-2, `orb.rr_check_basis` `NOMINAL` (absent in 0.6.0, where the actual-fill check is the only behaviour) |
| Role | RESEARCH | RESEARCH |
| Detector | `detect_orb_b0` (untouched) | `detect_orb_b0_fill`: reuses the same signal code through a shared helper so the signal population is identical by construction |

No edit of 0.1.0 to 0.6.0, no edit of A's tests except additions. A's `check_b0_parameters` keeps rejecting `FIXED_R_FILL`, so A cannot be turned into B by configuration.

## 5. Files and components affected (when implemented)

New: `app/domain/setups/orb_b0_fill.py` (detector; pure fill-target function `fill_target(F, S, tau, k)` returning `T`, `delta`, `rr_realised`); `rulesets/pa-intraday/0.7.0.json` plus seeder copy; spec page; `tests/trading/test_orb_b0_fill.py`; `tests/backtest/test_strategy_run_b0_fill.py`; comparison tooling `scripts/compare_orb_targets.py` (reads two run outputs, writes nothing to the database).
Modified (additive): `app/rulesets.py` (role), `app/domain/strategies.py` and `scripts/check_strategy_isolation.py` (id), `app/domain/risk/fill.py` (a separate `simulate_entry_fill_target`; `simulate_entry` untouched), `app/backtest/replay.py` (choose the entry function and carry the recomputed target into `Position`, selected by a `target_basis` field so A's path is byte-for-byte the same), `app/backtest/trade.py` (optional fields `signal_target`, `fill_target`, `delta`, `rr_realised`, default `None`), `tests/test_ruleset_integrity.py`, ruleset changelog, DECISIONS, TASKS, CURRENT, docs status. Not touched: PAQS, risk limits, matched-control code, candles, the database.

## 6. Required tests

Both variants: determinism; no look-ahead (target from `F` uses only `O[c+1]`); truncation equality; symmetry of eligibility (one `EligibilityMap`); tick `None` versus resolved; `SKIPPED_*` order; replay equivalence; unsupported values rejected.
A (regression, exist or extend): the F-1 pin; for every traded-scale input `delta = 0`; trades only when `F <= E`; A's outputs identical before and after the B code lands (golden vectors).
B: `T_B = down(3F - 2S)` on vectors with and without a grid-aligned `X`; `rr_B = 2 - delta / R_f` identity; bound `delta < tau`; B-1/B-2 behaviour pinned for the owner's choice, including the basis-confound case (the same bars on traded and adjusted scale); gap-up fills up to 1.003 E; stop distance diagnostic; a skip when `O <= S`; B and A emit identical signals on identical bars (the signal-population test).

## 7. Comparison protocol (specification only; nothing is run)

Pre-registered before any run, on the same development data, with one run per variant per population:
1. **Identical** across A and B: instrument-session eligibility (one `EligibilityMap`, hashes recorded), signal population (compared by `(symbol, session, signal bar)` and required equal), entry and slippage, stop, costs, portfolio constraints, matched-control method. The control arm of each variant is run under that variant's own fill and target rules; the control method (selection, matching, eligibility) is unchanged.
2. **Separate** records: trades and skipped signals per variant, with reasons; metrics; statistical evaluation against the unchanged acceptance criteria. No pooling of A and B trades.
3. **Compared** (descriptively, side by side): signal count; filled trades; skips by reason; win rate; average R (gross and net); net expectancy; profit factor; maximum drawdown; by instrument and by market period; ORB minus matched controls, with intervals. Under B-2 also the realised-rr shortfall distribution.
4. Two views per variant: filled trades only, and all signals with a skipped signal counted as no trade (reported next to the skip rate so selection is visible). A paired comparison on signals filled by both variants is reported as a diagnostic.
5. **No winner by trade count.** More trades is not better. Neither variant is promoted from this comparison alone; the multiplicity cost of two experiments must be set by the owner before the run (proposal: evaluate each against the unchanged criteria separately and report both; no selection of the better one without a pre-registered paired test).

## 8. Remaining governance and backtest prerequisites

1. Owner choice of B-1, B-2 or B-3 (OD-F1-B), and the multiplicity rule.
2. Independent human reviewer (DR-7a) or a written extension, for the new spec page, ruleset 0.7.0 and every curated table.
3. The real tick, event and session tables reviewed and hash-pinned; the price-basis matrix pinned.
4. The remaining Step 2 items: the control arm over `EligibilityMap`, persistence of `reference_data` in chunks, MG02-A1 and session-facts spec amendments.
5. The sample-size reconciliation decision (Step 2 record §5): with A skipping most signals, the trade count must be measured first.
6. A separate explicit authorisation to implement B and a further one to run either backtest. Neither is given by this page.
