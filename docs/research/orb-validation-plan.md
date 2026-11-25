# ORB Validation Plan (Phase 3 draft)

| Field | Value |
|---|---|
| Version | 0.6.0 (draft; owner decisions of 2026-11-23 applied: calibration screening thresholds, P0-1 approved for separate execution, trade-floor counting rules, prospective universe, OD-14) |
| Status | **Draft. The plan as a whole is not approved and not pre-registered.** The ORB specification and B0 were approved and frozen on 2026-11-23. Of the Phase 3 decisions, **OD-14 is approved** (with counting populations), the calibration screening thresholds, the P0-1 scan (for separate execution, not run), the trade-floor counting rules and the prospective universe are accepted; **OD-8, OD-15 and OD-16 are open** and P0-1b is not approved. Nothing has been run. The plan becomes binding only when the owner approves it; the [ORB specification](../strategies/opening-range-breakout.md) family is then entered in the [experiment registry](experiment-registry.md) with the plan's commit hash **before** any run |
| Strategy | 09 Opening Range Breakout (`opening_range_breakout`), long only |
| Related | [ORB specification](../strategies/opening-range-breakout.md) (rule IDs) · [Decisions and readiness](../development/orb-phase2-decisions-and-readiness.md) (OD register, engineering prerequisites) · [Independent backtesting standards](independent-backtesting-standards.md) · [Validation criteria](validation-criteria.md) · [Research data limitations](research-data-limitations.md) · [Fast screening report](fast-screening-report.md) · [Framework diagnosis report](framework-diagnosis-report.md) |

Hypothetical, simulated results only (TRD-06 BT-06). Aggregates only in the repository.

**What changed in revision 2.** Exposed 2026 data is development data, not a holdout (§2). Validation is prospective (§8). The random-entry control is rebuilt to match universe, sessions, entry times, frequency, direction, exits, costs and portfolio constraints, with a stated evaluation of the difference (§4.2-4.3). Targets are separate experiments (spec §12.4). The 65 variants are cut to 38 with explicit hypotheses and a two-tier multiple-testing design (§6-7). Stage A has stopping and continuation criteria fixed in advance (§4.4).

## 1. Purpose and rules that bind every experiment

Establish, with as little data-snooping as possible, whether ORB has a positive entry edge and, only if it does, which rules contribute. All retrospective work **nominates** a configuration; **only prospective data validates** it.

1. **Independence.** Only the ORB detector runs. No other strategy confirms, suppresses, filters, ranks or combines ORB trades; no PAQS, no `choose_signal`, no slot limit in experiment 4a ([standards §2, §3](independent-backtesting-standards.md)). The isolation proof is a required test.
2. **One change at a time** against B0. No factorial grid. Target methods are never combined.
3. **Pre-registration before running.** The registry of §7 (with hypotheses and predicted signs), the controls, the decision rules and the assembly rule are frozen at approval.
4. **Everything is logged,** including failures and dropped variants, with a cumulative variant count.
5. **No promotion by this plan.** Live use needs the separate path of DEC-025.

## 2. Data classes and exposure

### 2.1 Classes (owner review, item 1)

| Class | Period | Status for ORB |
|---|---|---|
| `DEVELOPMENT` | 2024-01-02 to 2025-09-23 (partly seen through the M1 screen on 10 stocks) **and 2026-01-01 to 2026-11-19 (seen in combined runs; classified development by the owner)** | Used to define, explore and select. Never described as out-of-sample or holdout. Results here are optimistic by construction |
| `RESERVE` | 2025-09-24 to 2025-12-31 (about 70 sessions) | Never seen for ORB. **Retrospective**: the segment was chosen after the exposure was known and the market period is known, so it is supportive evidence only, not blind (OD-17) |
| `PROSPECTIVE` | Sessions after the frozen pre-registration (§8) | The only genuinely unseen observations. The only data that can support `RESEARCH_VALIDATED` |

The labels in-sample / out-of-sample / holdout used for Strategies 01 and 02 do **not** apply to ORB. No ORB document uses "blind" or "holdout" for any retrospective period. Walk-forward, thirds and robustness checks inside `DEVELOPMENT` measure stability, not validity.

### 2.2 What was seen

| Exposure | Period | What was seen |
|---|---|---|
| Fast screen M1 | 2024, 10 stocks | Aggregate minimal-ORB results vs random entries |
| Combined runs PRE-001 to PRE-003 and the 2026-11-20 diagnostics | 2026-01-01 to 2026-11-19 | ORB trade counts and averages inside non-isolated runs (13, 75, 49 trades) and an opening-hour window tested on the same trades |

### 2.3 Exclusions and flags (every run)

Special sessions removed (L-4); invalid ranges (`ORB-MG-02`, §7.1.2 of the specification) removed from ORB **and from every control's eligible sessions alike**; corporate-action windows excluded (L-6); sessions from 2026-08-03 flagged for the missing 15:15-15:25 bars (L-3), trades held to the session-end exit reported separately. Flags on every result: `survivorship_bias_risk`, `costs_unverified`, `UNSUPPORTED_DIRECTION:SHORT`, and the data class (`DEVELOPMENT`, `RESERVE`, `PROSPECTIVE`).

### 2.4 Instrument universes: historical (Stage A) versus prospective (Stage C)

The two universes are different objects and are never pooled.

| | Stage A and Stage B (historical) | Stage C (prospective) |
|---|---|---|
| Universe | Today's NIFTY 50 membership applied to every historical session (membership dated 2026-09-01 or later; [L-1](research-data-limitations.md)). No point-in-time membership exists for 2024-2026 (OQ-BT-01, D-6) | The **50 instrument identifiers** of the NIFTY 50 membership on the freeze date, frozen for the whole horizon and recorded in the freeze package. **No replacement instruments, ever.** A later delisting, suspension, symbol change or unavailable instrument **stays in the dataset**, with its data and the event recorded; corporate actions, index removals and data outages are logged with dates |
| Survivorship bias | **Present and unavoidable.** Today's members include stocks that entered the index because they rose, and exclude stocks that fell out. Long positions on these names are biased upward, in absolute expectancy and drawdown. **The historical survivorship limitation remains** and the flag `survivorship_bias_risk` stays on every Stage A and Stage B result | **Owner decision 2026-11-23: the historical survivorship-bias flag is cleared for the frozen prospective universe only.** The universe is fixed before the future is observed and is never edited, so forward returns do not depend on which names later survive. Residual effects (index changes during the horizon, a short horizon, one market period) are recorded, not ignored |
| Effect on the Stage A decision | The edge `Δ` compares ORB with a control on the **same instruments and sessions**, so the level bias largely cancels; it does not cancel if breakouts are more frequent in momentum names. The **gross mean R `> 0`** condition of §4.4 is an absolute figure and is biased toward passing; it is reported as an upper bound and must not be read as evidence of an edge on its own | Results are not biased by the selection of names |
| Stated limits | Names with symbol changes or demergers (for example ETERNAL, TMPV; L-2, L-6) are excluded per run, listed in the run record | A freeze-date membership list is stored in the freeze package |
| What may be claimed | At most "met the Stage A criteria on a survivorship-biased universe: an upper bound" ([criteria §3, D-3](validation-criteria.md)) | A statement about **this frozen universe over this horizon**. It is **not generalised** to other instruments, other periods or a changed index without further evidence. The flag is cleared for these results only; it stays set for every historical result |

No sensitivity analysis on membership is possible without membership history; none is invented. The robustness checks that do not need it (single-instrument share, year and regime cuts) apply.

## 3. Pre-flight (counts only, no returns)

Engineering that Phase 3 needs is listed, with its status and its separation from methodology, in the [readiness page §3](../development/orb-phase2-decisions-and-readiness.md#3-engineering-prerequisites-for-isolated-orb-research). Pre-flight checks, reported as counts on `DEVELOPMENT` data:

| ID | Check |
|---|---|
| P0-1 | **Counts-only data-integrity scan** (defined below). **Approved 2026-11-23 and executed once on 2026-11-23**; the tick-dependent counts are not reliable; a post-remediation scan is conditionally approved and not run ([remediation page](../development/orb-data-remediation.md)) |
| P0-2 | Index series in storage? Daily-bar coverage (previous close, high, low) per session. Decides whether `CF-04`, `06`, `07`, `08` are testable (`UNTESTABLE` otherwise) |
| P0-3 | Isolation proof: single-strategy ORB candidates equal the ORB-only candidates of a full `analyse()` run on the same real bars (CUR); 0 differences required |
| P0-4 | Fidelity: B0 reproduced on hand-built bars; truncation-equality and replay tests pass |
| P0-5 | Resolution: the M1 screen resolved about 0.05R with about 1,000 trades; resolution scales with `1/√n`. Report B0's expected trade count from P0-1 |

**P0-1 definition (counts-only data-integrity scan; to run only after a separate owner approval).**

- *Purpose:* find data defects that would invalidate ORB ranges or sessions, and size the eligible population, before Stage A.
- *Scope:* stored 5m, 15m and 1D bars and the calendar, for the `DEVELOPMENT` classes of §2.1 only. `RESERVE` and `PROSPECTIVE` data are not scanned. It runs no detector beyond the pure range validator (spec §7.1.2), no simulation and no control generation.
- *Permitted output (fixed table layouts, rows in alphabetical symbol order and ascending date order, never sorted by a count or a value):* instrument-sessions per data class and per calendar month; sessions excluded by `MG-01` by reason; opening ranges failing `MG-02` by sub-reason (`OR_MISSING_BAR`, `OR_DUPLICATE_BAR`, `OR_INVALID_OHLC`, `OR_NOT_CLOSED`) per month and per instrument (data defects only); instrument-sessions whose width falls inside `0.30-2.00%`; daily-bar and tick-size coverage; whether an index series exists; the input hash.
- *Forbidden output (the exact contract, unchanged; the owner's approval of 2026-11-23 restates it):* any profitability or return statistic (P&L, R, win rate, expectancy); any statistic of price movement after the range closes; any edge estimate; any ranking or ordering by count, value or performance; any comparison with a control or between instruments' results; **no signal counts and no trade counts, whether by instrument or in aggregate** (a first close above the trigger, a candidate, a fill, a skip). The output file carries a header stating this, and a reviewer confirms it before the owner reads it.
- *Feasibility counts (P0-1b) are a separate item and are **NOT APPROVED** (owner, 2026-11-23).* They would count B0 signals and fills by month; they will not be run, and P0-1 must not produce them. Whether the 1,000-trade gate is met is therefore known only when Stage A runs: if it is not, Stage A halts with `INSUFFICIENT_SAMPLE` (§4.4) and nothing is interpreted.
- *Status:* **executed 2026-11-23** (counts-only, development data only, no P0-1b). Superseded for tick-dependent counts by the conditionally approved post-remediation scan (not run).

Planning scale (from M1 only, not a result): about 0.4 trades per instrument-session, so B0 should give thousands of trades on 50 stocks; CUR (far target, 15m filter) far fewer.

## 4. Stage A: the entry-edge test

### 4.1 What runs

B0 and CUR ([spec §10.3](../strategies/opening-range-breakout.md#103-reference-configurations)), experiment 4a (every valid candidate, one open trade per symbol, fixed risk unit), on all `DEVELOPMENT` data, once, with the matched control of §4.2. CUR is a fidelity and comparison run and **does not enter the decision of §4.4**. B0 has no context filter at any instant ([spec §10.4](../strategies/opening-range-breakout.md#104-evaluation-timestamps)).

### 4.2 The matched random-entry control (MTC)

Why a new control. The M1 control drew a random bar from the whole session on the same symbol-sessions as the ORB trades. It was not matched on entry time, it was drawn only on sessions where a breakout later happened (a control bar before the breakout has the breakout in its future), and it did not match frequency per instrument and month. Neither effect is proven to explain M1's result; both are removed here.

| Requirement | How the control is matched | Check (before any result is read) |
|---|---|---|
| **Instrument universe** | The same 50 instruments; control entries per instrument equal ORB's filled trades per instrument | Counts per instrument identical |
| **Eligible sessions** | Controls are drawn only from sessions that pass `MG-01`, `MG-02` and `SC-03` (the same eligibility as an ORB candidate), **whether or not a breakout occurs** | Same eligibility function and the same invalid-session list as ORB |
| **Entry-time distribution** | Each control's signal time is drawn from the empirical distribution of ORB signal times (5m bins) in the analysed segment | Distribution difference (maximum CDF gap) at most 0.01 pooled and 0.03 per quarter |
| **Trade frequency** | Per instrument and calendar month, the number of control entries equals ORB's filled trades; at most one entry per instrument-session (as ORB) | Counts per instrument-month identical |
| **Direction** | Long only | By construction |
| **Risk and exit assumptions** | The same stop rule (`OR_LOW`, S-A, or the stop of the variant being tested), the same target method of the run, the same `RC-01`, `RC-02`, `RC-04` gates, the same exits and the same fill rule (signal at the close, fill at the next open) | A control that fails a gate (for example price below `OR_LOW`) is redrawn in time up to 20 times, then in session; the redraw rate is reported and must stay under 20% of draws, else the result is flagged `CONTROL_STRAINED` |
| **Costs and slippage** | The same schedule and the `adverse-all` slippage | Same function |
| **Portfolio constraints** | 4a: none beyond one open position per symbol, as for ORB. 4b: the control trades are replayed through the same account limits, capital, and the same documented tie-break as ORB | Same replay function; skip counts reported for both |

Replicates: `K = 1,000` independent control sets, seeds 1 to 1,000, fixed in advance. Each set is generated and simulated by the same code as ORB trades. The stop-distance distribution (median, quartiles) of controls and ORB trades is reported; a median differing by more than 25% is flagged, since the stop depends on the entry bar's price.

**Secondary diagnostics (not used in decisions).** C-B: on the ORB trade sessions, random entries strictly after the breakout bar (isolates timing given the event). C-C: the M1 control exactly as registered (comparability with the −0.150R figure). C-D: a placebo range formed at 10:15-10:30 with the same rules (is the opening range special?).

### 4.3 Evaluating the expectancy difference and its uncertainty

`R` is net or gross P&L divided by the planned risk (reference entry minus stop), as in the earlier protocols. Gross and net are both reported; the Stage A decision uses gross, the acceptance criteria use net.

1. `X_ORB` = mean R of ORB trades. `X_c(r)` = mean R of control set `r`.
2. **Edge** `Δ = X_ORB − mean over r of X_c(r)`.
3. **Uncertainty (month-block bootstrap, 10,000 resamples, seed 1).** Resample calendar months with replacement. In each resample recompute `X_ORB` over the drawn months' ORB trades and the control mean over the same drawn months' control trades (the control mean per month is already averaged over the 1,000 replicates). The 99% interval of `Δ` is the 0.5th and 99.5th percentiles. Month blocks keep within-month dependence between instruments and between ORB and its matched controls. The block method is **provisional** and is confirmed or replaced only by the predeclared calibration of §4.6 (development data span about 31 months, so even Stage A has few blocks).
4. **Control sampling error.** The spread of `X_ORB − X_c(r)` across the replicates is reported with the Monte Carlo standard error of the replicate mean; it must be at most 0.005R, else `K` is increased (decided and recorded before the result is read).
5. **Supplementary p-value.** `p = (1 + #{r : X_c(r) ≥ X_ORB}) / (K + 1)`, conditional on the months analysed. Not used for decisions.
6. **Stability.** `DEVELOPMENT` is split into three chronological parts of equal session count; `Δ` is computed in each. Cells under 30 trades are shown, not interpreted.
7. Sample sizes are printed beside every figure.

### 4.4 Stage A stopping and continuation criteria (fixed now, before any result)

**Integrity gate (halt).** Stage A results are read only if all hold: P0-3 shows 0 differences; P0-4 passes; the matching checks of §4.2 pass; the run record is complete (standards §5.3); B0 produced at least **1,000** filled trades. Otherwise: halt, record `INTEGRITY_HALT` or `INSUFFICIENT_SAMPLE` and the reason, and return to the owner. No result is interpreted.

**Outcomes** (on B0, `DEVELOPMENT`, gross, 99% interval):

| Outcome | Condition | What follows |
|---|---|---|
| **A-CONTINUE** | All of: `Δ ≥ +0.05R`; the interval's lower bound `> 0`; gross mean R `> 0`; `Δ > 0` in at least two of the three chronological parts | Stage B runs as written (§7) |
| **A-STOP (futility)** | The interval's **upper** bound `< +0.05R` (materiality cannot be reached) | Stage B does not run. Recommend `VALIDATION_FAILED` or `DEFERRED` (as for Strategies 01 and 02). The owner decides. A deliberate new hypothesis is a new pre-registration and counts as an improvement round ([criteria §5](validation-criteria.md)) |
| **A-INCONCLUSIVE** | Neither: the upper bound is at least +0.05R but the continue conditions are not all met | Stage B does not run. The owner chooses: freeze B0 for prospective testing alone (§8, no retrospective tuning), spend one improvement round with a written hypothesis, or stop |

**Rules around the decision.** Stage A runs once, as a single batch (B0, CUR, controls, diagnostics). Results are read only after the batch ends. B0 and the criteria above are not changed after reading. A re-run is allowed only for a verified implementation defect found by a test, is logged as a new row with the reason, and never replaces the first row.

### 4.5 What the sample-size thresholds count (clarification, 2026-11-23)

Three thresholds with different jobs were easy to confuse. Each counts one population. **Filled trades** means trades that passed every rule and the fill checks (`RC-04`), and that ended by stop, target or the session-end exit; `END_OF_DATA` trades are counted and reported separately and are excluded from the statistics (L-8, the same rule for ORB and controls).

| Threshold | Population it counts | Job | Where it applies |
|---|---|---|---|
| **1,000 (Stage A integrity gate; population approved under OD-14, 2026-11-23)** | The **filled B0 trades of experiment 4a, pooled across all `DEVELOPMENT` data and all 50 instruments before any chronological split into thirds.** **Excluded:** controls, CUR, every variant, prospective data, and `END_OF_DATA` trades. Not counted per instrument, per part or per month | **Resolution:** with fewer, the 99% interval of the edge cannot be expected to resolve the 0.05R materiality line (the M1 screen needed about 1,000 trades for a half-width of 0.05R). It decides whether Stage A's result may be read. The Stage A acceptance criteria of §4.4 are unchanged | Plan §4.4, before the outcome is read |
| **100 (minimum to interpret)** | (a) *Prospective:* the filled trades of the frozen **primary configuration** (F1, or B0 if nothing was selected) in 4a over the prospective horizon, and separately in 4b. (b) *Stage B:* the filled trades of one variant **after** its filter or change. (c) *Each chronological third of `DEVELOPMENT`* in Stage A: a third with fewer than 100 B0 trades is shown but not interpreted and does not count as a positive part | **Validity floor**, not a precision target: the [criteria §3](validation-criteria.md) minimum for `RESEARCH_VALIDATED` (100 filled trades over at least 60 sessions) and the plan's minimum for interpreting any variant | Plan §6, §7, §8 |
| **30 (cell)** | Trades in one regime or time cell | Show, do not interpret | Plan §5 |

How the first two interact in Stage C. The trade floor (100 filled trades in each of 4a and 4b, over at least 60 sessions) and the precision requirement (99% half-width of the gross edge at most 0.05R) are **both mandatory**; neither is sufficient alone. They are judged at 60 sessions and, if either fails, at the predeclared maximum of 120 sessions; if either still fails at 120 the result is `INCONCLUSIVE` and nothing further is permitted ([§8](#8-stage-c-prospective-validation)). Because the interval half-width scales with `1/√n`, the precision requirement in practice asks for a prospective trade count of the same order as Stage A's 1,000, but 1,000 is **not** a requirement. From M1 alone (not a result), about 0.4 trades per instrument-session would give on the order of 1,000 trades in 60 sessions of 50 instruments, so the extension may or may not trigger; the estimate will be replaced by the feasibility counts (P0-1b), if the owner approves them.

The two numbers therefore never compare like with like: 1,000 is a retrospective, pooled, B0-only, Stage A gate on resolution; 100 is a per-configuration minimum on prospective (or post-filter) trades for acceptance. The prospective data are required to reach 100 filled trades, 60 sessions and the precision rule of §8; they are **not** required to reach 1,000. **There is no separate fixed prospective trade floor beyond the 100 (owner direction, 2026-11-23).** Meeting the trade floor alone does not establish an edge; every predeclared acceptance criterion of §8 still applies.

### 4.6 Interval calibration (predeclared, not run)

**The problem (reassessment of finding F-1).** The prospective data provide few independent blocks: about 12 calendar weeks at 60 sessions and 24 at 120. Four limits follow, and the first three are not removed by more resamples.

1. **A block bootstrap draws only from the block means it has.** With `B` blocks every resampled mean is a weighted average of the observed block means, so it cannot fall outside their range. A 99% interval needs the 0.5% and 99.5% tails, which 12 observations cannot describe; the percentile interval is structurally narrow in the tails.
2. **The interval's own noise.** The standard error estimated from 12 block means has a relative error of roughly `1/√(2(B−1))`, about 21% at 12 blocks and 15% at 24, for well-behaved data; heavy tails make it worse. A half-width that sits near the 0.05R objective will flip either way by chance, and a percentile interval ignores the extra width a small-sample `t` interval would add. The known tendency is that coverage falls below nominal for small `B`; its size here is **not known and is not assumed**.
3. **Dependence.** The 50 instruments in a week share market-wide moves, so the unit of independence is the session or week, not the trade. Serial dependence between weeks (volatility clustering, trends) lowers the effective number of blocks below the nominal 12 or 24.
4. **Why 1,000 control replicates do not help.** The replicates reduce the Monte Carlo noise of the *control mean* (to the 0.005R target of §4.3); the 10,000 bootstrap resamples reduce the Monte Carlo noise of the *percentile*. Neither adds information about market-period variation, which comes only from the number and independence of the blocks. More replicates or resamples make a too-narrow interval more precisely too narrow.

**Candidate methods** (none is chosen; the provisional method of §4.3 and §8 is a placeholder):

| ID | Method | Note |
|---|---|---|
| M-1 | Week-block bootstrap, percentile (provisional) | 12 or 24 blocks |
| M-2 | Session-block bootstrap | 60 or 120 blocks; keeps the cross-section inside a block; ignores serial dependence |
| M-3 | Stationary bootstrap over sessions, mean block length chosen by a data-driven rule (Politis-White) | Adapts to dependence; the rule needs enough data |
| M-4 | Moving-block bootstrap with a fixed length (3 to 5 sessions) | Between M-1 and M-2 |
| M-5 | Studentised (bootstrap-t) versions of M-1 to M-4 | Better small-sample accuracy than percentile |
| M-6 | Cluster-robust `t` interval with clusters = sessions or weeks and `G − 1` degrees of freedom | Analytic; wider for small `G` |
| M-7 | Sign-flip randomisation on paired session or week differences, interval by inversion | No bootstrap-tail limit; assumes symmetry under the null |
| M-8 | Wild cluster bootstrap-t | Designed for few clusters |

**Predeclared calibration approach (to be run only after approval, before any freeze, on control trades and synthetic data only; no ORB result is used, so the edge is not exposed).**

1. *Null by construction on real windows.* From the `DEVELOPMENT` controls, build two independent matched control sets (pseudo-ORB and pseudo-control; true edge `0`, same matching and dependence). Cut windows of 60 and 120 consecutive sessions, start step 5 sessions. For each method record whether the interval covers `0`, its half-width, and whether the **decision rule** (edge `≥ +0.05R` with the lower bound above zero) fires falsely.
2. *Alternatives.* Repeat with a constant `+0.05R` and `+0.10R` added to the pseudo-ORB trades (true edge known): coverage of the true value, and power of the decision rule.
3. *Synthetic horizons with fitted dependence.* Fit the dependence of the session-level paired differences (serial correlation, cross-sectional clustering, tail weight) from the development controls, simulate at least 10,000 pseudo-horizons at 60 and 120 sessions, and measure coverage, half-width and the false-positive rate with a small Monte Carlo error.
4. *What can and cannot be verified.* The development data hold about 650 sessions, so there are only about 10 non-overlapping 60-session windows and 5 of 120. Coverage near 99% **cannot be verified from real windows**; they detect gross failure and supply the dependence estimates. The quantitative coverage statement comes from step 3 and holds only as far as its dependence model does. Overlapping windows are dependent and are reported with Clopper-Pearson limits that do not treat them as independent.
5. *Screening thresholds (accepted by the owner on 2026-11-23 as the **minimum screening criteria**):* in step 3, at **both** the 60- and the 120-session horizons, the empirical coverage of the 99% interval is at least **98.0%** and the false-positive rate of the decision rule is at most **1.5%**; in step 1, no gross failure (coverage at least 95% in the overlapping windows). **These are screening thresholds, not proof of real-world 99% coverage:** they show that a method is not anti-conservative under the simulated dependence structures, and they hold only as far as those structures do. Reporting is mandatory: (a) **nominal (99%) and observed coverage shown separately**, per method, per horizon and per scenario; (b) the **uncertainty** around every estimated coverage and false-positive rate (Clopper-Pearson limits for the binomial proportion, with overlapping windows flagged as dependent and not treated as independent, and the Monte Carlo error of the synthetic runs); (c) the 60- and 120-session results side by side; (d) **sensitivity** to the dependence structure (no, moderate and strong serial correlation; weak and strong cross-sectional clustering; the fitted structure) and to the volatility regime (low-, medium- and high-volatility periods of the development controls, and a volatility-clustering scenario). A method passes only if it meets both thresholds in **every** reported scenario, not on average. Among passing methods the one with the smallest median half-width at 60 sessions is a candidate; ties go to the fewest assumptions. **No interval method is selected or approved yet;** the method review is part of OD-15, which is open.
6. *If no method passes:* none is selected, the prospective interval stays undefined, and **the alternatives are returned to the owner** (for example a more conservative interval such as M-6, a longer horizon, which would change the protocol, or a lower nominal level with new thresholds). **The thresholds are not relaxed, and a failing method is never selected silently.** No replacement is chosen in this document.
7. The same calibration is applied to Stage A's interval (about 31 months of development data), with the same rules.
8. The chosen method, its parameters and the calibration report are part of the freeze package and cannot change afterwards.

## 5. Reporting for every experiment

Total, long and short (short `UNSUPPORTED`) trades; win rate; gross and net R and P&L; profit factor; expectancy; average winner and loser; maximum drawdown; streaks; holding time; by instrument, month, quarter, year; by regime; cost impact and the friction decomposition of the diagnosis; skip counts and rejection codes ([spec §13.2](../strategies/opening-range-breakout.md#132-rejection-conditions-question-i)); invalid-session counts by sub-reason; the three timestamps of each candidate; the data class; the run record of [standards §5.3](independent-backtesting-standards.md#53-run-record).

**Regimes, fixed now.** (1) 15m structure state at `t_BD`. (2) Gap band at the open: `g < −0.5%`, `−0.5%..+0.5%`, `> +0.5%`. (3) Range width: `0.30-0.50`, `0.50-1.00`, `1.00-2.00`. (4) Breakout time: before 10:00, 10:00-10:30, after 10:30. (5) Month and year. Under 30 trades in a cell: shown, not interpreted.

## 6. Statistics, multiple testing and selection bias

| Item | Rule |
|---|---|
| Effect | Mean R per trade, gross and net, planned-risk basis. For variants that change the trade set, the variant's mean R per trade against B0's, and the mean R of kept versus removed trades for a filter; counts always shown |
| Intervals | 99% month-block bootstrap, 10,000 resamples, seed 1 (provisional; the method is fixed by the calibration of §4.6) |
| Minimum sample | 100 trades to interpret a variant; 30 per cell |
| Materiality | An improvement under 0.05R net is not material, whatever its significance |
| **Tiers** | **Tier 1** (§7): the variant has a written mechanism and predicted sign, and can be selected. **Tier 2**: exploratory; reported with unadjusted intervals and labelled so; it cannot be selected and can only seed a new pre-registration |
| **Family-wise control (Tier 1)** | All Tier 1 variants (25) are tested jointly against B0 for the hypothesis "this variant improves net mean R per trade by at least 0.05R", with a max-statistic month-block bootstrap (White's reality check, with the Romano-Wolf step-down for the individual adjusted results), family-wise error 5%. Holm at 5% is the fallback if the bootstrap cannot be run |
| Predicted sign | Every variant records its predicted sign before the run. A result significant in the opposite direction is reported as `CONTRADICTS` and is not selectable |
| Consistency | The improvement must have the same sign in at least two of three chronological parts, and no part may carry more than half of it |
| Selection rule | **F1** = B0 plus every Tier 1 variant that passes (adjusted significance, ≥ 0.05R, consistent, ≥ 100 trades, predicted sign), at most one per rule dimension (one stop, one target, one window ...); within a dimension, the largest adjusted lower bound. If nothing passes, B0 is the only candidate |
| Selection bias | All retrospective data is `DEVELOPMENT`, so F1's in-sample effect is optimistic. Reported beside it: the number of variants tried (cumulative, §9), the mean of the max statistic under the bootstrap null (the optimism expected from picking the best of 25), and F1's result on `RESERVE` (supportive). **F1 is not validated by any of this**; §8 is the test |
| Interaction check | F1 is run once against B0 on `DEVELOPMENT` (not for selection). A leave-one-out on F1's components is descriptive and not counted as selection |
| Gross rule | A configuration whose gross expectancy is not positive cannot be rescued by the cost assumption ([criteria §1](validation-criteria.md)) |

## 7. Stage B: the pre-registered variant registry (38 variants)

Every row is one run against B0. Sign is the predicted change in net mean R per trade. IDs match the rule table of the specification. The 65-variant draft is cut to 38: dropped were fixed-R multiples other than 2.0 (target methods are the four of spec §12.4), no-target, buffer 0.20, fill-gap 0.15%, range-length and CF grids, and the leave-one-out and four-way combination blocks that had no pre-stated mechanism.

| ID | Rule | Change from B0 | Hypothesis (mechanism) | Sign | Tier |
|---|---|---|---|---|---|
| A1a | SC-01 | Range 5 minutes | A one-bar range is the auction spike; breaking it means less | − | 2 |
| A1b | SC-01 | Range 30 minutes | A longer range filters noisy breaks | + | 1 |
| A1c | SC-01 | Range 60 minutes | More meaningful but late | ? | 2 |
| A2 | SC-02 | Body basis | Removes auction-spike wicks, so the level is more relevant | + | 1 |
| A3a | SC-03 | Minimum width 0.5% | Stop distance is at least the width; friction in R falls (diagnosis DX-3) | + | 1 |
| A3b | SC-03 | Minimum width 1.0% | As A3a, stronger | + | 1 |
| A4 | SC-03 | Maximum width 1.5% | Wide ranges have spent the move and hit the stop gate when extended | + | 1 |
| A5a | SC-04 | Buffer 0 | No buffer admits marginal closes | − | 2 |
| A5b | SC-04 | Buffer 0.10% | Fewer marginal closes | + | 1 |
| A6a | SC-06 | Window 30 minutes | Late breakouts are weaker | + | 1 |
| A6b | SC-06 | Window to the cutoff | More trades, later ones weaker | − | 2 |
| A7 | SC-05 | Whipsaw invalidation off | A range lost on one side is not a clean range | − | 1 |
| B1 | EX-01 | Stop S-B (breakout-bar low) | Tighter risk raises the stop-out rate and friction share | − | 1 |
| B2 | EX-01 | Stop S-C (5m swing low) | Adapts to price action; few pivots exist early | ? | 2 |
| B3 | EX-01 | Stop S-D (range midpoint) | A nearer stop raises reward per R at the same target | ? | 1 |
| C-T2 | EX-02 | Existing ladder (T2) | Survivors have room beyond; many breakouts are removed | ? | 1 |
| C-T3a | EX-02 | Measured move k = 2 (T3) | The strategy's own range sets the target | ? | 1 |
| C-T3b | EX-02 | Measured move k = 3 | As above, farther | ? | 2 |
| C-T4 | EX-02 | Structural resistance (T4) | Exits in front of supply | ? | 1 |
| D1 | EX-05 | Failed-breakout exit | A close back inside the range cuts losers early | + | 1 |
| D2 | EX-09 | Time exit at 12 bars if +0.5R not reached | Stalled breakouts decay | ? | 2 |
| D3 | EX-10 | Structure exit on | The earlier study found structure exits gave back gains (D5) | − | 1 |
| E1a | CF-01 | 15m filter at `t_OR` | Context at the start decides if the setup is armed | ? | 1 |
| E1b | CF-01 | 15m filter at `t_BD` | Context at the breakout | ? | 1 |
| E1c | CF-01 | 15m filter continuous (today) | Today's behaviour | ? | 1 |
| E2 | CF-02 | Close location ≥ 0.70 | A close near the high shows no seller response | + | 1 |
| E3 | CF-03 | Displacement ≥ 0.25 widths | A marginal close is noise | + | 1 |
| E4 | CF-04 | Exclude gap < −0.5% | A gap-down open often fails | + | 1 |
| E5 | CF-04 | Exclude `|gap| > 0.5%` | Large gaps already hold the move | ? | 1 |
| E6 | CF-05 | 5m state not bearish | Trade with 5m structure | + | 1 |
| E7 | CF-06 | Range ≥ 15% of yesterday's range (after OD-5) | Energy stored in a relatively wide opening range | + | 2 |
| E8 | CF-07 | Headroom to PDH ≥ 1R | A level just above caps the move | + | 1 |
| E9 | CF-08 | Index 15m context (if data exists) | Stocks follow the index | + | 2 |
| E10 | CF-09 | Breakout-bar volume ≥ 1.0 × median (research only) | Participation behind the break | + | 2 |
| F1 | RC-03 | Extension cap 0.5 widths | A very extended close raises risk without moving the stop | + | 1 |
| F2 | RC-04 | Fill gap limit 0.15R | A fill far above the reference degrades the trade | + | 2 |
| K1 | pair | CF-02 + CF-03 | Breakout quality | + | 2 |
| K2 | pair | E1b + CF-05 | Structure agreement | + | 2 |

Totals: 38 variants (25 Tier 1, 13 Tier 2) plus the two references (B0, CUR) = 40 registered runs. Variants dependent on a pending decision (E7: OD-5; E9: OD-6, data; E10: research track) are dropped, not replaced, if the decision or data is missing. **No other variant is run;** a new idea is a new pre-registration with its own count.

**Order.** Each variant once, in registry order, against B0 only (never against another variant's chosen value). Then the selection rule of §6 builds F1 (or B0 alone).

**Frozen-configuration checks on `DEVELOPMENT` (stability, not validity):** walk-forward windows 120/40/40 sessions (`app/backtest/splits.py`) with no re-optimisation; year, quarter, regime and instrument cuts; parameter sensitivity of F1's values at ±25% and ±50% (sensitivity, not tuning); costs at 0.5x, 1x, 2x and slippage 0, 0.05, 0.10%; the friction decomposition; 4b under the account limits with the documented tie-break and a second tie-break re-run.

**`RESERVE` (OD-17, supportive).** F1 and B0 are run once on `RESERVE` with the matched control. A failure is reported and does not veto the prospective test; a pass is labelled retrospective.

## 8. Stage C: prospective validation

Only observations that did not exist when the configuration was frozen can validate it.

**Freeze package (written before the first prospective session, and not before the engineering prerequisites, the interval calibration, the pre-registration and this package are complete: no prospective capture, early log or sealed log starts earlier).** Git commit of the engine and harness; the research ruleset file and its SHA-256; this plan and the specification at their approved versions; the configuration to test (F1, or B0 if nothing was selected; B0 is always run alongside as the reference); the control generator, the 1,000 seeds, the matching tolerances, the interval method chosen by the calibration of §4.6 and its report, and the decision rules of this section; the data-quality masks; the **frozen instrument universe: the 50 instrument identifiers on the freeze date (no replacement, no removal; delistings, suspensions, corporate actions, index changes and outages stay in the dataset and are recorded)**. The freeze timestamp and the first prospective session `T0` (the first full session after the freeze) are entered in the registry. Nothing in the package changes afterwards.

**Capture.** The frozen detector runs on each session's closed bars after the close (batch replay is equivalent to bar-by-bar by the replay test). Each candidate (three timestamps, rule outcomes, levels, rejection reasons) is appended to an **append-only signal log** with the commit hash. A daily hash of each instrument-session's 5m, 15m and 1D bars is stored. Ingestion outages and invalid ranges are logged and removed **symmetrically** from ORB and the controls. Fills and exits are simulated by the frozen rules; if the owner also trades the signals, those are recorded separately and are not part of the test.

**Horizon, trade floor and precision (owner direction, 2026-11-23, clarified 2026-11-23).** Two requirements are **both mandatory**, and each is judged only at the two predeclared looks (60 and 120 sessions):

1. **Trade floor:** at least **100 qualifying filled trades** over at least 60 sessions, in each of experiments 4a and 4b for the frozen primary configuration ([criteria §3](validation-criteria.md)); the maximum horizon is 120 sessions. There is no separate, higher trade floor, and the floor is **not lowered after results are observed**. **Only qualifying filled trades count.** At every look the report keeps four things apart and counts them separately: (a) **qualifying signals** (a candidate of the frozen configuration in a valid session that passed every rule and risk check up to the fill); (b) **account-limit rejections** (4b only: a signal skipped by the account limits of `RC-05`, not a fill); (c) **actual fills** (candidates that passed the fill checks of `RC-04` and, in 4b, the account limits); (d) **`END_OF_DATA` exclusions** (trades still open when the data ended, reported and excluded from the statistics, L-8). The floor counts (c) minus (d) in each experiment. Signals, rejections and exclusions never count toward it.
2. **Precision:** the half-width of the 99% interval of the gross edge `Δ` (primary configuration, 4a) is at most 0.05R.

At **60 sessions** a width-only report gives the trade counts per experiment, the session count and the half-width. If both requirements are met, the single efficacy analysis is made at 60 sessions. If either is not met, the test continues to the predeclared maximum of **120 sessions**, and the single efficacy analysis is made once, at 120 sessions, on all prospective data. At **120 sessions**, if either requirement is still unmet, the result is classified **`INCONCLUSIVE`**, with the reason recorded as `INCONCLUSIVE_TRADE_COUNT` (fewer than 100 qualifying filled trades in 4a or in 4b by 120 sessions; the floor is not lowered), `INCONCLUSIVE_PRECISION` (half-width above 0.05R) or both. **No further extension is permitted under this protocol**, the horizon is never extended after inspecting results, and the data are not re-analysed to claim an edge. An `INCONCLUSIVE` result claims neither an edge nor a failure; the estimates may be reported descriptively. Any further collection is outside this protocol and needs a new pre-registration and a new owner decision; the sessions already observed are not unseen for it. Meeting the trade floor alone does not establish an edge: even when both requirements are met, all predeclared acceptance criteria below still apply. No look is taken between 60 and 120 sessions other than the integrity checks.

**Interim reporting restriction (unchanged).** Interim looks report data integrity, the trade and session counts and the **precision width only** (the half-width and the counts: no point estimate, no interval endpoints, no edge, no comparison with the control). The decision to extend therefore cannot be made on, or influenced by, the observed edge. The edge estimates and interval endpoints stay sealed until the single efficacy analysis, whether at 60 or at 120 sessions. (OD-16.)

**Interval for the prospective data (provisional; not a chosen method).** A bootstrap over calendar months would have about three blocks at 60 sessions and cannot be used. The provisional placeholder is the calendar-week block (five sessions: about 12 blocks at 60 sessions, 24 at 120), resampled as in §4.3 with the control averaged per week. **Its coverage at the 99% level is doubtful with so few blocks, for the reasons in [§4.6](#46-interval-calibration-predeclared-not-run), and no replacement is chosen here.** The method is fixed only by the predeclared calibration of §4.6, before the freeze, and is then part of the freeze package. The precision width is computed with that method. The 0.05R objective and the 99% level are unchanged.

**Hypothesis and decision.** Primary: the frozen configuration's gross edge `Δ` against the matched control (§4.2-4.3 with the week blocks above, generated at the end from the prospective sessions with the frozen seeds) is at least +0.05R with the 99% interval above zero, **and** the precision objective was met (half-width at most 0.05R at 60 or at 120 sessions). Then the acceptance criteria of [validation criteria §3](validation-criteria.md) are applied to prospective data, for experiments 4a and 4b: net expectancy above 0.10R, net profit factor above 1.2, drawdown at most 2x the development maximum, positive net expectancy in most blocks (consecutive 20-session blocks replace walk-forward windows), the 2x-cost condition, no single instrument, month or regime over half the result, isolation proof and complete run records. B0's result is descriptive. If the prospective window contains one market regime only, the result is labelled `LIMITED_REGIME`.

**Change control.** Any change to a rule, a parameter, code that affects outputs, the control procedure or the exclusions voids the run; it restarts with a new freeze and a registry row recording why.

**Meaning.** `RESEARCH_VALIDATED` needs this stage. `PAPER_TRADING_READY` additionally needs the other items of criteria §4 (verified costs, owner acceptance of the survivorship bias, owner approval); a prospective log produced under TRD-07 can serve as the forward log.

## 9. Preventing data snooping and repeated optimisation

| Safeguard | How |
|---|---|
| Freeze before running | Registry, controls, decision rules and assembly rule fixed at approval, written to the registry with a commit hash |
| Cumulative counter | One count of ORB variants ever tried, including the three M1 screens, printed beside every result and in the final decision |
| Stage A gate | Only A-CONTINUE runs the sweep (§4.4) |
| One change at a time, against B0 | No result is compared with another variant's chosen value |
| Two tiers | Only Tier 1 is selectable; Tier 2 is exploratory |
| Retrospective data nominates only | `DEVELOPMENT` and `RESERVE` never validate; only `PROSPECTIVE` does |
| No re-runs with changed grids | A variant is run once; a corrected run is a new row |
| Selection disclosure | Reported as selected, with the optimism estimate of §6 |
| Isolation | No other strategy's signal, score or exit enters any ORB run |
| Improvement rounds | At most three ([criteria §5](validation-criteria.md)), each with a hypothesis and a new pre-registration |

## 10. Per-rule validation matrix

| Rule | Validated by | Evidence that keeps the rule |
|---|---|---|
| `MG-01` to `MG-07` | Tests (boundary, each invalid-range sub-reason, look-ahead truncation, replay equivalence, one signal per session, cutoff, long-only); counts of exclusions per run | All tests pass. No performance test: these define the strategy |
| `SC-01` to `SC-03`, `SC-05`, `SC-06` | A1a-c, A2, A3a-b, A4, A6a-b, A7 | Tier 1 selection rule; if none passes, B0's value stays |
| `SC-04` | Tests; A5a-b for the buffer; Stage A for the idea as a whole | Stage A |
| `CF-01` | E1a, E1b, E1c (never combined) | Tier 1 selection rule |
| `CF-02` to `CF-09` | E2 to E10, K1, K2 | Tier 1 selection rule; Tier 2 exploratory only |
| `RC-01`, `RC-02`, `RC-04`, `RC-05` | Tests; skip counts and R effect; 4b | Shared; F2 is exploratory |
| `RC-03` | F1 | Tier 1 selection rule |
| `EX-01` | B1 to B3 | Tier 1 selection rule |
| `EX-02` | T1 (B0), C-T2, C-T3a-b, C-T4, each separate, with the common-trade comparison | Both views of spec §12.4 |
| `EX-03`, `EX-04` | Tests; the L-3 flag | Mandatory, shared |
| `EX-05`, `EX-09`, `EX-10` | D1 to D3 | Tier 1 selection rule |
| `EX-06` to `EX-08` | Not run (engine support, OD-8); offline only if an edge exists | — |

## 11. What Phase 3 will not do

Change any ruleset, PAQS weight or other strategy; promote anything to live; run other strategies with ORB; call any retrospective period blind; add variants after seeing a result; count a combined-strategy result; start before the owner approves this plan, the specification, the decision register and the engineering scope.

## 12. Deliverables of Phase 3

Registry pre-registration; pre-flight counts; the approved engineering prerequisites; the Stage A report; (if continued) the Stage B results, F1, stability and `RESERVE` checks; the freeze package; the prospective results; the acceptance decision on the strategy page §27 with the tracker, `CURRENT.md` and `TASKS.md` updated; owner review before the next strategy ([process §7](../development/strategy-development-process.md#7-sequential-rule)).

## 13. Open decisions that affect this plan

OD-14 (Stage A criteria), OD-15 (control design), OD-16 (prospective protocol), OD-17 (`RESERVE`), OD-5, OD-6 (testable context rules) and OD-8 (engineering scope); each is in the [register](../development/orb-phase2-decisions-and-readiness.md#2-owner-decision-register).
