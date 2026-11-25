# ORB Phase 2: Owner Decision Register and Readiness Assessment

| Field | Value |
|---|---|
| Version | 1.4.0 (2026-11-23, owner decisions on the Phase 3 readiness documentation applied) |
| Status | Phase 2 **APPROVED / COMPLETE** (2026-11-23). Phase 3 readiness review (T-I152): owner decisions of 2026-11-23 applied (§2.0). **Approved:** OD-14. **Accepted:** calibration screening thresholds, P0-1 (for separate execution, **not run**), trade-floor counting rules, the frozen prospective universe. **Open:** OD-8, OD-15. **Not approved:** OD-16 (owner prefers option (a)), P0-1b. Phase 3 implementation, engineering E1-E11, experiments, backtests and prospective capture are **NOT STARTED** |
| Related | [ORB specification](../strategies/opening-range-breakout.md) · [ORB validation plan](../research/orb-validation-plan.md) · [DEC-026](../../DECISIONS.md) · [Process](strategy-development-process.md) |

This page keeps two kinds of item apart:

- **Methodology decisions** change what ORB is or how it is judged. Only the owner decides them (§2).
- **Engineering prerequisites** are code, data and tooling needed to run the approved methodology in isolation. They change no trading rule (§3). Approving one is a scope decision (OD-8), not a methodology decision.

No application code, trading rule, PAQS weight or ruleset was changed to write this page.

## 1. How to read the register

"Needed before" uses four gates: **P2** (approval of the Phase 2 specification), **P3** (start of Phase 3, i.e. Stage A), **B** (start of Stage B), **C** (the Stage C freeze). "Default holds" means nothing is needed unless the owner wants a change.

## 2. Owner decision register

### 2.0 Status after the owner's approval of 2026-11-23

| ID | Decision | Status |
|---|---|---|
| OD-1 | B0 is the frozen reference | **APPROVED 2026-11-23** |
| OD-2 | 15-minute context filtering stays outside B0, as a separate experiment (E1a, E1b, E1c) | **APPROVED 2026-11-23** |
| OD-3 | Fixed 2R (T1) is B0's target; T2, T3, T4 remain separate experiments | **APPROVED 2026-11-23** |
| OD-7 | The documented `DEVELOPMENT`, exposed and `RESERVE` data classes | **APPROVED 2026-11-23** (the 2026-01-01..2026-11-19 ORB data is development data; `RESERVE` is retrospective and supportive only; only prospective data can validate) |
| OD-11 | First qualifying close-based breakout only (`FIRST_ONLY`) | **APPROVED 2026-11-23** |
| OD-13 | Wick-based opening-range calculation | **APPROVED 2026-11-23** |
| OD-8 | Engineering prerequisite scope (E1 to E8) | **Step 1 APPROVED (owner, 2026-11-25, [DEC-040](../../DECISIONS.md)): E1, E3, E7 only, implemented ([roadmap §8](orb-stage-a-finalisation-roadmap.md#8-od-8-step-1-execution-record-e1-e3-e7-2026-11-25)).** Steps 2-3 (E2, E4, E5, E6, E8, E10, E11) remain **OPEN and not authorised** |
| OD-14 | Stage A stopping and continuation criteria | **APPROVED 2026-11-23** with explicit counting populations: the 1,000-trade gate counts filled B0 trades of experiment 4a pooled across development data and all 50 instruments before any chronological split; controls, variants, prospective data and `END_OF_DATA` trades are excluded; the previously drafted Stage A acceptance criteria are unchanged; the prospective 100-trade floor is separate |
| OD-15 | Matched random-entry control design and interval method | **OPEN.** No matched-control implementation or validation before the interval-method review. No interval method is selected or approved. The calibration screening thresholds are accepted (OD-18) |
| OD-16 | Prospective validation protocol | **NOT APPROVED.** Owner preference recorded: **option (a), no early prospective log.** Capture requires, first: engineering prerequisites, interval calibration, pre-registration and the final freeze package |
| OD-18 | Calibration screening thresholds (coverage at least 98.0%, false-positive rate at most 1.5%) | **ACCEPTED 2026-11-23** as minimum **screening** criteria, not proof of real-world 99% coverage; uncertainty, nominal versus observed coverage, 60- and 120-session results and sensitivity to dependence and volatility must be reported; if no method passes, alternatives return to the owner and the thresholds are not relaxed; no method selected |
| OD-19 | P0-1 counts-only data-integrity scan | **EXECUTED 2026-11-23** (approved 2026-11-23 for separate execution; run once, independently reconciled). Exact output contract preserved; development data only. Its tick-dependent counts are not reliable; a post-remediation scan is conditionally approved (DR-8, [remediation page](orb-data-remediation.md#1-owner-decision-register-2026-11-23)), not run |
| OD-19b | P0-1b signal and fill counts | **NOT APPROVED** |
| OD-20 | Prospective trade-floor counting rules | **ACCEPTED 2026-11-23:** at least 100 qualifying filled trades and at least 60 sessions, 120-session maximum; only qualifying filled trades count; qualifying signals, account-limit rejections, actual fills and `END_OF_DATA` exclusions are distinguished; not met by 120 sessions means `INCONCLUSIVE`; the floor is not lowered after results |
| OD-21 | Prospective survivorship and the frozen universe | **ACCEPTED 2026-11-23:** the historical survivorship flag is cleared for the frozen prospective universe only; all 50 identifiers frozen; delistings, suspensions and unavailable instruments stay in the dataset; corporate actions, removals and outages recorded; no replacement; not generalised beyond the frozen universe; Stage A's historical limitation remains |
| OD-4, OD-5, OD-6, OD-10, OD-17 | Stage B choices | OPEN until Stage B; they are not needed for Phase 3 approval |
| OD-9, OD-12 | Short stays informational; retest is Strategy 11 | Default holds |

### 2.0.1 Register

The table below keeps the exact questions, options and consequences as reviewed. The approved options are the ones marked "Recommended" for OD-1, OD-2, OD-3, OD-7, OD-11 and OD-13.

All 15 earlier decisions are reviewed; OD-7 is rewritten per the review; OD-14 and OD-15 change content; OD-16 and OD-17 are new. Kind: M = methodology, E = engineering scope.

| ID | Exact question | Options | Recommended | Consequences | Needed before |
|---|---|---|---|---|---|
| **OD-1** (M) | Which configuration is the reference against which every ORB rule is measured? | (a) B0: range 15 min, close above the range, stop `OR_LOW`, fixed 2R, **no context filter**. (b) CUR: today's behaviour (15m lockout, target ladder, structure exit). (c) Both as co-references | (a) B0 as reference; CUR run once for fidelity, not in any decision | B0 needs new research code paths (E2-E5) and is not today's live behaviour, so its results do not describe the live scanner. With (b) the 15m lockout and the ladder would stay in the reference and most breakouts would be rejected before measurement | P2 |
| **OD-2** (M) | Is the 15m context filter part of ORB's own rules, or an experiment? | (a) Experiment only, off in B0, tested at three separate timestamps (E1a, E1b, E1c). (b) Own rule, on in B0 | (a) | Applies the review's item 6. With (b) B0 changes, E1a-c disappear, and the lockout question is untestable | P2 |
| **OD-3** (M) | What is B0's target? | (a) Fixed 2.0R (T1). (b) Existing ladder (T2). (c) Opening-range measured move (T3). (d) Structural resistance (T4) | (a), with T2, T3, T4 as separate experiments (never combined, spec §12.4) | (a) makes every valid breakout a trade and `min_rr` hold by construction, so the sample is large and the target does not select trades. (b)-(d) reject breakouts, so they need a common-trade comparison | P2 |
| **OD-4** (M) | Which stop methods are admitted as experiments? | (a) S-A only. (b) S-A baseline plus S-B, S-C, S-D | (b) | Three more registered variants (B1-B3); S-C depends on the structure engine and few pivots exist early, so it is Tier 2 | B |
| **OD-5** (M) | Is the ratio `OR width / previous-day range` a permitted price-action measure under MP-01? | Permit / forbid | Permit (one ratio of two OHLC ranges, no averaging) | Forbid drops E7 (37 variants). Permit needs reliable previous-day bars (L-5) | B |
| **OD-6** (M) | May an index (NIFTY 50) series be used as a context fact, if stored? | Allow if data exists / forbid | Allow if data exists | New cross-instrument dependency. If no series exists (pre-flight P0-2) E9 is `UNTESTABLE` and dropped | B |
| **OD-7** (M) | Confirm that all ORB data from 2026-01-01 to 2026-11-19 is development data, 2024 is partly exposed, and no document calls any retrospective period blind or holdout | (a) Confirm. (b) Treat part of 2026 as blind | (a) **Applied in the documents per the owner's review** | Retrospective data can nominate a configuration but never validate it; validation needs prospective data (about 3 months of waiting before any `RESEARCH_VALIDATED`). (b) would overstate the evidence | P2 (confirm) |
| **OD-8** (E) | Approve the scope of the engineering prerequisites E1 to E8 (§3) for Phase 3? | (a) Approve E1-E8 in steps. (b) Approve E1, E3, E7 only (fidelity and validation first). (c) Defer all | (b) first, then (a) | Code changes appear in the engine (new modules and tests, a new research ruleset); `0.1.0` and `0.5.0` stay untouched. With (c) no isolated ORB run exists and Phase 3 cannot start. **Status: OPEN; no engineering work is authorised** | P3 |
| **OD-9** (M) | Does the short side stay informational? | Informational / start research simulation (D-4) | Informational | No short work in ORB; short stays `UNSUPPORTED_DIRECTION`. A change needs D-4, D-9 and an ADR | Default holds |
| **OD-10** (M) | Form of the entry-gap limit | (a) 0.30% of the reference (today). (b) A fraction of the risk, 0.15R. (c) Both | (c): B0 keeps (a); (b) is the Tier 2 variant F2 | 0.30% is a third of a 0.9% stop, so a fill can degrade by about 0.33R before skipping. (b) is stricter and removes more trades | B |
| **OD-11** (M) | Which breakout is the signal? | (a) `FIRST_ONLY`: the first close above the trigger, rejected for the session if it fails a rule. (b) `FIRST_PASSING`: the first close that passes every rule | (a) | (a) removes the freedom to wait for a good bar and keeps ORB apart from retest and continuation logic; confirmations then act as filters on the one breakout. (b) changes B0 only slightly but adds a timing role and a hindsight freedom | P2 |
| **OD-12** (M) | Is a retest entry an ORB variant? | Separate strategy (Strategy 11) / ORB variant | Separate strategy | Keeps independence; the overlap of the `OR_HIGH` anchor is recorded for Strategy 11 | Default holds |
| **OD-13** (M) | Range basis and first bar | (a) Wick, all bars (today). (b) Body basis. (c) Exclude the first bar | (a) in B0, (b) as variant A2; (c) not registered | (c) is a different, shorter range and would need its own hypothesis | P2 |
| **OD-14** (M) | Approve the Stage A stopping and continuation criteria of [plan §4.4](../research/orb-validation-plan.md#44-stage-a-stopping-and-continuation-criteria-fixed-now-before-any-result), with the counting populations of [plan §4.5](../research/orb-validation-plan.md#45-what-the-sample-size-thresholds-count-clarification-2026-11-23)? | (a) As written: integrity gate; at least 1,000 filled B0 trades of experiment 4a pooled over all `DEVELOPMENT` data and all 50 instruments before any chronological split, excluding controls, variants, prospective data and `END_OF_DATA` trades; continue only if the gross edge `≥ +0.05R`, 99% lower bound `> 0`, gross mean R `> 0`, positive in two of three parts with at least 100 trades; stop when the upper bound `< +0.05R`; otherwise inconclusive. (b) Change a threshold. (c) Ungated sweep | (a) | The thresholds cannot change after Stage A runs. The gross-mean-R condition is biased upward on the historical universe (plan §2.4). **Status: APPROVED 2026-11-23**; the prospective 100-trade floor is separate | P3 |
| **OD-15** (M) | Approve the matched random-entry control of [plan §4.2](../research/orb-validation-plan.md#42-the-matched-random-entry-control-mtc) and its evaluation, with the interval method chosen only by the calibration of [plan §4.6](../research/orb-validation-plan.md#46-interval-calibration-predeclared-not-run)? | (a) As written (week and month blocks provisional; method chosen by calibration). (b) A simpler per-session control. (c) Keep the unmatched M1 control | (a) | (a) costs more engineering (E6) but avoids choosing an interval method without evidence. **Status: OPEN;** no matched-control implementation or validation until the interval-method review. The screening thresholds are accepted separately (OD-18) | P3 |
| **OD-16** (M) | Approve the prospective validation protocol of [plan §8](../research/orb-validation-plan.md#8-stage-c-prospective-validation)? | (a) 100 qualifying filled trades over 60 sessions in 4a and 4b and a 99% half-width of the gross edge at most 0.05R, both mandatory; judged only at 60 and 120 sessions; `INCONCLUSIVE` at 120 if either is unmet; no further extension; width-only interim reporting; universe frozen at the freeze; interval method from the calibration; **no early log; capture only after the engineering prerequisites, the calibration, the pre-registration and the final freeze package**. (b) A fixed 120 sessions. (c) Another horizon. (d) As (a) plus an early sealed B0-only log | (a) | About 12 weeks of daily capture after the freeze, up to about 24 if the second look is needed; needs live ingestion every trading day (E9). **Status: NOT APPROVED; owner preference for (a) recorded.** (d) is not preferred | P3 (design); the freeze date is set at C |
| **OD-17** (M) | How is the `RESERVE` segment (2025-09-24 to 2025-12-31, never seen for ORB) used? | (a) Once, as retrospective supportive evidence for F1 and B0. (b) Not used (kept for later strategies). (c) Reclassified as development | (a) | It is retrospective, so it can never count as blind or validate. It costs one run and gives an early, weak sanity check | B |

### 2.1 Decisions needed at each gate

| Gate | Decisions |
|---|---|
| **P2** (approve the specification) | OD-1, OD-2, OD-3, OD-7, OD-11, OD-13: **all approved 2026-11-23** |
| **P3** (start Stage A) | the P2 set (approved), OD-14 (approved), plus OD-8 (open), OD-15 (open), OD-16 (not approved) |
| **B** (start Stage B, only after A-CONTINUE) | OD-4, OD-5, OD-6, OD-10, OD-17 |
| **C** (freeze) | The freeze package of plan §8; E9 operating |
| Default holds | OD-9, OD-12 |

## 3. Engineering prerequisites for isolated ORB research

Minimum set to run the approved methodology in isolation, **without changing the trading methodology**. None is started; none is approved (OD-8). Existing ruleset files stay immutable (ADR-008).

| ID | Prerequisite | Why it is needed | Changes methodology? | Needed by |
|---|---|---|---|---|
| E1 | Register `opening_range_breakout` in the single-strategy registry (`app/domain/strategies.py`) with **today's detector unchanged** | No isolated ORB run exists; enables the isolation proof (P0-3) and the CUR run | No | Stage A |
| E2 | A new research ruleset (a new `pa-intraday` version, role `RESEARCH`, never `LIVE`) carrying the proposed `orb.*` keys; the role test and the hash check cover it | B0 and the variants need keys that do not exist; no released file may change | No | Stage A |
| E3 | A pure strict range validator (`ORB-MG-02`, sub-reasons, spec §7.1.2), used only by the B0 path | Today a missing bar silently changes the range | No (adds a gate for B0; CUR and live unchanged) | Stage A |
| E4 | A B0 detector path with switches: no 15m check, window and buffer parameters, the three evaluation timestamps stored on each candidate, and target modules T1 to T4 selectable one at a time | Context and targets must be separable experiments | No | Stage A (T1, no context); Stage B (the rest) |
| E5 | Run settings for B0: structure exit off, no score gate (the single-strategy mode already supports both), 4a without limits | Isolation (standards §3) | No | Stage A |
| E6 | The matched-control generator and statistics: seeded sampler on the same eligibility, entry-time and frequency matching, redraw rules, 4a and 4b replay, 1,000 replicates, month-block bootstrap, balance diagnostics, and (Stage B) the reality-check bootstrap | The control of plan §4.2 does not exist | No | Stage A |
| E7 | Tests: truncation equality, replay equivalence, the isolation proof, boundary tests per rule and per invalid-range sub-reason, TRD-08 vectors for the new rules | Stage 3 of the process; the ORB tests today are 8 and shared | No | Stage A |
| E8 | Registry and run-record extensions: data class labels, timestamps, cumulative variant counter, pre-registration file with commit and ruleset hashes | Plan §2, §9 | No | Stage A |
| E9 | Prospective capture: ingestion running every trading day (`INGEST_ENABLED`, daily broker login; not yet run live per `CURRENT.md`), append-only signal log, daily data hash, freeze manifest, outage log | Stage C needs data that does not exist yet | No | Stage C (operating before the freeze) |
| E10 | Data pre-flight scans (P0-1, P0-2): counts of invalid ranges by sub-reason, index availability, daily-bar coverage, duplicate and invalid bars | Decides which variants are testable | No | Stage A |
| E11 | A runtime benchmark for 1,000 control replicates | Decides whether `K` can stay at 1,000 (to be recorded before results) | No | Stage A |

Not prerequisites for Phase 3 and deliberately deferred: engine support for break-even, trailing and partial exits (`EX-06` to `EX-08`), short-side infrastructure, any change to PAQS or the live scanner.

## 4. Phase 2 readiness assessment

### 4.1 The owner's review items

| # | Revision requested | Where it is addressed | State |
|---|---|---|---|
| 1 | Classify 2026 exposed results as development data; no blind holdout language | Spec §25; plan §2 | Done in the documents (confirm OD-7) |
| 2 | Prospective validation with genuinely unseen observations | Plan §8 | Done; design needs OD-16 |
| 3 | Redesign the random-entry control (universe, sessions, entry times, frequency, direction, exits, costs, portfolio) and its evaluation | Plan §4.2-4.3 | Done; needs OD-15 and E6 |
| 4 | Separate target experiments with formulas | Spec §12.4; plan §7 (C-T2, C-T3a-b, C-T4 against T1) | Done |
| 5 | Strict range validation and invalid-session behaviour | Spec §7.1.2, `ORB-MG-02`; rejection codes | Done; needs E3 |
| 6 | Separate evaluation timestamps; B0 without context filters | Spec §10.4, §10.3; CF-01 split into E1a/b/c | Done |
| 7 | Minimum infrastructure for isolated research | §3 above | Done as a list; none built |
| 8 | Review all 15 decisions with the required fields | §2 above | Done; 17 decisions now |
| 9 | Review the 65 variants: pre-registration, hypotheses, multiple testing, selection bias | Plan §6-7: 38 variants, written hypotheses and signs, two tiers, family-wise control, optimism estimate | Done |
| 10 | Stage A stopping and continuation criteria | Plan §4.4 | Done; needs OD-14 |

### 4.2 Assessment

| Question | Answer |
|---|---|
| Is the specification complete and testable? | On paper, yes: every rule has a calculation, a pass/fail, a parameter and the evidence that keeps it. Nothing has been checked by tests or runs |
| Is it ready for owner approval? | **Done: approved 2026-11-23** with OD-1, OD-2, OD-3, OD-7, OD-11 and OD-13 as recommended. The ORB specification and B0 are frozen (spec freeze notice) |
| Is Phase 3 ready to start? | **No.** It is blocked by OD-8, OD-14, OD-15 and OD-16 and by the engineering prerequisites E1 to E8, E10 and E11 (none started) |
| What does approving Phase 2 authorise? | Adopting the specification and freezing B0 and its methodology. It does **not** authorise code, a ruleset, an experiment, a backtest or Phase 3, and it does not approve the validation plan (OD-8, OD-14, OD-15 and OD-16 are open) |
| Weaknesses that remain | Every retrospective result is optimistic; the only decisive evidence is prospective and needs about 12 weeks after the freeze; costs and slippage are unverified (D-6); the prior (M1 and the daily screen) is negative, so the most likely Stage A outcome is a stop, which the plan accepts |
| What could change the plan | Pre-flight P0-1 and P0-2 (invalid-range counts, index and daily coverage), the runtime benchmark E11, and the owner's answers |

### 4.3 Remaining owner decisions

**Open for Phase 3 approval:** OD-8, OD-15; OD-16 not yet approved (option (a) preferred). **Approved:** OD-14.
**Open until Stage B (only if Stage A continues):** OD-4, OD-5, OD-6, OD-10, OD-17.
**Defaults hold unless changed:** OD-9, OD-12.

### 4.4 Next milestone: Phase 3 readiness review

Done as T-I152 (documentation only): see §5. Nothing runs until the owner approves Phase 3.

## 5. Phase 3 readiness review (T-I152, 2026-11-23)

Scope: documentation review only. Reviewed: the frozen [ORB specification](../strategies/opening-range-breakout.md), the [validation plan](../research/orb-validation-plan.md), this register, the standards and criteria they rely on, and the code facts recorded in the specification. No code, PAQS, released ruleset, other strategy or B0 element was changed. Nothing was run.

### 5.1 Findings

| ID | Finding | Severity | Action |
|---|---|---|---|
| F-1 | **Reassessed.** The prospective interval is **not solved** by week blocks. About 12 blocks at 60 sessions and 24 at 120 cannot describe the 99% tails (a block bootstrap cannot leave the range of the block means; the estimated standard error is itself uncertain by about 21% and 15%; weeks are not independent; 1,000 control replicates and 10,000 resamples reduce only Monte Carlo noise). Coverage at the 99% level is doubtful and its size is unknown | High (plan defect, open) | Plan §4.6 lists eight candidate methods (M-1 to M-8), keeps the week block only as a **provisional placeholder**, and predeclares a calibration (null by construction on controls, injected edges, synthetic horizons with fitted dependence, acceptance thresholds, a fallback to the owner). **No replacement is chosen.** Not run |
| F-2 | **The 60-session precision check would reveal the result.** Computing a half-width normally shows the interval and the estimate, so the decision to extend could be made on the edge | High (selection risk) | Plan §8: a width-only report (half-width and counts only); edge estimates sealed until the single efficacy analysis |
| F-3 | The horizon, floor and precision rules | Applied (revised) | Plan §8, §4.5: both the trade floor (100 filled trades over 60 sessions, in 4a and in 4b) and the precision requirement are mandatory; judged only at 60 and 120 sessions; at 120 an unmet requirement is `INCONCLUSIVE` (`INCONCLUSIVE_TRADE_COUNT`, `INCONCLUSIVE_PRECISION` or both); no further extension; the floor alone proves nothing. B0 unchanged |
| F-4 | Under the owner direction a wide interval is `INCONCLUSIVE` even when the point estimate is negative | Informational | Descriptive reporting is allowed; no edge and no failure is claimed from it. No change |
| F-5 | The two universes were not kept apart | Resolved by owner decision (OD-21, 2026-11-23) | Plan §2.4: Stage A keeps the historical survivorship limitation; the prospective universe is the 50 frozen identifiers, no replacement, delistings and outages kept in the dataset; the flag is cleared for the frozen prospective universe only and is not generalised |
| F-6 | The 1,000-trade gate depends on how many B0 trades exist | Accepted risk (owner, 2026-11-23) | P0-1 is approved for separate execution as a counts-only integrity scan (not run). **P0-1b is not approved**, so the gate is checked only when Stage A runs; a shortfall halts Stage A as `INSUFFICIENT_SAMPLE` |
| F-7 | **Timeline.** Prospective validation can only start after a freeze, which comes after Stage A (and Stage B if it continues). Realistically a first `RESEARCH_VALIDATED` needs: engineering, Stage A, possibly Stage B, then 12 to 24 weeks | Planning | OD-16 option (d): a B0-only prospective log, sealed, could start once E9 is ready, because B0 is frozen. It must stay sealed so it cannot steer Stage A or B |
| F-8 | **E9 depends on a manual step.** Ingestion has not run live (`CURRENT.md`); the broker login is needed each trading day. A missed day lowers the prospective count and lengthens the calendar | Medium | Outages are removed symmetrically (plan §8). Owner to confirm that daily capture is practical before the freeze |
| F-9 | Costs and slippage stay unverified (D-6); every result carries `costs_unverified` | Known, not blocking Stage A | Verification is needed before `PAPER_TRADING_READY` (criteria §4) |
| F-10 | The late-session bars missing since 2026-08-03 (L-3) affect exits held to 15:15 in development data | Known | Flagged per run (plan §2.3); prospective capture will show whether the gap persists |
| F-11 | Plan arithmetic checked: 38 variants (25 Tier 1, 13 Tier 2) plus B0 and CUR; spec rule IDs match the plan's matrix; B0 appears identically in the spec §10.3 and the plan | OK | None |
| F-12 | The plan's Stage A criteria apply only to B0; CUR does not enter any decision | OK | None |
| F-13 | **Stage A has the same block problem in milder form:** about 31 development months are 31 blocks | Medium | Plan §4.6 step 7: the same calibration applies to Stage A; month blocks are provisional |
| F-14 | The trade floor applies to 4a and 4b, and 4b under account limits may produce fewer than 100 trades | Resolved by owner decision (OD-20) | The floor counts only qualifying filled trades; signals, account-limit rejections, fills and `END_OF_DATA` exclusions are reported separately; not met by 120 sessions is `INCONCLUSIVE`; the floor is not lowered |
| F-15 | A calibration of the interval could expose the edge if it used ORB trades | Controlled | Plan §4.6 uses control trades and synthetic data only; the width-only interim restriction is unchanged |

### 5.2 Outstanding prerequisites

| Prerequisite | State |
|---|---|
| Owner decisions | OD-14 **approved**; OD-8 and OD-15 **open**; OD-16 **not approved** (option (a) preferred); OD-18 to OD-21 accepted; OD-19b not approved (§2.0) |
| E1 to E11 ([§3](#3-engineering-prerequisites-for-isolated-orb-research)) | **E1, E3 and the step-1 part of E7 IMPLEMENTED (2026-11-25)**; the rest NOT STARTED and not approved. Order: then E2, E4, E5, then E6, E8, E10, E11. **E9: design only; no capture before the freeze package (OD-16, option (a))** |
| Pre-flight | **P0-1 approved for separate execution, not run** (explicit instruction needed); P0-1b not approved; P0-2 to P0-5 not run |
| Pre-registration text for the registry | Not written; written after Phase 3 approval, with the plan's commit hash |
| Cost schedule verification (D-6) | Open; not needed before Stage A |
| Phase 3 implementation, experiments, backtests, prospective validation | **NOT STARTED** |

### 5.3 Decisions presented for final owner review (not approved)

Each states the exact approval being asked. Selecting an option is the owner's act; none is marked approved.

| ID | Exact approval requested | What approving means | What it leaves open |
|---|---|---|---|
| **OD-8** | Approve the scope of E1 to E8 for Phase 3 in the suggested order, under a new research ruleset; E9 to E11 scoped separately | Engine changes (registration, strict range validator, B0 path, tests, registry extensions) | **OPEN. No engineering work is authorised.** |
| **OD-14** | Stage A criteria and counting populations (plan §4.4, §4.5) | The thresholds are fixed before any result and cannot change after Stage A runs | **APPROVED 2026-11-23.** Whether B0 reaches 1,000 is known only at Stage A (P0-1b not approved); a shortfall halts Stage A as `INSUFFICIENT_SAMPLE` |
| **OD-15** | Matched control and interval method (plan §4.2, §4.6) | Not assumed | **OPEN.** Thresholds accepted as screening criteria (OD-18); no method selected; no implementation or validation |
| **OD-16** | Prospective protocol (plan §8) | The wording of the plan, with the owner's counting rules (OD-20) and frozen universe (OD-21) | **NOT APPROVED.** Preference: option (a), no early log |

### 5.4 Readiness verdict

**Documentation reflects the owner decisions of 2026-11-23.** One High finding stays open on purpose: the interval method (F-1) is chosen only by calibration after the OD-15 review. Phase 3 is **not ready to start**: OD-8 and OD-15 are open, OD-16 is not approved, and the engineering prerequisites E1 to E11 do not exist. Approving OD-8, OD-15 and OD-16 would still not start any step until the owner approves Phase 3 itself. P0-1 may run, separately, on the owner's explicit instruction.

### 5.5 Owner decisions applied and what remains

**Applied 2026-11-23:** the calibration screening thresholds (OD-18); P0-1 approved for separate execution and not run (OD-19); P0-1b not approved (OD-19b); the trade-floor counting rules (OD-20); the frozen prospective universe and the clearing of the survivorship flag for it only (OD-21); OD-14 approved with its counting populations; OD-16 not approved with option (a) preferred.

**Still open (no action authorised):** OD-8 (engineering scope); OD-15 (control design and interval-method review). **Not yet decided:** the interval method (none selected); OD-16 approval.

**Before P0-1 runs:** the owner's explicit instruction. P0-1 produces counts only under the output contract of plan §3, on development data, with no signal or trade counts.

**Before any prospective capture:** engineering prerequisites, interval calibration, pre-registration and the final freeze package, in that order of dependency; no early or sealed log.

**Question left for the owner:** none new. If the calibration finds no passing method, the alternatives return to the owner and the thresholds are not relaxed.
