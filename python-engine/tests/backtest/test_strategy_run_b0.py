"""E4/E7: the B0 strategy in the single-strategy run mode (hand-built bars; no database, no stored candle)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from app.backtest.costs import CostSchedule
from app.backtest.replay import SymbolData
from app.backtest.run import SessionInput
from app.backtest.strategy_run import run_strategy_backtest
from app.domain.analyse import analyse
from app.domain.session import DailyLevels
from app.domain.setups.signal import Signal
from app.domain.strategies import strategy_detectors
from app.domain.types import Bar

from ..trading._session import CLOSE, OPEN, mk
from .b0_support import INDEPENDENT_RD, ctx
from .test_strategy_run import _small, _spec

pytestmark = pytest.mark.usefixtures("small_b0_hash")

D = Decimal
SID = "orb_b0"
PREV = DailyLevels(D("1100"), D("990"), D("1000"))
OR3 = [("1002", "1005", "1000", "1003"), ("1003", "1004", "1001", "1002"), ("1002", "1003", "1000.5", "1001")]
QUIET, BREAK = ("1003", "1004", "1001", "1003"), ("1003", "1007", "1002", "1006")
HIT_TARGET = [("1005", "1020", "1004", "1019")]  # opens 0.1 % under the signal close: see the F-1 test below
HIT_STOP = [("1005", "1007", "999", "999.2")]  # stop 999.50
WILD = [("1000", "5000", "1", "2")] * 3  # nothing after the exit may change the trade
KW = {"previous_session_open": None, "session_close": CLOSE}


def _sym(rows: list[tuple[str, str, str, str]], tick: str | None = "0.05") -> SymbolData:
    bars: list[Bar] = mk(rows)
    return SymbolData("A", bars, bars, PREV, D(tick) if tick else None)


def _run(rows: list[tuple[str, str, str, str]], tick: str | None = "0.05", **ref: str):  # type: ignore[no-untyped-def]
    p = _small("pa-intraday", "0.6.0")
    inputs = [SessionInput(_spec(), [_sym(rows, tick)])]
    return run_strategy_backtest(
        SID,
        "4a",
        inputs,
        p,
        D("100000"),
        CostSchedule(),
        "e",
        "d",
        "u",
        reference_data={**INDEPENDENT_RD, **ref},
        b0_context=ctx(p, {**INDEPENDENT_RD, **ref}),
    )


def test_the_registry_has_the_separate_b0_strategy_and_the_current_detector_is_untouched() -> None:
    from app.domain.setups.opening_range import detect_opening_range
    from app.domain.setups.orb_b0 import detect_orb_b0

    assert strategy_detectors(SID) == (detect_orb_b0,)
    assert strategy_detectors("opening_range_breakout") == (detect_opening_range,)


def test_isolated_signal_is_an_entry_with_a_two_r_target_and_no_score() -> None:
    p = _small("pa-intraday", "0.6.0")
    b5 = mk([*OR3, QUIET, BREAK])
    r = analyse(b5, b5, OPEN, PREV, p, detectors=strategy_detectors(SID), isolated=True, **KW)  # type: ignore[arg-type]
    assert r.signal is not None and r.signal.signal is Signal.ENTRY_CONFIRMED and r.signal.primary is not None
    lv = r.signal.primary.levels
    assert lv is not None and (lv.stop, lv.target, lv.rr) == (D("999.50"), D("1019.00"), D(2))
    assert r.signal.primary.paqs is None


def test_a_run_exits_at_the_two_r_target_and_ignores_everything_after() -> None:
    a = _run([*OR3, QUIET, BREAK, *HIT_TARGET])
    b = _run([*OR3, QUIET, BREAK, *HIT_TARGET, *WILD])
    assert len(a.trades) == 1 and a.trades[0].reason == "TARGET"
    assert a.trades == b.trades  # no look-ahead past the exit
    assert a.trades[0].anchor == "OR_HIGH"


def test_a_run_exits_at_the_stop_and_a_session_with_no_breakout_does_not_trade() -> None:
    assert _run([*OR3, QUIET, BREAK, *HIT_STOP]).trades[0].reason == "STOP"
    assert _run(OR3 + [QUIET] * 8).trades == ()


def test_the_structure_exit_is_off_in_0_6_0() -> None:
    assert _small("pa-intraday", "0.6.0").values["exit.structure_exit_enabled"] is False


def test_provider_adjusted_scale_runs_without_tick_rounding() -> None:
    r = _run([*OR3, QUIET, BREAK, *HIT_TARGET], tick=None)
    assert len(r.trades) == 1 and r.trades[0].reason == "TARGET"


def test_the_run_record_carries_the_reference_hashes_and_resolver_version() -> None:
    ref = {"tick_table_sha256": "a" * 64, "tick_resolver_version": "tick-resolver-1.0.0",
           "session_table_sha256": "b" * 64, "event_table_sha256": "c" * 64}  # fmt: skip
    r = _run([*OR3, QUIET, BREAK, *HIT_TARGET], **ref)
    assert {k: r.record.reference_data[k] for k in ref} == ref
    assert r.record.ruleset == "pa-intraday 0.6.0" and r.record.strategy_id == SID
    assert replace(r.record, reference_data={}).reference_data == {}
    assert _run([*OR3, QUIET, BREAK, *HIT_TARGET]).record.reference_data == INDEPENDENT_RD


def test_the_run_is_deterministic() -> None:
    rows = [*OR3, QUIET, BREAK, *HIT_TARGET]
    assert _run(rows).trades == _run(rows).trades
    assert _run(rows).record == _run(rows).record


def test_finding_f1_a_flat_open_is_skipped_because_the_fixed_2r_target_meets_entry_slippage() -> None:
    """Pins a design interaction for the owner (not changed here; B0 is frozen).

    T1 = down(E + 2R) is measured from the signal close E, and `ORB-RC-04` rejects a fill whose reward-to-risk
    is below `risk.min_rr` = 2.0. The fill is the next open raised by the 0.05 % entry slippage, so rr at the fill
    is below 2.0 whenever that fill is above E. Only an open at least 0.05 % under the signal close trades.
    """
    flat = _run([*OR3, QUIET, BREAK, ("1006", "1020", "1005", "1019")])
    assert flat.trades == () and [k.reason for k in flat.skips] == ["SKIPPED_RR_DEGRADED"]
    under = _run([*OR3, QUIET, BREAK, ("1005.4", "1020", "1004", "1019")])
    assert len(under.trades) == 1  # 1005.4 x 1.0005 = 1005.90 <= 1006: the fill is not above E
