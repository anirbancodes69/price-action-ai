"""Session replay (TRD-06 §2, §4, §6) with a scripted analysis function.

The domain analysis is covered elsewhere; here each symbol emits `ENTRY_CONFIRMED` at a chosen bar so the
fill, exit, sizing and account behaviour can be checked against hand-computed numbers.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.backtest.costs import CostSchedule
from app.backtest.replay import SessionSpec, SymbolData, replay_session
from app.domain.analyse import AnalysisResult
from app.domain.htf import HtfContext
from app.domain.levels import TradeLevels
from app.domain.params import RulesetParams
from app.domain.risk.account import RiskProfile
from app.domain.setups.scoring import Paqs
from app.domain.setups.signal import ScoredSetup, Signal, SignalResult
from app.domain.setups.types import Setup, SetupDirection, SetupStatus, SetupType
from app.domain.snapshot import SnapshotCheck, SnapshotStatus
from app.domain.types import (
    Bar,
    BarState,
    Direction,
    EventType,
    StructureEvent,
    StructureResult,
    StructureState,
)
from app.rulesets import load_ruleset

D = Decimal
OPEN = datetime(2026, 11, 18, 3, 45, tzinfo=UTC)  # 09:15 IST
CLOSE = OPEN + timedelta(hours=6, minutes=15)
BASE = load_ruleset("pa-intraday", "0.1.0")
PROFILE = RiskProfile(D("100000"), D("0.5"), D("50000"), D("1.5"), 3, 2, D("1.0"))
SCHEDULE = CostSchedule()


def params(**over: object) -> RulesetParams:
    return RulesetParams(BASE.code, BASE.version, {**BASE.values, **over})


def bars(rows: list[tuple[str, str, str, str]]) -> list[Bar]:
    out = []
    for i, (o, h, lo, c) in enumerate(rows):
        s = OPEN + timedelta(minutes=5 * i)
        out.append(Bar(s, s + timedelta(minutes=5), D(o), D(h), D(lo), D(c)))
    return out


FLAT = ("100", "100.2", "99.8", "100")


def day(overrides: dict[int, tuple[str, str, str, str]], n: int = 10) -> list[Bar]:
    return bars([overrides.get(i, FLAT) for i in range(n)])


def sym(name: str, rows: list[Bar]) -> SymbolData:
    return SymbolData(name, rows, [], None, D("0.05"))


def make_analyse(signals: dict[tuple[str, int], int], chochs: dict[tuple[str, int], bool] | None = None):  # type: ignore[no-untyped-def]
    """`signals[(symbol, bar_index)] = paqs`: ENTRY_CONFIRMED at that bar's close."""
    chochs = chochs or {}

    def fn(s: SymbolData, k: int, spec: SessionSpec, p: RulesetParams) -> AnalysisResult:
        i = k - 1
        bar = s.bars_5m[i]
        events = ()
        if chochs.get((s.symbol, i)):
            events = (
                StructureEvent(EventType.CHOCH, Direction.DOWN, D("99"), 0, i, bar.start, bar.close, i),
            )
        struct = StructureResult((), events, ())
        htf = HtfContext(0, BarState(StructureState.BULLISH, None, None, None))
        sig = SignalResult(Signal.NO_TRADE, None, ("NO_SETUP",), bar.end, None)
        paqs = signals.get((s.symbol, i))
        if paqs is not None:
            setup = Setup(
                SetupType.OPENING_RANGE_BREAKOUT,
                SetupDirection.LONG,
                SetupStatus.ENTRY_CONFIRMED,
                i,
                D("100"),
                "OR_HIGH",
                confirmed_at_index=i,
                confirm_close=D("100"),
            )
            lv = TradeLevels(D("100"), D("99"), D("103"), "TEST", D("1"), D("3"), False)
            sig = SignalResult(
                Signal.ENTRY_CONFIRMED, ScoredSetup(setup, Paqs("t", paqs, ()), lv), (), bar.end, bar.end
            )
        return AnalysisResult(
            "pa-intraday",
            "0.1.0",
            SnapshotCheck(SnapshotStatus.VALID, ()),
            "",
            "",
            struct,
            None,
            htf,
            None,
            signal=sig,
        )

    return fn


def run(symbols, analyse_fn, p=BASE, profile=PROFILE, close=CLOSE):  # type: ignore[no-untyped-def]
    spec = SessionSpec(OPEN.date(), OPEN, close)
    return replay_session(symbols, spec, p, profile, SCHEDULE, analyse_fn)


def test_signal_fills_next_open_and_exits_at_target() -> None:
    """Signal at bar 2 -> fill at bar 3's open 100 x 1.0005 = 100.05; qty min(500, 476, 499) = 476;
    bar 4 reaches the 103 target. Gross 2.95 x 476 = 1404.20, costs 51.41 (hand-computed), net 1352.79."""
    rows = day({3: ("100", "100.5", "99.9", "100.2"), 4: ("100.2", "103.5", "100", "103")})
    r = run([sym("A", rows)], make_analyse({("A", 2): 80}))
    [t] = r.trades
    assert (t.entry, t.qty, t.exit, t.reason) == (D("100.0500"), 476, D("103"), "TARGET")
    assert (t.signal_at, t.fill_at) == (rows[2].end, rows[3].start)
    assert (t.gross_pnl, t.costs, t.net_pnl) == (D("1404.2000"), D("51.41"), D("1352.7900"))
    assert t.risk_amount == D("499.8000") and r.net_pnl == t.net_pnl and r.skips == ()


def test_stop_collision_and_gap_exits_take_slippage() -> None:
    stop_bar = day({3: FLAT, 4: ("100", "100.5", "98.9", "99")})
    [t] = run([sym("A", stop_bar)], make_analyse({("A", 2): 80})).trades
    assert (t.reason, t.exit) == ("STOP", D("99") * D("0.9995"))
    collision = day({4: ("100", "103.5", "98.9", "99")})
    assert run([sym("A", collision)], make_analyse({("A", 2): 80})).trades[0].reason == "STOP_COLLISION"
    gap = day({4: ("98.5", "99", "98", "98.2")})
    [g] = run([sym("A", gap)], make_analyse({("A", 2): 80})).trades
    assert (g.reason, g.exit) == ("STOP_GAP", D("98.5") * D("0.9995"))
    assert g.net_pnl < g.gross_pnl < 0


def test_gap_up_skips_entry() -> None:
    rows = day({3: ("101", "101.5", "100.8", "101.2")})  # limit 100 x 1.003 = 100.3
    r = run([sym("A", rows)], make_analyse({("A", 2): 80}))
    assert r.trades == () and [s.reason for s in r.skips] == ["SKIPPED_GAP_UP"]


def test_account_limits_and_paqs_priority_at_the_same_close() -> None:
    """Two signals at one close, one position allowed: higher PAQS gets the order, the other is skipped."""
    one = RiskProfile(D("100000"), D("0.5"), D("50000"), D("1.5"), 3, 1, D("1.0"))
    rows = day({})
    sigs = {("A", 2): 70, ("B", 2): 90}
    r = run([sym("A", rows), sym("B", rows)], make_analyse(sigs), profile=one)
    assert [(t.symbol, t.paqs) for t in r.trades] == [("B", 90)]
    assert [(s.symbol, s.reason) for s in r.skips] == [("A", "MAX_POSITIONS_REACHED")]
    # equal PAQS: symbol ascending
    r2 = run([sym("B", rows), sym("A", rows)], make_analyse({("A", 2): 80, ("B", 2): 80}), profile=one)
    assert [t.symbol for t in r2.trades] == ["A"]


def test_one_position_per_symbol() -> None:
    r = run([sym("A", day({}))], make_analyse({("A", 2): 80, ("A", 4): 80}))
    assert len(r.trades) == 1 and [s.reason for s in r.skips] == ["ALREADY_IN_POSITION"]


def test_structure_exit_at_next_open() -> None:
    rows = day({4: ("100.4", "100.6", "100.1", "100.3")})
    r = run([sym("A", rows)], make_analyse({("A", 2): 80}, {("A", 3): True}))
    [t] = r.trades
    assert (t.reason, t.exit, t.exit_at) == ("STRUCTURE_EXIT", D("100.4"), rows[4].start)
    # disabled by the ruleset
    off = run(
        [sym("A", rows)],
        make_analyse({("A", 2): 80}, {("A", 3): True}),
        p=params(**{"exit.structure_exit_enabled": False}),
    )
    assert off.trades[0].reason != "STRUCTURE_EXIT"


def test_session_end_exit_and_end_of_data() -> None:
    rows = day({7: ("100.3", "100.4", "100.0", "100.1")})
    # close = OPEN + 50 min, cutoff 10 min before it, session-end exit at OPEN + 35 min = start of bar 7
    p = params(**{"session.entry_cutoff_minutes_before_close": 10})
    r = run([sym("A", rows)], make_analyse({("A", 2): 80}), p=p, close=OPEN + timedelta(minutes=50))
    [t] = r.trades
    assert (t.reason, t.exit, t.end_of_data) == ("SESSION_END", D("100.3"), False)
    # data ends well before the exit time: END_OF_DATA at the last close, flagged
    [e] = run([sym("A", rows[:6])], make_analyse({("A", 2): 80})).trades
    assert (e.reason, e.exit, e.end_of_data) == ("END_OF_DATA", rows[5].close, True)


def test_no_fill_bar_skips_the_order() -> None:
    rows = day({})
    short = rows[:3]  # the signal bar is the last bar: no next open exists
    r = run([sym("A", short)], make_analyse({("A", 2): 80}))
    assert r.trades == () and [s.reason for s in r.skips] == ["SKIPPED_NO_BAR"]


def test_daily_loss_limit_blocks_later_entries() -> None:
    """A stop-out of ~₹499.8 x 3 reaches ... use a small limit so one loss blocks the next signal."""
    small = RiskProfile(D("100000"), D("0.5"), D("50000"), D("0.4"), 3, 2, D("1.0"))  # limit ₹400
    stop = {4: ("100", "100.1", "98.9", "99")}
    rows = day(stop, n=12)
    r = run([sym("A", rows)], make_analyse({("A", 2): 80, ("A", 6): 80}), profile=small)
    assert [t.reason for t in r.trades] == ["STOP"]
    assert [s.reason for s in r.skips] == ["ACCOUNT_LIMIT"]
