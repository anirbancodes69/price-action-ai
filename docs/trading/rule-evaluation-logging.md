# Rule Evaluation Logging Specification

| Item | Value |
|---|---|
| Status | Implemented as a read-only layer (Phase 1 P5, 2026-11-23); wired into the backtest replay, not yet persisted or exposed by an API |
| Code | `python-engine/app/domain/audit.py` (`build_decision_records`, `DecisionRecord`, `RuleEvaluation`), hook `decision_sink` in `app/backtest/replay.py` |
| Tests | `tests/trading/test_audit.py` (11) |
| Guarantee | The records *describe* an `AnalysisResult` and the `RiskResult`; nothing reads them back, so entry, exit, PAQS weights, the minimum score and the decision mechanism are unchanged. A test replays a session with and without the sink and asserts identical trades and skips |

## 1. What is recorded

One `DecisionRecord` per evaluated setup on a closed 5m bar, or one `NEVER_DETECTED` record when the bar produced no setup.

| Field | Meaning |
|---|---|
| `schema_version`, `instrument`, `bar_end` | Format version, symbol, the closed bar the decision was made on |
| `strategy_id` | Setup type; `null` only for `NEVER_DETECTED` |
| `ruleset`, `ruleset_hash` | `"<code> <version>"` and the SHA-256 of the exact values |
| `market_context` | `htf_15m_state`, `structure_5m_state` |
| `lifecycle_state` | FORMING, AWAITING_CONFIRMATION, ENTRY_CONFIRMED, INVALIDATED, EXPIRED |
| `outcome` | see §2 |
| `final_signal` | NO_TRADE, BUY_WATCH or ENTRY_CONFIRMED for the primary setup; `null` for the others |
| `final_rejection_reason` | The engine's reason codes (`LOW_SCORE`, `RR_BELOW_MINIMUM`, ...) joined with `;`, the risk error, the end reason, or `OUTRANKED` |
| `entry`, `stop`, `target`, `position_size` | Planned levels and the planned quantity when the caller ran the risk check |
| `paqs_total`, `paqs_version`, `paqs_components` | The score and each component (name, points, maximum, missing, reason) |
| `rules` | Ordered `RuleEvaluation` list, §3 |

## 2. Rejected versus never detected

| `outcome` | Meaning |
|---|---|
| `NEVER_DETECTED` | No detector produced a setup. The single `SETUP_DETECTED` rule is FAIL with the detectors' reasons |
| `TERMINATED` | Detected, then INVALIDATED or EXPIRED (`final_rejection_reason` is the end reason) |
| `INFORMATIONAL` | A short setup (SD-06): shown, never actionable |
| `NOT_SELECTED` | Live and long, but another setup was the primary (`OUTRANKED`) or its confirmation was stale |
| `REJECTED` | The primary and at least one mandatory gate failed (`NO_TRADE`) |
| `WATCH` | The primary, all gates passed, entry trigger not yet closed (`BUY_WATCH`) |
| `ENTRY_CONFIRMED` | The primary, all gates passed |
| `RISK_REJECTED` | The engine said ENTRY_CONFIRMED or BUY_WATCH but the risk check refused the plan |

## 3. Rule evaluations

Each: `rule_id`, `description`, `stage` (DETECTION, LIFECYCLE, SELECTION, SIGNAL_GATE, RISK), `classification` (`MANDATORY` fail stops the setup, `CONFIRMATION` decides ENTRY_CONFIRMED versus BUY_WATCH and is never a rejection, `INFORMATIONAL`), `result` (`PASS`, `FAIL`, `NOT_APPLICABLE`), `inputs`, `thresholds` (strings, read from the ruleset), `failure_reason`.

| `rule_id` | Stage | Class | Source of truth |
|---|---|---|---|
| `SETUP_DETECTED` | DETECTION | mandatory | the detector output |
| `SETUP_LIFECYCLE` | LIFECYCLE | mandatory | `Setup.status`, `end_reason` |
| `DIRECTION_LONG` | SELECTION | mandatory | SD-06 |
| `SELECTED_AS_PRIMARY` | SELECTION | mandatory | `_eligible` and the TRD-04 §12 ordering |
| `PAQS_MINIMUM` | SIGNAL_GATE | mandatory (informational when no score, isolated runs) | `score.watch_threshold` |
| `RR_MINIMUM` | SIGNAL_GATE | mandatory | `risk.min_rr`, `NO_TARGET` |
| `BEFORE_ENTRY_CUTOFF` | SIGNAL_GATE | mandatory | `session.entry_cutoff_minutes_before_close` |
| `ENTRY_CONFIRMED` | SIGNAL_GATE | confirmation | setup status |
| `RISK_STOP_DISTANCE`, `RISK_MIN_RR`, `RISK_ACCOUNT_LIMITS`, `RISK_SIZING`, `RISK_STOP_BELOW_ENTRY`, `RISK_TARGET_ABOVE_ENTRY`, `RISK_CHECK` | RISK | mandatory | `RiskResult` (one rule, named by the first error) |

The three signal gates are evaluated by `choose_signal` for the primary only, so they are `NOT_APPLICABLE` for every other setup. When several gates fail at once every failing rule is reported.

## 4. Extending to a new strategy

Register a provider: `RULE_PROVIDERS["MY_SETUP"] = lambda setup, analysis: [RuleEvaluation(...)]`. Its rules are appended to that strategy's records with no change to the builder (test: `test_a_strategy_can_register_extra_rules_without_touching_the_builder`).

## 5. Wiring and limits

- Backtest: `replay_session(..., decision_sink=callable)` receives the records at every bar close, with the risk result of the primary when it was checked. `DecisionRecord.to_json()` is stable and sorted. Fill-time rejections (`SKIPPED_GAP_UP`, `SKIPPED_RR_DEGRADED`, ...) happen on the next bar and stay in `SessionResult.skips`; link them by `(symbol, signal_at)`.
- Not done: a CLI flag or file sink for `run_backtest.py`; persistence; a live endpoint. Both need a storage decision (volume, retention) and, for an endpoint, an ARC-04 and OpenAPI change.
- Not captured: the individual rules **inside** each detector (for example the opening-range width bounds, the retest tolerance). Detectors do not emit a per-rule trace today, so these appear only through the setup's own fields (`anchor`, `trigger_price`, end reason). Recording them requires each detector to report its checks, a change inside strategy code that Phase 1 excludes; the provider hook above is where it plugs in.
- A record exists only when the snapshot is valid and the session context is known (the same condition under which the engine produces a signal).
