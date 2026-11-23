"""Phase 1 P6: the live ruleset's risk defaults, applied end to end on a ₹1,00,000 account.

Expected values are hand-computed from the planning values (CLAUDE.md §1, TRD-05 §2): 0.5% risk = ₹500,
₹50,000 per position, daily loss 1.5% = ₹1,500, 3 losing trades, 2 positions, open risk 1.0% = ₹1,000, min R:R 2.
The daily-loss, streak, position and open-risk values are placeholders pending the owner (OQ-TRD-04); these
tests pin what is configured, they do not approve it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from app.backtest.trade import ExitConfig, Position, step_position
from app.domain.risk.account import AccountState, ClosedTrade, OpenPosition, RiskProfile, derive_account_state
from app.domain.risk.request import RiskRequest, calculate_risk
from app.domain.setups.types import SetupDirection
from app.domain.types import Bar
from app.rulesets import load_ruleset

P = load_ruleset("pa-intraday", "0.1.0")
PROFILE = RiskProfile.from_params(P, D("100000"))
NOW = datetime(2026, 11, 18, 5, 0, tzinfo=UTC)
CUTOFF = NOW + timedelta(hours=1)
FLAT = AccountState(D(0), D(0), D(0), D(0), 0, 0, D(0))


def plan(entry: str, stop: str, target: str, state: AccountState = FLAT):  # type: ignore[no-untyped-def]
    return calculate_risk(
        RiskRequest(
            SetupDirection.LONG, D(entry), D(stop), D(target), D("0.05"), 1, PROFILE, state, True, NOW, CUTOFF
        ),
        P,
    )


def test_the_default_profile_equals_the_planning_values() -> None:
    assert (PROFILE.capital, PROFILE.risk_pct, PROFILE.max_position_value) == (D(100000), D("0.5"), D(50000))
    assert (PROFILE.daily_loss_limit, PROFILE.max_consecutive_losses, PROFILE.max_open_positions) == (
        D(1500),
        3,
        2,
    )
    assert PROFILE.capital * PROFILE.max_open_risk_pct / 100 == D(1000)


def test_a_one_percent_stop_sizes_to_the_risk_budget_and_the_position_cap_together() -> None:
    r = plan("1000", "990", "1020")  # risk/share 10: budget 500/10 = 50 sh, cap 50000/1000 = 50 sh
    assert r.ok and r.sizing is not None
    assert (r.sizing.qty, r.sizing.actual_risk, r.sizing.position_value) == (50, D(500), D(50000))


def test_a_tight_stop_is_bound_by_the_position_cap_not_the_risk_budget() -> None:
    r = plan("1000", "998", "1010")  # budget 500/2 = 250 sh but the cap allows 50 sh: risk is only ₹100
    assert r.sizing is not None and (r.sizing.qty, r.sizing.actual_risk) == (50, D(100))
    assert r.sizing.binding_constraint == "POSITION_CAP"


def test_minimum_reward_to_risk_and_stop_distance_limits_apply() -> None:
    assert plan("1000", "990", "1019").errors == ("RR_BELOW_MINIMUM",)  # 1.9R < 2.0
    assert plan("1000", "970", "1090").errors == ("STOP_TOO_WIDE",)  # 3% > 2.0%
    assert plan("1000", "999.5", "1002").errors == ("STOP_TOO_TIGHT",)  # 0.05% < 0.15%


@pytest.mark.parametrize(
    ("state", "blocked"),
    [
        (AccountState(D(-1400), D(1400), D(0), D(1400), 0, 0, D(0)), None),
        (AccountState(D(-1500), D(1500), D(0), D(1500), 0, 0, D(0)), "DAILY_LOSS_LIMIT_REACHED"),
        (AccountState(D(0), D(0), D(0), D(0), 2, 0, D(0)), None),
        (AccountState(D(0), D(0), D(0), D(0), 3, 0, D(0)), "MAX_CONSECUTIVE_LOSSES_REACHED"),
        (AccountState(D(0), D(0), D(0), D(0), 0, 1, D(0)), None),
        (AccountState(D(0), D(0), D(0), D(0), 0, 2, D(0)), "MAX_POSITIONS_REACHED"),
    ],
)
def test_account_limits_trip_exactly_at_the_configured_values(
    state: AccountState, blocked: str | None
) -> None:
    r = plan("1000", "990", "1020", state)
    assert r.blocked_reason == blocked and r.ok is (blocked is None)


def test_the_remaining_daily_loss_budget_caps_the_size() -> None:
    r = plan("1000", "990", "1020", AccountState(D(-1400), D(1400), D(0), D(1400), 0, 0, D(0)))
    assert r.sizing is not None and (r.sizing.qty, r.remaining_daily_loss) == (
        10,
        D(100),
    )  # ₹100 left / ₹10 per share


def test_the_open_risk_limit_leaves_room_for_a_second_full_risk_position_only() -> None:
    one = derive_account_state([], [OpenPosition(D(1000), D(990), 50)])  # ₹500 at risk
    assert plan("1000", "990", "1020", one).ok
    two = derive_account_state([], [OpenPosition(D(1000), D(990), 50), OpenPosition(D(1000), D(990), 50)])
    assert plan("1000", "990", "1020", two).blocked_reason == "MAX_POSITIONS_REACHED"
    heavy = derive_account_state([], [OpenPosition(D(1000), D(980), 50)])  # ₹1,000 at risk = the whole limit
    r = plan("1000", "990", "1020", heavy)
    assert not r.ok and r.errors == ("OPEN_RISK_LIMIT_REACHED",)


def test_a_losing_streak_counts_only_the_trailing_losses_of_the_day() -> None:
    state = derive_account_state(
        [ClosedTrade(D(-10)), ClosedTrade(D(50)), ClosedTrade(D(-5)), ClosedTrade(D(-5))], []
    )
    assert state.losing_streak == 2


def _bar(o: str, h: str, lo: str, c: str, start: datetime) -> Bar:
    return Bar(start, start + timedelta(minutes=5), D(o), D(h), D(lo), D(c))


def test_slippage_is_charged_on_stop_exits_only_characterisation() -> None:
    """Known simplification (docs/trading/exit-execution-specification.md §6): adverse slippage applies to the
    entry and to stop exits; target, session-end and structure exits at the open take none."""
    exit_time = NOW + timedelta(minutes=30)
    cfg = ExitConfig(D("0.05"), exit_time, True, True)
    pos = Position("X", "T", 0, "", 1, D("100"), D("99"), D("103"), NOW, NOW)
    assert step_position(pos, _bar("100", "100.5", "98.9", "99", NOW), cfg) == (D("99") * D("0.9995"), "STOP")
    assert step_position(pos, _bar("100", "103.2", "99.5", "103", NOW), cfg) == (D("103"), "TARGET")
    assert step_position(pos, _bar("101", "101.5", "100.5", "101", exit_time), cfg) == (
        D("101"),
        "SESSION_END",
    )


def test_risk_per_trade_above_the_two_percent_ceiling_is_refused_and_two_percent_is_allowed() -> None:
    """DEC-024 D-3: 2% is a technical ceiling, not a recommended risk; the default stays 0.5%."""
    import dataclasses

    def with_risk(pct: str):  # type: ignore[no-untyped-def]
        prof = dataclasses.replace(PROFILE, risk_pct=D(pct))
        req = RiskRequest(
            SetupDirection.LONG, D("1000"), D("990"), D("1020"), D("0.05"), 1, prof, FLAT, True, NOW, CUTOFF
        )
        return calculate_risk(req, P)

    assert with_risk("2").ok and with_risk("2").sizing is not None
    assert with_risk("2").sizing.actual_risk <= D(2000)  # type: ignore[union-attr]
    for bad in ("2.01", "5", "0", "-1"):
        r = with_risk(bad)
        assert (r.ok, r.errors) == (False, ("RISK_PCT_ABOVE_CEILING",))
    assert PROFILE.risk_pct == D("0.5")  # the default is unchanged
