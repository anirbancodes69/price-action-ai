"""TV-RSK (TRD-05): rounding, validation, account limits, sizing, fills, exits, request. Hand-computed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.risk.account import (
    ClosedTrade,
    OpenPosition,
    RiskProfile,
    check_account_limits,
    derive_account_state,
)
from app.domain.risk.exits import evaluate_bar_exit
from app.domain.risk.fill import simulate_entry
from app.domain.risk.request import RiskRequest, calculate_risk
from app.domain.risk.rounding import down_to_tick, entry_up, inr, qty_to_lots
from app.domain.risk.sizing import size_position
from app.domain.risk.validation import (
    effective_min_rr,
    risk_reward,
    stop_override_warning,
    validate_rr,
    validate_stop,
)
from app.domain.setups.types import SetupDirection
from app.domain.types import Bar
from app.rulesets import load_ruleset

D = Decimal
PARAMS = load_ruleset("pa-intraday", "0.1.0")
T0 = datetime(2026, 11, 18, 4, 0, tzinfo=UTC)
CUTOFF = T0 + timedelta(hours=5)
PROFILE = RiskProfile(D("100000"), D("0.5"), D("50000"), D("1.5"), 3, 2, D("1.0"))
EMPTY = derive_account_state([], [])


def test_rounding_directions() -> None:
    tick = D("0.05")
    assert entry_up(D("1498.12"), tick) == D("1498.15")
    assert entry_up(D("1498.10"), tick) == D("1498.10")
    assert down_to_tick(D("1485.27"), tick) == D("1485.25")
    assert qty_to_lots(33, 10) == 30
    assert inr(D("424.045")) == D("424.05")  # ROUND_HALF_UP


def test_profile_from_ruleset_defaults() -> None:
    p = RiskProfile.from_params(PARAMS, D("100000"))
    assert p == PROFILE
    assert p.daily_loss_limit == D("1500")


def test_stop_validation_boundaries() -> None:
    tick, mn, mx = D("0.05"), D("0.15"), D("2.0")
    assert validate_stop(D("1000"), D("1000"), tick, mn, mx) == ["STOP_NOT_BELOW_ENTRY"]
    assert validate_stop(D("1000"), D("998.5"), tick, mn, mx) == []  # exactly 0.15 %
    assert validate_stop(D("1000"), D("998.51"), tick, mn, mx) == ["STOP_TOO_TIGHT"]
    assert validate_stop(D("1000"), D("980"), tick, mn, mx) == []  # exactly 2.0 %
    assert validate_stop(D("1000"), D("979.95"), tick, mn, mx) == ["STOP_TOO_WIDE"]
    assert validate_stop(D("10"), D("9.95"), tick, mn, mx) == ["STOP_TOO_TIGHT"]  # under 2 ticks (0.10)


def test_rr_validation_example_from_spec() -> None:
    entry, stop, target = D("412.30"), D("409.60"), D("417.20")
    assert risk_reward(entry, stop, target) == D("4.90") / D("2.70")  # 1.81
    assert validate_rr(entry, stop, target, D("2")) == ["RR_BELOW_MINIMUM"]
    assert validate_rr(entry, stop, D("412.30"), D("2")) == ["TARGET_NOT_ABOVE_ENTRY"]
    assert validate_rr(entry, stop, D("417.70"), D("2")) == []  # 5.40 / 2.70 = 2.0 exactly
    assert effective_min_rr(D("2"), D("1.5")) == D("2") and effective_min_rr(D("2"), D("3")) == D("3")
    assert stop_override_warning(D("410"), D("409")) == "STOP_TIGHTER_THAN_STRUCTURE"
    assert stop_override_warning(D("408"), D("409")) is None


def test_account_state_derivation() -> None:
    closed = [ClosedTrade(D("-300")), ClosedTrade(D("100")), ClosedTrade(D("-50")), ClosedTrade(D("-20"))]
    st = derive_account_state(closed, [OpenPosition(D("100"), D("98"), 10)], pending_fills=1)
    assert st.realised_net_pnl_today == D("-270") and st.realised_net_loss_today == D("270")
    assert st.open_risk == D("20") and st.day_loss_used == D("290")
    assert st.losing_streak == 2  # the +100 trade resets the run
    assert st.open_positions == 2 and st.cost_basis_open == D("1000")
    # a stop above the fill (trailed into profit) contributes no open risk
    assert derive_account_state([], [OpenPosition(D("100"), D("101"), 5)]).open_risk == 0
    assert derive_account_state([ClosedTrade(D("50"))], []).realised_net_loss_today == 0


def test_account_limits_boundaries_and_order() -> None:
    def state(loss: str = "0", streak: int = 0, pos: int = 0):  # type: ignore[no-untyped-def]
        trades = [ClosedTrade(D("-1"))] * streak
        base = derive_account_state(trades, [OpenPosition(D("10"), D("9"), 1)] * pos)
        return base.__class__(
            -D(loss),
            D(loss),
            base.open_risk,
            D(loss) + base.open_risk,
            base.losing_streak,
            base.open_positions,
            base.cost_basis_open,
        )

    end = CUTOFF
    assert check_account_limits(state("1499.99"), PROFILE, True, end, CUTOFF) is None
    assert check_account_limits(state("1500"), PROFILE, True, end, CUTOFF) == "DAILY_LOSS_LIMIT_REACHED"
    assert check_account_limits(state(streak=2), PROFILE, True, end, CUTOFF) is None
    assert (
        check_account_limits(state(streak=3), PROFILE, True, end, CUTOFF) == "MAX_CONSECUTIVE_LOSSES_REACHED"
    )
    assert check_account_limits(state(pos=2), PROFILE, True, end, CUTOFF) == "MAX_POSITIONS_REACHED"
    assert check_account_limits(state(), PROFILE, False, end, CUTOFF) == "SESSION_CLOSED"
    assert (
        check_account_limits(state(), PROFILE, True, end + timedelta(minutes=5), CUTOFF)
        == "ENTRY_CUTOFF_PASSED"
    )
    both = state("1500", streak=3)  # first failure wins
    assert check_account_limits(both, PROFILE, True, end, CUTOFF) == "DAILY_LOSS_LIMIT_REACHED"


def test_sizing_worked_example_3_1() -> None:
    s = size_position(D("1498.10"), D("1485.25"), PROFILE, EMPTY)
    assert s.constraints == {
        "RISK_BUDGET": 38,
        "CAPITAL": 66,
        "POSITION_CAP": 33,
        "OPEN_RISK": 77,
        "DAILY_LOSS": 116,
    }
    assert (s.qty, s.binding_constraint, s.rejection) == (33, "POSITION_CAP", None)
    assert (s.risk_per_share, s.risk_budget) == (D("12.85"), D("500"))
    assert s.actual_risk == D("424.05") and s.position_value == D("49437.30")


def test_sizing_example_3_2_daily_loss_binds() -> None:
    st = derive_account_state([ClosedTrade(D("-1200"))], [])
    s = size_position(D("1498.10"), D("1485.25"), PROFILE, st)
    assert (s.qty, s.binding_constraint) == (23, "DAILY_LOSS")  # floor(300 / 12.85)
    assert s.actual_risk == D("295.55")


def test_sizing_open_risk_capital_and_lots() -> None:
    st = derive_account_state([], [OpenPosition(D("1000"), D("940"), 15)])  # open risk 900, cost basis 15000
    s = size_position(D("1498.10"), D("1485.25"), PROFILE, st)
    assert s.constraints["OPEN_RISK"] == 7  # floor((1000 - 900) / 12.85)
    assert s.constraints["CAPITAL"] == 56  # floor(85000 / 1498.10)
    assert (s.qty, s.binding_constraint) == (7, "OPEN_RISK")
    assert size_position(D("1498.10"), D("1485.25"), PROFILE, EMPTY, lot_size=10).qty == 30


def test_sizing_rejections() -> None:
    s = size_position(D("1000"), D("400"), PROFILE, EMPTY)  # 600 risk per share > 500 budget
    assert (s.qty, s.binding_constraint, s.rejection) == (0, "RISK_BUDGET", "RISK_BUDGET_TOO_SMALL")
    st = derive_account_state([ClosedTrade(D("-1495"))], [])  # 5 left of the daily limit
    assert size_position(D("1498.10"), D("1485.25"), PROFILE, st).rejection == "DAILY_LOSS_LIMIT_REACHED"
    pricey = size_position(D("60000"), D("59000"), PROFILE, EMPTY)  # cap and capital both allow zero
    assert pricey.qty == 0 and pricey.rejection is not None


def _fill(open_price: str, **kw):  # type: ignore[no-untyped-def]
    args = {
        "entry_ref": D("1498.10"),
        "stop": D("1485.25"),
        "target": D("1529.00"),
        "qty_plan": 33,
        "risk_budget": D("500"),
        "max_position_value": D("50000"),
        "min_rr": D("2"),
        "max_entry_gap_pct": D("0.30"),
        "bar_start": T0,
        "cutoff": CUTOFF,
    }
    args.update(kw)
    return simulate_entry(D(open_price), **args)


def test_entry_fill_examples_from_spec() -> None:
    skipped = _fill("1503.00")  # limit 1498.10 x 1.003 = 1502.5943
    assert (skipped.filled, skipped.reason) == (False, "SKIPPED_GAP_UP")
    ok = _fill("1499.00")  # rr 30.00 / 13.75 = 2.18; qty = min(33, 36, 33)
    assert (ok.filled, ok.price, ok.qty) == (True, D("1499.00"), 33)
    assert _fill("1502.59", min_rr=D("1")).filled  # inside the gap limit (rr 1.52 would fail min 2.0)
    assert _fill("1485.25").reason == "SKIPPED_GAP_BELOW_STOP"  # O <= stop
    assert _fill("1501.00").reason == "SKIPPED_RR_DEGRADED"  # 28.00 / 15.75 = 1.78 < 2.0
    assert _fill("1499.00", bar_start=CUTOFF).reason == "SKIPPED_SESSION_CUTOFF"
    assert _fill("1499.00", account_blocked="DAILY_LOSS_LIMIT_REACHED").reason == "SKIPPED_ACCOUNT_LIMIT"


def test_fill_never_increases_quantity_and_applies_slippage() -> None:
    smaller = _fill("1499.00", qty_plan=10)
    assert smaller.qty == 10
    tight = _fill("1499.00", risk_budget=D("100"))  # floor(100 / 13.75) = 7
    assert tight.qty == 7
    slipped = _fill("1499.00", slippage_pct=D("0.05"))
    assert slipped.price == D("1499.00") * D("1.0005")


def _bar(o: str, h: str, lo: str, c: str, start: datetime = T0) -> Bar:
    return Bar(start, start + timedelta(minutes=5), D(o), D(h), D(lo), D(c))


def test_exit_rules() -> None:
    stop, target = D("98"), D("105")
    assert evaluate_bar_exit(_bar("100", "101", "99", "100"), stop, target) is None
    gap = evaluate_bar_exit(_bar("97", "99", "96", "98"), stop, target)
    assert gap is not None and (gap.price, gap.reason, gap.gap) == (D("97"), "STOP", True)
    up = evaluate_bar_exit(_bar("106", "107", "105", "106"), stop, target)
    assert up is not None and (up.price, up.reason) == (D("106"), "TARGET")
    hit = evaluate_bar_exit(_bar("100", "101", "97.5", "99"), stop, target, slippage_pct=D("0.05"))
    assert hit is not None and (hit.price, hit.reason) == (D("98") * D("0.9995"), "STOP")
    tgt = evaluate_bar_exit(_bar("100", "106", "99", "105"), stop, target)
    assert tgt is not None and (tgt.price, tgt.reason, tgt.gap) == (
        D("105"),
        "TARGET",
        False,
    )  # no positive slippage
    both = evaluate_bar_exit(_bar("100", "105.5", "97.5", "100"), stop, target)  # BT-04: stop wins
    assert both is not None and both.reason == "STOP"


def test_session_end_and_structure_exit() -> None:
    stop, target, bar = D("98"), D("105"), _bar("100", "101", "99", "100")
    end = evaluate_bar_exit(bar, stop, target, session_exit_time=T0)
    assert end is not None and (end.price, end.reason) == (D("100"), "SESSION_END")
    assert evaluate_bar_exit(bar, stop, target, session_exit_time=T0 + timedelta(minutes=5)) is None
    assert evaluate_bar_exit(bar, stop, target, session_exit_time=T0, session_exit_enabled=False) is None
    st = evaluate_bar_exit(bar, stop, target, structure_exit_pending=True)
    assert st is not None and st.reason == "STRUCTURE_EXIT"
    assert (
        evaluate_bar_exit(bar, stop, target, structure_exit_pending=True, structure_exit_enabled=False)
        is None
    )


def _req(**kw):  # type: ignore[no-untyped-def]
    args = {
        "direction": SetupDirection.LONG,
        "entry": D("1498.10"),
        "stop": D("1485.25"),
        "target": D("1529.00"),
        "tick_size": D("0.05"),
        "lot_size": 1,
        "profile": PROFILE,
        "state": EMPTY,
        "session_open": True,
        "bar_end": CUTOFF - timedelta(minutes=30),
        "cutoff": CUTOFF,
    }
    args.update(kw)
    return RiskRequest(**args)


def test_calculate_risk_worked_example() -> None:
    r = calculate_risk(_req(), PARAMS)
    assert r.ok and r.errors == () and r.sizing is not None
    assert (r.sizing.qty, r.sizing.binding_constraint) == (33, "POSITION_CAP")
    assert r.rr is not None and r.rr.quantize(D("0.01")) == D("2.40")
    assert r.remaining_daily_loss == D("1500.00") and r.ruleset_version == "pa-intraday 0.1.0"


def test_calculate_risk_rounds_conservatively() -> None:
    r = calculate_risk(_req(entry=D("1498.12"), stop=D("1485.27"), target=D("1529.04")), PARAMS)
    assert (r.entry, r.stop, r.target) == (D("1498.15"), D("1485.25"), D("1529.00"))


def test_calculate_risk_rejections_in_order() -> None:
    assert calculate_risk(_req(direction=SetupDirection.SHORT), PARAMS).errors == ("SHORT_NOT_SUPPORTED",)
    small = RiskProfile(D("9999"), D("0.5"), D("50000"), D("1.5"), 3, 2, D("1.0"))
    assert calculate_risk(_req(profile=small), PARAMS).errors == ("CAPITAL_BELOW_MINIMUM",)
    blocked = derive_account_state([ClosedTrade(D("-1500"))], [])
    r = calculate_risk(_req(state=blocked), PARAMS)
    assert (r.ok, r.errors, r.blocked_reason) == (
        False,
        ("DAILY_LOSS_LIMIT_REACHED",),
        "DAILY_LOSS_LIMIT_REACHED",
    )
    assert calculate_risk(_req(target=D("1505")), PARAMS).errors == ("RR_BELOW_MINIMUM",)
    assert calculate_risk(_req(stop=D("1498.00")), PARAMS).errors == ("STOP_TOO_TIGHT",)
    tiny = RiskProfile(D("10000"), D("0.01"), D("50000"), D("1.5"), 3, 2, D("1.0"))  # risk budget 1 rupee
    assert calculate_risk(_req(profile=tiny), PARAMS).errors == ("RISK_BUDGET_TOO_SMALL",)


def test_stop_override_marks_levels_overridden() -> None:
    r = calculate_risk(_req(stop=D("1490"), engine_stop=D("1485.25")), PARAMS)
    assert r.ok and r.warnings == ("STOP_TIGHTER_THAN_STRUCTURE",) and r.levels_overridden
