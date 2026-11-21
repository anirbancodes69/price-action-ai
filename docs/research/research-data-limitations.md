# Research Data Limitations

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Status | Current. Facts come from the [research readiness audit](adaptive-strategy-validation/RESEARCH_READINESS.md) (2026-11-21); that report holds the evidence and queries |
| Date | 2026-11-21 |
| Related | [Independent backtesting standards](independent-backtesting-standards.md) · [Validation criteria](validation-criteria.md) · [Experiment registry](experiment-registry.md) |

The audit describes the database and code on 2026-11-21. **Re-verify the relevant rows before each experiment**; several have open tasks and may change.

## 1. Known limitations

| ID | Limitation | Required handling in every experiment | Open item |
|---|---|---|---|
| L-1 | **Survivorship bias.** Historical NIFTY 50 membership is unavailable for 2024-2026. The universe is today's 50 names applied to all earlier years (membership dated 2026-09-01) | Flag `survivorship_bias_risk`. Never claim point-in-time accuracy. Describe results as biased | OQ-BT-01, D-6 |
| L-2 | **Instrument mappings and symbol changes** (for example ETERNAL and TMPV are stored under today's names; no `SYMBOL_CHANGE` records) | Record the mapping used; check each symbol's identity across the period | Audit §B.2 |
| L-3 | **Missing late-session candles.** From 2026-08-03, 75 sessions lack the last three 5m bars (15:15-15:25) and the last 15m bar. Earlier sessions have them. Cause undetermined | Do not treat the sessions alike for anything computed from the last 15 minutes. Record the regime break | Audit §B.3 |
| L-4 | **Special sessions** (Saturdays 2024-03-02 and 2024-05-18 are partial; Muhurat evenings 2024-11-01 and 2026-11-08; a short session 2025-10-21; three full-length weekend sessions) are replayed with normal hours | Exclude the five partial or evening sessions, or model their hours. Record the exclusions. **Single-strategy runs now do this** (`SPECIAL_SESSIONS` in `app/backtest/exclusions.py`: removed from the replay, the lookback window and the previous-day lookup; each run prints the exclusions). The list is a harness constant until the verified calendar exists | T-I137, audit §B.5 |
| L-5 | **Previous-day levels.** The loader derives PDH/PDL/PDC from the previous session's 5m bars. After 2026-08-03 PDH differs from the official daily bar in about 9% of sessions. Daily bars exist only from 2026-01-01 | Use a reliable daily source for PDH/PDL, or exclude the affected sessions. Never use incomplete sessions to calculate daily levels. **Single-strategy runs now use the previous full session's 1D bar**; an instrument-session without it is left out and recorded as `MISSING_PREV_DAY_LEVELS`. Effective once the 1D bars for 2024-2025 are loaded (pending) | T-I138, D-7 |
| L-6 | **Corporate actions and demergers.** Split and bonus history is provider-adjusted (contradicting TRD-06 §6); the TMPV demerger on 2025-10-14 is not adjusted; `corporate_actions` is empty and no exclusion exists | Exclude lookbacks that contain a known unadjusted event; record each exclusion | OQ-BT-03, audit §B.6 |
| L-7 | **Costs and slippage are unverified**, and one schedule is used for the whole period. Exit slippage is applied to stops and not to other exits | Document the schedule; apply adverse slippage consistently to all exits; label results `costs_unverified` | OQ-BT-02, D-6 |
| L-8 | **End-of-data trades** are excluded from statistics but included in the equity curve | Reconcile statistics with the equity curve, or report both | Audit R-8 |
| L-9 | **Short-side infrastructure** is not validated: entry, exit, sizing and replay are long-only | Report short results as `UNSUPPORTED_DIRECTION`. No short claim without D-4 and validated infrastructure | D-4, D-9 |
| L-10 | **No 1-minute history.** Collisions resolve against the trader | Report that intrabar order is unknown; results are a conservative bound | OQ-BT-07 |
| L-11 | **Gaps and anomalies** (seven instrument-sessions with missing bars; zero-volume bars; no quality check on history; `data_quality_issues` empty) | Mask or exclude affected instrument-sessions; list them in the run record | T-I136 |
| L-12 | **One market period.** 717 sessions are one continuous sequence of regimes | Count regimes, not only sessions, before regime claims | Audit R-13 |
| L-13 | **Run reproducibility.** `backtest_runs` is empty; earlier variants used an unrecorded script | Every run recorded in the [registry](experiment-registry.md) with configuration, commit, range and exclusions | Audit R-11 |
| L-14 | **Look-ahead tests** for all setups are not yet machine-checked end to end (only the sweep has a truncated-data test) | Add a truncation-equality test per strategy ([process §4](../development/strategy-development-process.md#4-functional-testing-standard-stage-3)) | T-I139 |

## 2. Data integrity rules

1. Never silently fill missing historical data.
2. Never claim point-in-time universe accuracy without historical membership.
3. Never use incomplete sessions to calculate daily levels.
4. Exclude or correctly model special sessions.
5. Record corporate-action exclusions.
6. Document all transaction cost assumptions.
7. Use identical assumptions for comparative experiments.
8. Report unsupported directions and timeframes explicitly.
9. Record data-quality issues for every experiment.
10. Do not describe biased results as unbiased historical evidence.

If a data limitation prevents a reliable conclusion, mark the experiment accordingly (the flags in [standards §5.3](independent-backtesting-standards.md#53-run-record)). Do not quietly drop the limitation from the report.

## 3. Flags

| Flag | Set when |
|---|---|
| `survivorship_bias_risk` | The universe is not point-in-time (L-1). Currently always set |
| `short_history` | Fewer than 120 sessions (TRD-06 §3) |
| `costs_unverified` | The schedule or slippage is an assumption (L-7). Currently always set |
| `calendar_unverified` | Holidays or special sessions are not verified (L-4) |
| `NOT_ISOLATED` | The run did not use the single-strategy run mode (standards §3) |
| `UNSUPPORTED_DIRECTION` | A direction was not simulated because the infrastructure does not support it |
