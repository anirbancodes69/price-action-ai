"""E1 and E7 (OD-8 step 1): the opening-range detector in the single-strategy run mode.

The registered detector is today's `detect_opening_range` (the current configuration, CUR), unchanged. It is
**not** the frozen B0 path (E4). These tests give the isolation proof (P0-3 on hand-built bars), bar-by-bar
replay equivalence, determinism and the absence of look-ahead at the backtest level. No database is read and no
stored candle is used.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.backtest.costs import CostSchedule
from app.backtest.replay import SymbolData, replay_session
from app.backtest.run import SessionInput
from app.backtest.strategy_run import (
    run_strategy_backtest,
    seeded_order,
    strategy_analyse,
    unlimited_profile,
)
from app.domain.analyse import analyse
from app.domain.session import DailyLevels
from app.domain.setups.opening_range import detect_opening_range
from app.domain.setups.signal import Signal
from app.domain.setups.types import SetupDirection, SetupType
from app.domain.strategies import STRATEGY_DETECTORS, strategy_detectors
from app.domain.types import Bar

from ..trading._session import CLOSE, OPEN, mk
from ..trading.test_setups_session import ORB_DAY
from .test_strategy_run import _small, _spec

D = Decimal
SID = "opening_range_breakout"
ORB = SetupType.OPENING_RANGE_BREAKOUT
PREV = DailyLevels(D("1600"), D("1480"), D("1495"))  # a far previous-day high so the entry has a target
KW = {"previous_session_open": None, "session_close": CLOSE}
# After the confirmation (bar 6) the price rises, then a bar breaks the stop (below the OR low 1486).
ENTRY_TAIL = [("1498.5", "1500", "1497", "1499")]
STOP_TAIL = [("1499", "1499.5", "1480", "1481")]
WILD_TAIL = [("1481", "5000", "1", "2")] * 3  # nothing after the exit may change the trade


def _sym(rows: list[tuple[str, str, str, str]], name: str = "A") -> SymbolData:
    bars = mk(rows)
    return SymbolData(name, bars, bars, PREV, D("0.05"))


def _run(rows: list[tuple[str, str, str, str]], experiment: str = "4a"):  # type: ignore[no-untyped-def]
    inputs = [SessionInput(_spec(), [_sym(rows)])]
    return run_strategy_backtest(
        SID, experiment, inputs, _small("pa-intraday", "0.5.0"), D("100000"), CostSchedule(), "e", "d", "u"
    )


# --- E1: the registry -----------------------------------------------------------------------------------------------


def test_the_registry_holds_the_current_opening_range_detector_unchanged() -> None:
    assert strategy_detectors(SID) == (detect_opening_range,)
    assert SID in STRATEGY_DETECTORS and len(STRATEGY_DETECTORS) == 4


def test_unknown_strategies_are_still_rejected_and_the_message_lists_the_known_ids() -> None:
    with pytest.raises(ValueError, match="unknown strategy") as e:
        strategy_detectors("vwap_pullback")
    assert SID in str(e.value)


def test_the_registered_detector_is_the_current_one_not_b0() -> None:
    """Pins the facts that make this CUR: both directions, and the 15m context filter. B0 is long only (E4)."""
    p = _small("pa-intraday", "0.5.0")
    b5 = mk(ORB_DAY)
    alone = analyse(b5[:5], b5[:5], OPEN, PREV, p, detectors=strategy_detectors(SID), isolated=True, **KW)  # type: ignore[arg-type]
    assert alone.setups is not None
    assert {s.setup.direction for s in alone.setups} == {SetupDirection.LONG, SetupDirection.SHORT}


# --- E7: the isolation proof (P0-3 on hand-built bars) --------------------------------------------------------------


def test_isolation_proof_candidates_equal_the_orb_only_candidates_of_the_combined_run() -> None:
    p = _small("pa-intraday", "0.5.0")
    b5 = mk(ORB_DAY + ENTRY_TAIL * 4)
    combined_types: set[SetupType] = set()
    compared = 0
    for k in range(5, len(b5) + 1):  # every bar close from the first analysable one
        combined = analyse(b5[:k], b5[:k], OPEN, PREV, p, **KW)  # type: ignore[arg-type]
        alone = analyse(b5[:k], b5[:k], OPEN, PREV, p, detectors=strategy_detectors(SID), isolated=True, **KW)  # type: ignore[arg-type]
        assert alone.setups is not None and combined.setups is not None
        combined_types |= {s.setup.type for s in combined.setups}
        own = [s for s in combined.setups if s.setup.type is ORB]
        assert [(s.setup, s.levels) for s in alone.setups] == [(s.setup, s.levels) for s in own], k
        assert all(s.setup.type is ORB and s.paqs is None for s in alone.setups), k
        compared += 1
    assert compared > 0 and len(combined_types) > 1, (
        "the combined run must contain other setup types to make the proof meaningful"
    )


def test_isolated_signal_takes_the_orb_candidate_without_the_score_gate() -> None:
    p = _small("pa-intraday", "0.5.0")
    b5 = mk(ORB_DAY + ENTRY_TAIL)
    alone = analyse(b5[:7], b5[:7], OPEN, PREV, p, detectors=strategy_detectors(SID), isolated=True, **KW)  # type: ignore[arg-type]
    assert alone.signal is not None and alone.signal.primary is not None
    assert alone.signal.signal is Signal.ENTRY_CONFIRMED and alone.signal.primary.setup.type is ORB


# --- E7: the run mode ------------------------------------------------------------------------------------------------


def test_4a_and_4b_runs_are_flagged_recorded_and_trade_only_the_opening_range_setup() -> None:
    for exp in ("4a", "4b"):
        r = _run(ORB_DAY + ENTRY_TAIL + STOP_TAIL, exp)
        assert (r.record.strategy_id, r.record.experiment) == (SID, exp)
        assert "NOT_ISOLATED" not in r.flags and {"costs_unverified", "UNSUPPORTED_DIRECTION:SHORT"} <= set(
            r.flags
        )
        assert len(r.trades) == 1 and {t.setup_type for t in r.trades} == {ORB.value}
        assert r.trades[0].anchor == "OR_HIGH"


# --- E7: bar-by-bar replay equivalence ------------------------------------------------------------------------------


def test_replay_equivalence_the_replayed_decision_equals_the_analysis_of_the_prefix() -> None:
    rows = ORB_DAY + ENTRY_TAIL + STOP_TAIL
    sym = _sym(rows)
    p = _small("pa-intraday", "0.5.0")
    spec = _spec()
    fn = strategy_analyse(SID)
    first_confirmed: int | None = None
    for k in range(1, len(sym.bars_5m) + 1):
        via_run = fn(sym, k, spec, p)
        direct = analyse(
            list(sym.bars_5m[:k]), list(sym.bars_15m[:k]), spec.session_open, sym.prev_day, p,
            spec.previous_session_open, sym.tick, spec.session_close, sym.zone_cache,
            detectors=strategy_detectors(SID), isolated=True,
        )  # fmt: skip
        assert via_run == direct, k
        if (
            first_confirmed is None
            and direct.signal is not None
            and direct.signal.signal is Signal.ENTRY_CONFIRMED
        ):
            first_confirmed = k
    assert first_confirmed is not None
    # The replay enters at the open of the bar after the first confirming close, never earlier.
    result = replay_session(
        [sym], spec, p, unlimited_profile(p, D("100000")), CostSchedule(), fn, seeded_order(1)
    )
    (trade,) = result.trades
    assert trade.signal_at == sym.bars_5m[first_confirmed - 1].end
    assert trade.fill_at == sym.bars_5m[first_confirmed].start


# --- E7: determinism, no look-ahead, data unchanged -----------------------------------------------------------------


def test_two_runs_on_the_same_input_are_identical() -> None:
    rows = ORB_DAY + ENTRY_TAIL + STOP_TAIL
    a, b = _run(rows), _run(rows)
    assert a.trades == b.trades and a.record == b.record and a.metrics == b.metrics and a.flags == b.flags


def test_no_look_ahead_data_after_the_exit_cannot_change_the_trade() -> None:
    base = _run(ORB_DAY + ENTRY_TAIL + STOP_TAIL)
    extended = _run(ORB_DAY + ENTRY_TAIL + STOP_TAIL + WILD_TAIL)
    (t0,), (t1,) = base.trades, extended.trades
    assert t0.reason == "STOP" and t1.reason == "STOP"
    keys = (
        "symbol",
        "entry",
        "exit",
        "reason",
        "qty",
        "signal_at",
        "fill_at",
        "exit_at",
        "gross_pnl",
        "costs",
        "net_pnl",
    )
    assert {k: getattr(t0, k) for k in keys} == {k: getattr(t1, k) for k in keys}


def test_the_run_does_not_modify_its_input_bars() -> None:
    rows = ORB_DAY + ENTRY_TAIL + STOP_TAIL
    sym = _sym(rows)
    before = (tuple(sym.bars_5m), tuple(sym.bars_15m), sym.prev_day, sym.tick)
    run_strategy_backtest(
        SID,
        "4a",
        [SessionInput(_spec(), [sym])],
        _small("pa-intraday", "0.5.0"),
        D("100000"),
        CostSchedule(),
        "e",
        "d",
        "u",
    )
    assert (tuple(sym.bars_5m), tuple(sym.bars_15m), sym.prev_day, sym.tick) == before


def test_today_s_detector_silently_changes_the_range_when_an_opening_bar_is_missing_the_strict_rule_rejects_it() -> (
    None
):
    """The defect of specification §17.1 item 1, pinned: without the 09:20 bar (the highest of the range) the
    current detector builds the range from the bars that exist and moves the trigger from 1496.5 to 1495.0. The
    strict rule (E3) is what E4 will call; today's detector is unchanged by this step."""
    from app.domain.setups.orb_range import OrbRangeReason, validate_opening_range

    bars = mk(ORB_DAY + ENTRY_TAIL)
    gap = [b for b in bars if b.start != bars[1].start]  # drop the 09:20 bar
    assert validate_opening_range(gap, OPEN).reason is OrbRangeReason.OR_MISSING_BAR
    p = _small("pa-intraday", "0.5.0")
    det = strategy_detectors(SID)

    def trigger(rows: list[Bar]) -> Decimal:
        r = analyse(rows, rows, OPEN, PREV, p, detectors=det, isolated=True, **KW)  # type: ignore[arg-type]
        assert r.setups is not None
        return next(s.setup.trigger_price for s in r.setups if s.setup.direction is SetupDirection.LONG)

    assert (trigger(bars), trigger(gap)) == (D("1496.5"), D("1495.0"))
