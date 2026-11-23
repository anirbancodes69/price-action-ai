"""Phase 1 P5: rule-evaluation records describe a decision without changing it."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from typing import Any

from app.domain.analyse import AnalysisResult
from app.domain.audit import (
    RULE_PROVIDERS,
    Outcome,
    RuleClass,
    RuleEvaluation,
    RuleResult,
    Stage,
    build_decision_records,
)
from app.domain.levels import TradeLevels
from app.domain.risk.request import RiskResult
from app.domain.risk.sizing import Sizing
from app.domain.setups.scoring import Component, Paqs
from app.domain.setups.signal import ScoredSetup, Signal, SignalResult
from app.domain.setups.types import Setup, SetupDirection, SetupStatus, SetupType
from app.domain.snapshot import SnapshotCheck, SnapshotStatus
from app.rulesets import load_ruleset

from ..backtest.test_replay import BASE, CLOSE, OPEN, day, make_analyse, run, sym

PARAMS = load_ruleset("pa-intraday", "0.1.0")
BAR_END = datetime(2026, 11, 18, 4, 0, tzinfo=UTC)
T = 5


def setup(status=SetupStatus.ENTRY_CONFIRMED, typ=SetupType.OPENING_RANGE_BREAKOUT, **kw) -> Setup:  # type: ignore[no-untyped-def]
    d: dict[str, Any] = {
        "type": typ,
        "direction": SetupDirection.LONG,
        "status": status,
        "detected_at_index": T,
        "trigger_price": D("100"),
        "anchor": "OR_HIGH",
        "confirmed_at_index": T if status is SetupStatus.ENTRY_CONFIRMED else None,
        "confirm_close": D("100.2"),
    }
    return Setup(**(d | kw))


def scored(st: Setup, paqs: int | None = 70, rr: str = "2.5", target: str | None = "102.5") -> ScoredSetup:
    lv = TradeLevels(
        D("100"),
        D("99"),
        D(target) if target else None,
        "PDH",
        D("1"),
        D(rr) if target else None,
        target is None or D(rr) < 2,
    )
    comps = (Component("structure_alignment", 25, 25), Component("key_level_quality", 0, 20, True, "NO_ZONE"))
    return ScoredSetup(st, Paqs("paqs-intraday-0.1.0", paqs, comps) if paqs is not None else None, lv)


def analysis(setups: list[ScoredSetup], signal: SignalResult) -> AnalysisResult:
    return AnalysisResult(
        "pa-intraday",
        "0.1.0",
        SnapshotCheck(SnapshotStatus.VALID, ()),
        "h5",
        "h15",
        None,
        None,
        None,
        None,
        setups=tuple(setups),
        signal=signal,
        no_setup_reasons=("NO_OR_BREAKOUT",) if not setups else (),
    )


def sig(kind: Signal, primary: ScoredSetup | None, *reasons: str) -> SignalResult:
    return SignalResult(kind, primary, tuple(reasons), BAR_END, BAR_END + timedelta(minutes=5))


def records(res: AnalysisResult, risk: RiskResult | None = None):  # type: ignore[no-untyped-def]
    return build_decision_records(res, "AAA", PARAMS.values, BAR_END, PARAMS.content_hash, risk, T)


def rule(rec, rid: str) -> RuleEvaluation:  # type: ignore[no-untyped-def]
    return next(r for r in rec.rules if r.rule_id == rid)


def test_a_bar_with_no_setup_is_never_detected_not_rejected() -> None:
    (rec,) = records(analysis([], sig(Signal.NO_TRADE, None, "NO_SETUP")))
    assert (rec.outcome, rec.strategy_id, rec.final_rejection_reason) == (
        Outcome.NEVER_DETECTED,
        None,
        "NO_SETUP",
    )
    r = rule(rec, "SETUP_DETECTED")
    assert (r.result, r.failure_reason, r.stage) == (RuleResult.FAIL, "NO_OR_BREAKOUT", Stage.DETECTION)


def test_a_low_score_setup_is_rejected_with_the_threshold_and_inputs_recorded() -> None:
    s = scored(setup(), paqs=50)
    (rec,) = records(analysis([s], sig(Signal.NO_TRADE, s, "LOW_SCORE")))
    assert (rec.outcome, rec.final_signal, rec.final_rejection_reason) == (
        Outcome.REJECTED,
        "NO_TRADE",
        "LOW_SCORE",
    )
    r = rule(rec, "PAQS_MINIMUM")
    assert (r.result, r.classification, r.inputs["paqs"], r.thresholds["score.watch_threshold"]) == (
        RuleResult.FAIL,
        RuleClass.MANDATORY,
        "50",
        "60",
    )
    assert rule(rec, "RR_MINIMUM").result is RuleResult.PASS
    assert (rec.paqs_total, rec.paqs_version, rec.paqs_components[1]["missing"]) == (
        50,
        "paqs-intraday-0.1.0",
        True,
    )
    assert (rec.strategy_id, rec.lifecycle_state, rec.entry, rec.stop, rec.target) == (
        "OPENING_RANGE_BREAKOUT",
        "ENTRY_CONFIRMED",
        "100",
        "99",
        "102.5",
    )


def test_every_gate_failure_is_reported_separately_when_several_fail() -> None:
    s = scored(setup(), paqs=50, rr="1.2")
    (rec,) = records(
        analysis([s], sig(Signal.NO_TRADE, s, "LOW_SCORE", "RR_BELOW_MINIMUM", "AFTER_ENTRY_CUTOFF"))
    )
    failed = {r.rule_id for r in rec.rules if r.result is RuleResult.FAIL}
    assert failed == {"PAQS_MINIMUM", "RR_MINIMUM", "BEFORE_ENTRY_CUTOFF"}
    assert rec.final_rejection_reason == "LOW_SCORE;RR_BELOW_MINIMUM;AFTER_ENTRY_CUTOFF"


def test_a_watch_setup_fails_only_the_confirmation_rule() -> None:
    s = scored(setup(SetupStatus.AWAITING_CONFIRMATION))
    (rec,) = records(analysis([s], sig(Signal.BUY_WATCH, s)))
    assert rec.outcome is Outcome.WATCH
    c = rule(rec, "ENTRY_CONFIRMED")
    assert (c.classification, c.result, c.failure_reason) == (
        RuleClass.CONFIRMATION,
        RuleResult.FAIL,
        "AWAITING_CONFIRMATION",
    )
    assert not [
        r for r in rec.rules if r.result is RuleResult.FAIL and r.classification is RuleClass.MANDATORY
    ]


def test_a_confirmed_setup_with_a_passing_risk_check_records_levels_and_size() -> None:
    s = scored(setup())
    ok = RiskResult(
        True,
        (),
        (),
        None,
        D("100"),
        D("99"),
        D("102.5"),
        D("2.5"),
        Sizing(476, D("500"), D("1"), D("476"), D("47600"), "RISK", {}, None),
    )
    (rec,) = records(analysis([s], sig(Signal.ENTRY_CONFIRMED, s)), ok)
    assert (rec.outcome, rec.final_signal, rec.position_size, rec.final_rejection_reason) == (
        Outcome.ENTRY_CONFIRMED,
        "ENTRY_CONFIRMED",
        476,
        None,
    )
    assert rule(rec, "RISK_CHECK").result is RuleResult.PASS


def test_a_confirmed_setup_refused_by_risk_is_risk_rejected_with_the_reason() -> None:
    s = scored(setup())
    bad = RiskResult(False, ("STOP_TOO_WIDE",), (), None, D("100"), D("96"), D("110"))
    (rec,) = records(analysis([s], sig(Signal.ENTRY_CONFIRMED, s)), bad)
    assert (rec.outcome, rec.final_rejection_reason) == (Outcome.RISK_REJECTED, "STOP_TOO_WIDE")
    r = rule(rec, "RISK_STOP_DISTANCE")
    assert (r.result, r.failure_reason, r.thresholds["risk.max_stop_distance_pct"]) == (
        RuleResult.FAIL,
        "STOP_TOO_WIDE",
        "2.0",
    )
    blocked = RiskResult(False, ("MAX_POSITIONS_REACHED",), (), "MAX_POSITIONS_REACHED")
    (rec2,) = records(analysis([s], sig(Signal.ENTRY_CONFIRMED, s)), blocked)
    assert rule(rec2, "RISK_ACCOUNT_LIMITS").failure_reason == "MAX_POSITIONS_REACHED"


def test_terminal_short_and_outranked_setups_each_get_their_own_record() -> None:
    primary = scored(setup(SetupStatus.AWAITING_CONFIRMATION, SetupType.BREAKOUT_RETEST), paqs=80)
    outranked = scored(setup(SetupStatus.AWAITING_CONFIRMATION, SetupType.PREV_DAY_HIGH_BREAK), paqs=65)
    expired = scored(setup(SetupStatus.EXPIRED, end_reason="EXPIRED_BARS", ended_at_index=T))
    short = scored(setup(SetupStatus.FORMING, SetupType.PREV_DAY_LOW_BREAK, direction=SetupDirection.SHORT))
    recs = records(analysis([primary, outranked, expired, short], sig(Signal.BUY_WATCH, primary)))
    by = {r.strategy_id + ":" + r.lifecycle_state: r for r in recs}  # type: ignore[operator]
    assert by["BREAKOUT_RETEST:AWAITING_CONFIRMATION"].outcome is Outcome.WATCH
    o = by["PREV_DAY_HIGH_BREAK:AWAITING_CONFIRMATION"]
    assert (o.outcome, o.final_signal, o.final_rejection_reason) == (Outcome.NOT_SELECTED, None, "OUTRANKED")
    assert rule(o, "PAQS_MINIMUM").result is RuleResult.NOT_APPLICABLE  # the gate runs on the primary only
    e = by["OPENING_RANGE_BREAKOUT:EXPIRED"]
    assert (e.outcome, e.final_rejection_reason) == (Outcome.TERMINATED, "EXPIRED_BARS")
    sh = by["PREV_DAY_LOW_BREAK:FORMING"]
    assert (sh.outcome, rule(sh, "DIRECTION_LONG").result) == (Outcome.INFORMATIONAL, RuleResult.FAIL)


def test_records_serialise_to_stable_json_with_the_ruleset_identity() -> None:
    s = scored(setup(), paqs=50)
    (rec,) = records(analysis([s], sig(Signal.NO_TRADE, s, "LOW_SCORE")))
    d = json.loads(rec.to_json())
    assert (d["schema_version"], d["ruleset"], d["ruleset_hash"], d["bar_end"]) == (
        1,
        "pa-intraday 0.1.0",
        PARAMS.content_hash,
        BAR_END.isoformat(),
    )
    assert d["rules"][0]["rule_id"] == "SETUP_DETECTED" and d["entry"] == "100"
    assert rec.to_json() == records(analysis([s], sig(Signal.NO_TRADE, s, "LOW_SCORE")))[0].to_json()


def test_a_strategy_can_register_extra_rules_without_touching_the_builder() -> None:
    extra = RuleEvaluation(
        "ORB_WIDTH", "Opening range width in bounds", Stage.DETECTION, RuleClass.MANDATORY, RuleResult.PASS
    )
    RULE_PROVIDERS["OPENING_RANGE_BREAKOUT"] = lambda _s, _r: [extra]
    try:
        s = scored(setup())
        (rec,) = records(analysis([s], sig(Signal.ENTRY_CONFIRMED, s)))
        assert rec.rules[-1] is extra
    finally:
        RULE_PROVIDERS.clear()


def test_an_invalid_snapshot_yields_no_records() -> None:
    res = replace(analysis([], sig(Signal.NO_TRADE, None)), signal=None, setups=None)
    assert records(res) == []


def test_the_replay_sink_is_read_only_and_sees_the_risk_result() -> None:
    rows = day({3: ("100", "100.5", "99.9", "100.2"), 4: ("100.2", "103.5", "100", "103")})
    base = make_analyse({("AAA", 2): 70})

    def with_setups(s, k, spec, p):  # type: ignore[no-untyped-def]
        res = base(s, k, spec, p)
        prim = res.signal.primary if res.signal else None
        return replace(res, setups=(prim,) if prim else ())

    got: list = []
    baseline = run([sym("AAA", rows)], base)
    audited = run_with_sink([sym("AAA", rows)], with_setups, got.append)
    assert (audited.trades, audited.skips) == (baseline.trades, baseline.skips)  # nothing changed
    confirmed = [r for r in got if r.outcome is Outcome.ENTRY_CONFIRMED]
    assert len(confirmed) == 1 and confirmed[0].instrument == "AAA" and confirmed[0].position_size == 500
    assert confirmed[0].ruleset_hash == BASE.content_hash
    assert any(r.outcome is Outcome.NEVER_DETECTED for r in got)


def run_with_sink(symbols, analyse_fn, sink):  # type: ignore[no-untyped-def]
    from app.backtest.replay import SessionSpec, replay_session

    from ..backtest.test_replay import PROFILE, SCHEDULE

    spec = SessionSpec(OPEN.date(), OPEN, CLOSE)
    return replay_session(symbols, spec, BASE, PROFILE, SCHEDULE, analyse_fn, decision_sink=sink)
