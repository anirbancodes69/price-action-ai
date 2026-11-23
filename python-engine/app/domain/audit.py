"""Rule-evaluation records: why a setup was accepted or rejected (Phase 1 P5).

Specification: docs/trading/rule-evaluation-logging.md.

Pure and read-only. `build_decision_records` *describes* an `AnalysisResult` (and optionally the `RiskResult`
of the primary setup); it never feeds back into a decision, so the existing mechanism, the score weights and
the minimum score are untouched. Every threshold shown is read from the ruleset or from the result itself.

One record per evaluated setup, plus one `NEVER_DETECTED` record when a bar produced no setup at all, so a
rejected setup (a record with `outcome` REJECTED) is distinguishable from a setup that never existed.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.domain.analyse import AnalysisResult
from app.domain.risk.request import RiskResult
from app.domain.setups.signal import ScoredSetup, Signal, _eligible
from app.domain.setups.types import Setup, SetupDirection, SetupStatus

SCHEMA_VERSION = 1


class RuleResult(StrEnum):
    PASS = "PASS"  # noqa: S105 - a rule outcome, not a credential
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RuleClass(StrEnum):
    MANDATORY = "MANDATORY"  # a FAIL stops the setup from becoming a signal
    CONFIRMATION = "CONFIRMATION"  # decides ENTRY_CONFIRMED versus BUY_WATCH, never a rejection
    INFORMATIONAL = "INFORMATIONAL"  # recorded for the audit; no effect on the decision


class Stage(StrEnum):
    DETECTION = "DETECTION"
    LIFECYCLE = "LIFECYCLE"
    SELECTION = "SELECTION"
    SIGNAL_GATE = "SIGNAL_GATE"
    RISK = "RISK"


class Outcome(StrEnum):
    NEVER_DETECTED = "NEVER_DETECTED"  # no detector produced a setup on this bar
    TERMINATED = "TERMINATED"  # detected, then INVALIDATED or EXPIRED
    INFORMATIONAL = "INFORMATIONAL"  # a short setup (SD-06): shown, never actionable
    NOT_SELECTED = "NOT_SELECTED"  # detected and live, but another setup was the primary
    REJECTED = "REJECTED"  # the primary and a mandatory rule failed: NO_TRADE
    WATCH = "WATCH"  # BUY_WATCH
    ENTRY_CONFIRMED = "ENTRY_CONFIRMED"
    RISK_REJECTED = "RISK_REJECTED"  # ENTRY_CONFIRMED by the engine, refused by the risk check


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    rule_id: str
    description: str
    stage: Stage
    classification: RuleClass
    result: RuleResult
    inputs: Mapping[str, str] = field(default_factory=dict)
    thresholds: Mapping[str, str] = field(default_factory=dict)
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    schema_version: int
    instrument: str
    bar_end: datetime  # the closed bar on which the decision was made
    strategy_id: str | None  # None only for NEVER_DETECTED
    ruleset: str  # "<code> <version>"
    ruleset_hash: str
    market_context: Mapping[str, str]
    lifecycle_state: str | None
    outcome: Outcome
    final_signal: str | None  # NO_TRADE / BUY_WATCH / ENTRY_CONFIRMED for the primary; None for others
    final_rejection_reason: str | None
    rules: tuple[RuleEvaluation, ...]
    entry: str | None = None
    stop: str | None = None
    target: str | None = None
    position_size: int | None = None
    paqs_total: int | None = None
    paqs_components: tuple[Mapping[str, Any], ...] = ()
    paqs_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe form (Decimals and datetimes as strings)."""
        out: dict[str, Any] = _plain(self)
        return out

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def _plain(v: Any) -> Any:
    if hasattr(v, "__dataclass_fields__"):
        return {k: _plain(getattr(v, k)) for k in v.__dataclass_fields__}
    if isinstance(v, Mapping):
        return {str(k): _plain(x) for k, x in v.items()}
    if isinstance(v, list | tuple):
        return [_plain(x) for x in v]
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, StrEnum):
        return v.value
    return v


# Per-strategy extension point: a provider returns the extra rule evaluations a strategy can explain from its
# `Setup` and the ruleset. None are registered yet (detectors do not emit per-rule traces; see the spec).
RuleProvider = Callable[[Setup, AnalysisResult], list[RuleEvaluation]]
RULE_PROVIDERS: dict[str, RuleProvider] = {}


def _s(v: object) -> str:
    return "" if v is None else str(v)


_RISK_RULE = {
    "STOP_NOT_BELOW_ENTRY": ("RISK_STOP_BELOW_ENTRY", "The stop is below the entry"),
    "STOP_TOO_TIGHT": ("RISK_STOP_DISTANCE", "The stop distance is within the ruleset limits"),
    "STOP_TOO_WIDE": ("RISK_STOP_DISTANCE", "The stop distance is within the ruleset limits"),
    "RR_BELOW_MINIMUM": ("RISK_MIN_RR", "Reward/risk is at least the minimum"),
    "TARGET_NOT_ABOVE_ENTRY": ("RISK_TARGET_ABOVE_ENTRY", "The target is above the entry"),
    "RISK_BUDGET_TOO_SMALL": ("RISK_SIZING", "The position size is at least one share"),
    "INSUFFICIENT_CAPITAL": ("RISK_SIZING", "The position size is at least one share"),
}


def _risk_rules(rr: RiskResult, params_thresholds: Mapping[str, str]) -> list[RuleEvaluation]:
    code = rr.errors[0] if rr.errors else None
    if rr.blocked_reason:
        rule_id, desc = "RISK_ACCOUNT_LIMITS", "No account-level limit blocks a new position"
    else:
        rule_id, desc = _RISK_RULE.get(code or "", ("RISK_CHECK", "The risk check passes"))
    inputs = {"entry": _s(rr.entry), "stop": _s(rr.stop), "target": _s(rr.target), "rr": _s(rr.rr)}
    if rr.sizing is not None:
        inputs |= {"qty": str(rr.sizing.qty), "binding_constraint": rr.sizing.binding_constraint}
    return [
        RuleEvaluation(
            rule_id,
            desc,
            Stage.RISK,
            RuleClass.MANDATORY,
            RuleResult.PASS if rr.ok else RuleResult.FAIL,
            inputs,
            params_thresholds,
            code if not rr.ok else None,
        )
    ]


def _setup_rules(
    sc: ScoredSetup, res: AnalysisResult, t: int, is_primary: bool, thresholds: Mapping[str, str]
) -> list[RuleEvaluation]:
    st, lv, sig = sc.setup, sc.levels, res.signal
    assert sig is not None
    reasons = sig.reasons if is_primary else ()
    rules = [
        RuleEvaluation(
            "SETUP_DETECTED",
            "The detector found the setup",
            Stage.DETECTION,
            RuleClass.MANDATORY,
            RuleResult.PASS,
            {
                "anchor": st.anchor,
                "trigger_price": _s(st.trigger_price),
                "detected_at_index": str(st.detected_at_index),
            },
        )
    ]
    terminal = st.is_terminal
    rules.append(
        RuleEvaluation(
            "SETUP_LIFECYCLE",
            "The setup is still live (not INVALIDATED or EXPIRED)",
            Stage.LIFECYCLE,
            RuleClass.MANDATORY,
            RuleResult.FAIL if terminal else RuleResult.PASS,
            {"status": st.status.value},
            {},
            st.end_reason if terminal else None,
        )
    )
    short = st.direction is SetupDirection.SHORT
    rules.append(
        RuleEvaluation(
            "DIRECTION_LONG",
            "Only long setups are actionable (SD-06)",
            Stage.SELECTION,
            RuleClass.MANDATORY,
            RuleResult.FAIL if short else RuleResult.PASS,
            {"direction": st.direction.value},
            {},
            "SHORT_INFORMATIONAL" if short else None,
        )
    )
    eligible = _eligible(sc, t)
    if terminal or short:
        rules.append(_na("SELECTED_AS_PRIMARY", "The setup is the primary candidate", Stage.SELECTION))
    else:
        why = (
            None
            if is_primary
            else (
                "STALE_CONFIRMATION"
                if st.status is SetupStatus.ENTRY_CONFIRMED and not eligible
                else "OUTRANKED"
            )
        )
        rules.append(
            RuleEvaluation(
                "SELECTED_AS_PRIMARY",
                "The setup is the primary candidate (TRD-04 §12 ordering)",
                Stage.SELECTION,
                RuleClass.MANDATORY,
                RuleResult.PASS if is_primary else RuleResult.FAIL,
                {"status": st.status.value, "confirmed_at_index": _s(st.confirmed_at_index), "t": str(t)},
                {},
                why,
            )
        )
    if not is_primary:
        for rid, desc in (
            ("PAQS_MINIMUM", "PAQS is at least the display threshold"),
            ("RR_MINIMUM", "Reward/risk is at least the minimum"),
            ("BEFORE_ENTRY_CUTOFF", "The signal is at or before the entry cutoff"),
        ):
            rules.append(_na(rid, desc, Stage.SIGNAL_GATE))
        rules.append(_na("ENTRY_CONFIRMED", "The entry trigger has closed", Stage.SIGNAL_GATE))
        return rules
    total = sc.paqs.total if sc.paqs else None
    rules.append(
        RuleEvaluation(
            "PAQS_MINIMUM",
            "PAQS is at least the minimum score (`score.watch_threshold`)",
            Stage.SIGNAL_GATE,
            RuleClass.MANDATORY if sc.paqs is not None else RuleClass.INFORMATIONAL,
            RuleResult.NOT_APPLICABLE
            if sc.paqs is None
            else RuleResult.FAIL
            if "LOW_SCORE" in reasons
            else RuleResult.PASS,
            {"paqs": _s(total)},
            {"score.watch_threshold": thresholds["score.watch_threshold"]},
            "LOW_SCORE" if "LOW_SCORE" in reasons else None,
        )
    )
    rr_fail = "RR_BELOW_MINIMUM" in reasons or "NO_TARGET" in reasons
    rules.append(
        RuleEvaluation(
            "RR_MINIMUM",
            "Reward/risk is at least `risk.min_rr`",
            Stage.SIGNAL_GATE,
            RuleClass.MANDATORY,
            RuleResult.FAIL if rr_fail else RuleResult.PASS,
            {
                "rr": _s(lv.rr if lv else None),
                "target": _s(lv.target if lv else None),
                "target_source": _s(lv.target_source if lv else None),
            },
            {"risk.min_rr": thresholds["risk.min_rr"]},
            "NO_TARGET" if "NO_TARGET" in reasons else "RR_BELOW_MINIMUM" if rr_fail else None,
        )
    )
    late = "AFTER_ENTRY_CUTOFF" in reasons
    rules.append(
        RuleEvaluation(
            "BEFORE_ENTRY_CUTOFF",
            "The signal is at or before the entry cutoff",
            Stage.SIGNAL_GATE,
            RuleClass.MANDATORY,
            RuleResult.FAIL if late else RuleResult.PASS,
            {"signal_at": sig.signal_at.isoformat()},
            {
                "session.entry_cutoff_minutes_before_close": thresholds[
                    "session.entry_cutoff_minutes_before_close"
                ]
            },
            "AFTER_ENTRY_CUTOFF" if late else None,
        )
    )
    confirmed = st.status is SetupStatus.ENTRY_CONFIRMED
    rules.append(
        RuleEvaluation(
            "ENTRY_CONFIRMED",
            "The entry trigger has closed (else BUY_WATCH)",
            Stage.SIGNAL_GATE,
            RuleClass.CONFIRMATION,
            RuleResult.PASS if confirmed else RuleResult.FAIL,
            {"status": st.status.value, "confirm_close": _s(st.confirm_close)},
            {},
            None if confirmed else "AWAITING_CONFIRMATION",
        )
    )
    return rules


def _na(rid: str, desc: str, stage: Stage) -> RuleEvaluation:
    return RuleEvaluation(rid, desc, stage, RuleClass.MANDATORY, RuleResult.NOT_APPLICABLE)


_THRESHOLD_KEYS = (
    "score.watch_threshold",
    "risk.min_rr",
    "session.entry_cutoff_minutes_before_close",
)
_RISK_THRESHOLD_KEYS = ("risk.min_stop_distance_pct", "risk.max_stop_distance_pct", "risk.min_rr")


def build_decision_records(
    res: AnalysisResult,
    instrument: str,
    params_values: Mapping[str, object],
    bar_end: datetime,
    ruleset_hash: str = "",
    risk: RiskResult | None = None,
    t: int | None = None,
) -> list[DecisionRecord]:
    """Records for one analysis: every detected setup, or one `NEVER_DETECTED` record.

    `params_values` is the ruleset's values (`RulesetParams.values`); `risk` is the result of
    `calculate_risk` for the primary setup when the caller ran it; `t` is the index of the last closed 5m bar
    (default: from the 5m structure). An invalid snapshot yields no records.
    """
    sig = res.signal
    if sig is None or res.setups is None:
        return []
    thresholds = {k: _s(params_values.get(k)) for k in _THRESHOLD_KEYS}
    risk_thresholds = {k: _s(params_values.get(k)) for k in _RISK_THRESHOLD_KEYS}
    ctx = {
        "htf_15m_state": res.htf.state.state.value if res.htf and res.htf.state else "NONE",
        "structure_5m_state": res.structure_5m.final.state.value
        if res.structure_5m and res.structure_5m.states
        else "NONE",
    }

    def make(strategy_id: str | None, **kw: Any) -> DecisionRecord:
        return DecisionRecord(
            schema_version=SCHEMA_VERSION,
            instrument=instrument,
            bar_end=bar_end,
            strategy_id=strategy_id,
            ruleset=f"{res.ruleset_code} {res.ruleset_version}",
            ruleset_hash=ruleset_hash,
            market_context=ctx,
            **kw,
        )

    if not res.setups:
        rule = RuleEvaluation(
            "SETUP_DETECTED",
            "A detector found a setup",
            Stage.DETECTION,
            RuleClass.MANDATORY,
            RuleResult.FAIL,
            {},
            {},
            ";".join(res.no_setup_reasons) or "NO_SETUP",
        )
        return [
            make(
                None,
                lifecycle_state=None,
                outcome=Outcome.NEVER_DETECTED,
                final_signal=sig.signal.value,
                final_rejection_reason="NO_SETUP",
                rules=(rule,),
            )
        ]
    if t is None:
        t = len(res.structure_5m.states) - 1 if res.structure_5m else 0
    out: list[DecisionRecord] = []
    for sc in res.setups:
        is_primary = sig.primary is sc
        rules = _setup_rules(sc, res, t, is_primary, thresholds)
        provider = RULE_PROVIDERS.get(sc.setup.type.value)
        if provider is not None:
            rules += provider(sc.setup, res)
        final_signal: str | None = sig.signal.value if is_primary else None
        reason: str | None = None
        if sc.setup.is_terminal:
            outcome, reason = Outcome.TERMINATED, sc.setup.end_reason
        elif sc.setup.informational:
            outcome, reason = Outcome.INFORMATIONAL, "SHORT_INFORMATIONAL"
        elif not is_primary:
            outcome, reason = (
                Outcome.NOT_SELECTED,
                next((r.failure_reason for r in rules if r.rule_id == "SELECTED_AS_PRIMARY"), None),
            )
        elif sig.signal is Signal.NO_TRADE:
            outcome, reason = Outcome.REJECTED, ";".join(sig.reasons)
        elif sig.signal is Signal.BUY_WATCH:
            outcome = Outcome.WATCH
        else:
            outcome = Outcome.ENTRY_CONFIRMED
        if is_primary and risk is not None:
            rules += _risk_rules(risk, risk_thresholds)
            if not risk.ok and sig.signal is not Signal.NO_TRADE:
                outcome, reason = (
                    Outcome.RISK_REJECTED,
                    risk.errors[0] if risk.errors else risk.blocked_reason,
                )
        lv = sc.levels
        out.append(
            make(
                sc.setup.type.value,
                lifecycle_state=sc.setup.status.value,
                outcome=outcome,
                final_signal=final_signal,
                final_rejection_reason=reason,
                rules=tuple(rules),
                entry=_s(lv.entry) if lv else None,
                stop=_s(lv.stop) if lv else None,
                target=_s(lv.target) if lv and lv.target is not None else None,
                position_size=risk.sizing.qty if is_primary and risk is not None and risk.sizing else None,
                paqs_total=sc.paqs.total if sc.paqs else None,
                paqs_version=sc.paqs.version if sc.paqs else None,
                paqs_components=tuple(
                    {
                        "name": c.name,
                        "points": c.points,
                        "maximum": c.maximum,
                        "missing": c.missing,
                        "reason": c.reason,
                    }
                    for c in (sc.paqs.components if sc.paqs else ())
                ),
            )
        )
    return out
