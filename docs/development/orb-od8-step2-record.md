# ORB OD-8 Step 2: execution record, findings and proposals

Date: 2026-11-25. Branch `feat/phase1-stabilization`, HEAD `a33bb83`, all work uncommitted. This record is **AI-assisted and NON-INDEPENDENT**. It is not an independent human review (DR-7a) and does not extend DR-11. Authority: owner decisions D1 to D8 of 2026-11-25 ([DEC-041](../../DECISIONS.md)). Context: [roadmap](orb-stage-a-finalisation-roadmap.md), [readiness](orb-phase2-decisions-and-readiness.md).

> **Update (DEC-045, 2026-11-25):** an owner-approved solo-research exception to DR-7a was recorded after this record ([DR-12](orb-data-remediation.md#211-dr-12-dr-7a-solo-research-exception-owner-approved-2026-11-25)). The table below is the state when Step 2 was implemented. The exception is not an independent review and does not complete the open items.

## 1. Governance gate (checked before implementation)

| Record | State | Consequence |
|---|---|---|
| DR-7 | Curated reference data needs a preparer **and** a separate independent human reviewer before it is loaded | Applies to the tick, corporate-event and session-facts tables (D2, D5, D6) |
| DR-7a | Reviewer unnamed, **OPEN** | No curated table can be marked `INDEPENDENTLY_REVIEWED` |
| DR-11 | AI-assisted plus owner review, **D1 only** | The 2026-11-25 message is not an extension; no written extension exists |

Result: **blocked** are (a) every edit of a frozen specification (ORB spec §7.1.2 / `ORB-MG-02` row / metadata / freeze notice, validation plan §3, TRD-04 §3, assigning 0.6.0 in spec metadata); (b) the use of any real curated table as a research input. **Unblocked and done:** the engineering mechanism, fixtures, the ruleset file and tests. The loader refuses an unreviewed table by default (`require_reviewed=True`; only `INDEPENDENTLY_REVIEWED` passes), so the block cannot be bypassed by accident. No real table was created, so there are no tick, event or session-table hashes yet.

## 2. What was built (dependency order of D8)

1. **Tick table and resolver** (`app/domain/ticks.py`): `TickResolution = RESOLVED(value, basis) | UNKNOWN(reason)`; duplicate, overlapping or conflicting rows fail the load; no coverage gives `UNKNOWN`, never 0.05. Resolver version `tick-resolver-1.0.0`. Loaders in `app/backtest/reference_tables.py` check the pinned SHA-256, the `kind` and the review status.
2. **E2 ruleset `pa-intraday 0.6.0`**: `0.5.0` with `exit.structure_exit_enabled=false` and `orb.range_basis=WICK`, `orb.breakout_window_minutes=60`, `orb.requalify=FIRST_ONLY`, `orb.stop_method=S-A`, `orb.target_method=FIXED_R`, `orb.target_k=2.0`. Role RESEARCH. Seeder copy byte-identical; hash tripwire and integrity tests extended. No T2 to T4, BODY, context-filter or Stage B key.
3. **E4 B0 detector** (`app/domain/setups/orb_b0.py`, strategy id `orb_b0`): separate from `detect_opening_range`; calls the frozen `validate_opening_range`; long only; no context filter; whipsaw invalidation; 60-minute window; first breakout only; unsupported parameter values raise `UnsupportedOrbParameter`. B0 levels in `app/domain/levels.py::orb_b0_levels` (stop S-A, target `down(E + 2R)`, tested against `min_rr` on the nominal multiple).
4. **E5 eligibility** (`app/backtest/b0_eligibility.py`, loader hook `b0=`): one decision per instrument-session shared by ORB and controls (`EligibilityMap`); reasons `SESSION_HOURS_UNKNOWN`, session-table exclusion (2024-01-20), `L6_EVENT`, `L6_EVENT_UNRESOLVED`, `PROVIDER_RATIO_STEP` (0.5 %, only when no event row explains it), `TICK_UNKNOWN`, `OR_*`, `TICK_MISALIGNED`. MG02-A1 classification (four statuses; only a verified fail invalidates). Provider-adjusted sessions run with `tick=None`, no rounding, note `TICK_ROUNDING_NOT_APPLIED`. The B0 loader path never reads `instrument_snapshots` or a session default. Run record gains `reference_data` (table hashes, resolver version).
5. **E7 tests**: see the completion report.

Widened (behaviour unchanged for a `Decimal` tick): `SymbolData.tick`, `RiskRequest.tick_size`, `entry_up`, `down_to_tick`, `validate_stop` accept `None` (no rounding).

## 3. Findings

- **F-1 (design interaction, needs an owner decision, B0 not changed).** The fixed target is `T1 = down(E + 2R)` from the signal close `E`; `ORB-RC-04` skips a fill whose reward-to-risk is below `min_rr = 2.0`; the fill is the next open plus 0.05 % entry slippage. rr at the fill is below 2.0 whenever the fill is above `E`, so a flat or higher open gives `SKIPPED_RR_DEGRADED`. Only an open at least 0.05 % **below** the signal close trades. The B0 population would be a strongly selected, gap-down-biased minority, not the breakout population the hypothesis describes. Pinned by `test_finding_f1_...`. Options for the owner (not applied): (a) take `T1` from the fill; (b) apply RC-04 to the nominal rr; (c) a tolerance in R units (OD-10); (d) keep as is and report the skip rate as the primary result. This must be decided before any historical run.
- **F-2.** `loader.tick_and_lot` (default 0.05) and `session_spec` (default 15:30) remain for the legacy path, pinned by an existing test. The B0 path does not call them. The Kite ingestion default and the diagnostics `TICK` constants are separate follow-ups (D2).
- **F-3.** The ratio-step definition (daily close divided by last 5m close, change between consecutive sessions, above 0.5 %) is my interpretation of D5; it needs review.
- **F-4.** Chunked runs do not persist `reference_data` yet; a chunked B0 run needs that before it is authorised.

## 4. Sensitivity analyses (prepared, not run)

- **Broader exclusion (D5):** rerun the B0 evaluation excluding every instrument-session within 5 sessions of any event row (any type, any status) and every whole company with an `UNRESOLVED` row; report ORB-minus-control for the primary and the broader population, labelled "sensitivity, not primary".
- **Price basis (D3):** all eligible sessions versus traded-scale-only sessions; report the count and the effect of `TICK_ROUNDING_NOT_APPLIED` sessions for both arms.

## 5. Reconciliation proposal for the sample-size conflict (owner decision needed; nothing resolved here)

The documents state a 1,000 pooled-trade requirement, a 100-trade-per-subgroup floor, a 60 to 120 session window and no early log. Proposal: (1) keep the 1,000 pooled trades as the confirmation threshold and the 100-trade floor as the minimum for any reported subgroup; (2) treat 60 to 120 sessions as the minimum **prospective capture** length, not as a stopping rule; (3) forbid any early look at outcomes (no early log) until the pre-registered stop; (4) state that F-1 can cut the trade count by an order of magnitude, so the session count needed is only known after F-1 is decided and the skip rate is measured on the development data (which needs a backtest authorisation). Not adopted until the owner decides.

## 6. Remaining before a historical backtest can be authorised

1. Owner decision on F-1.
2. A named independent reviewer (DR-7a) or a written extension; then the real tick, event and session tables, reviewed and hash-pinned; the price-basis matrix as a pinned table.
3. Spec amendments after review: MG02-A1, session facts, ruleset 0.6.0 metadata.
4. The control arm implementation that consumes `EligibilityMap` (E6, not authorised here); persistence of `reference_data` in chunks.
5. A separate explicit authorisation to run.
