"""Strategy 02 Stage 3 tests (process §4): anchors, boundaries, lifecycle, data, look-ahead, replay and limits.

Complements `test_setups_failed_breakdown.py` (TV-SET-29..35). Hand-computed expected values; `pa-intraday 0.4.0`
rules (sbuf = bb = sb = 0.05%, N = 6, expiry 12). Level Y = PDL 1480: `Y x (1 - sbuf)` = 1479.26.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from app.domain.analyse import analyse
from app.domain.levels import trade_levels
from app.domain.risk.validation import validate_stop
from app.domain.setups.failed_breakdown import detect_failed_breakdown
from app.domain.setups.types import Setup, SetupContext, SetupStatus
from app.domain.snapshot import SnapshotStatus
from app.domain.types import PivotKind, SwingPoint
from app.domain.zone_cache import ZoneCache
from app.domain.zones import Zone, ZoneStatus
from app.rulesets import load_ruleset

from ._session import CLOSE, OPEN, D, ctx_for, mk
from .test_setups_failed_breakdown import BREAK, CONFIRM, HOLD, RECLAIM, SEQ
from .test_setups_sweep import LEAD

FAILED = load_ruleset("pa-intraday", "0.4.0")
Row = tuple[str, str, str, str]
NOLEVEL: dict[str, object] = {"pdh": None, "pdl": None}

# A day with no PDL; opening range bars 0-2 (OR low 1517), broken by the close of bar 3 (1512 < 1516.2415).
TOP: list[Row] = [
    ("1530", "1532", "1520", "1525"),  # 0
    ("1525", "1527", "1518", "1520"),  # 1
    ("1520", "1522", "1517", "1518"),  # 2  OR low 1517
    ("1518", "1519", "1510", "1512"),  # 3  close 1512 < 1516.2415: OR_LOW is broken here (no reclaim >= 1517)
]


def _ctx(rows: list[Row], **kw: object) -> SetupContext:
    kw.setdefault("pdh", "1510")
    kw.setdefault("pdl", "1480")
    kw.setdefault("params", FAILED)
    return ctx_for(mk(rows), **kw)  # type: ignore[arg-type]


def _setups(rows: list[Row], **kw: object) -> list[Setup]:
    return detect_failed_breakdown(_ctx(rows, **kw))[0]


# ---------------------------------------------------------------------------------------------- anchors


def test_anchor_or_low() -> None:
    # OR low 1487 (bars 0-2); bar 3 closes 1486 < 1486.2565 (the breakdown); bar 4 closes 1488 >= 1487.
    rows = [*LEAD[:4], ("1486", "1490", "1485.5", "1488"), ("1488", "1492", "1487.5", "1491")]
    [s] = _setups(rows, **NOLEVEL)
    assert (s.anchor, s.swept_level, s.breakdown_index, s.detected_at_index) == ("OR_LOW", D("1487"), 3, 4)
    # Break low = min(L[3], L[4]) = min(1485, 1485.5); trigger H[4] = 1490; bar 5 closes 1491 > 1490.745.
    assert (s.stop_base, s.trigger_price) == (D("1485"), D("1490"))
    assert (s.status, s.confirmed_at_index) == (SetupStatus.ENTRY_CONFIRMED, 5)


SWING: list[Row] = [
    *TOP,
    ("1512", "1513", "1500", "1505"),  # 4  pivot low 1500 (confirmed on bar 6)
    ("1505", "1510", "1503", "1508"),  # 5
    ("1508", "1512", "1506", "1510"),  # 6
    ("1510", "1511", "1497", "1498"),  # 7  close 1498 < 1499.25: first close below the swing low
    ("1498", "1503", "1497.5", "1500.5"),  # 8  close 1500.5 >= 1500: reclaim, trigger 1503, break low 1497
    ("1500.5", "1506", "1500", "1504"),  # 9  1504 > 1503 x 1.0005 = 1503.5015
]


def test_anchor_swing_low_5m() -> None:
    [s] = _setups(SWING, **NOLEVEL)
    assert (s.anchor, s.swept_level, s.breakdown_index, s.detected_at_index) == (
        "SWING_LOW_5M",
        D("1500"),
        7,
        8,
    )
    assert (s.stop_base, s.trigger_price) == (D("1497"), D("1503"))
    assert (s.status, s.confirmed_at_index) == (SetupStatus.ENTRY_CONFIRMED, 9)


def test_anchor_equal_lows_wins_the_tie_with_a_swing_low_at_the_same_price() -> None:
    # Second pivot low 1500.4 (confirmed on bar 10) makes the pool level min(1500, 1500.4) = 1500: the same price
    # as the swing low, so two anchors. One close breaks both; the reclaim bar reclaims both (the 1500.4
    # pivot itself stays unreclaimed); anchor order puts EQUAL_LOWS first. One setup per breakdown bar.
    day: list[Row] = [
        *SWING[:7],
        ("1510", "1512", "1507", "1509"),  # 7
        ("1509", "1510", "1500.4", "1503"),  # 8  pivot low 1500.4
        ("1503", "1506", "1501", "1504"),  # 9
        ("1504", "1507", "1502", "1506"),  # 10
        ("1503", "1504", "1497", "1498"),  # 11 close 1498 < 1499.25 (and < 1500.4 x 0.9995): breakdown
        ("1498", "1503", "1497.5", "1500.2"),  # 12 close 1500.2 >= 1500, < 1500.4: reclaims 1500 only
    ]
    out = _setups(day, **NOLEVEL)
    assert [(s.anchor, s.swept_level, s.breakdown_index, s.detected_at_index) for s in out] == [
        ("EQUAL_LOWS", D("1500"), 11, 12)
    ]


ZDAY: list[Row] = [
    *TOP,
    ("1512", "1513", "1505", "1508"),  # 4
    ("1508", "1510", "1504", "1506"),  # 5  close 1506 > zone high 1503: the zone is SUPPORT at bar 5
    ("1506", "1507", "1498", "1498.5"),  # 6  close 1498.5 < 1499.25: breakdown of Z.low 1500
    ("1498.5", "1503", "1498", "1500.5"),  # 7  close 1500.5 >= 1500: reclaim
]


class _FakeZones(ZoneCache):
    def __init__(self, zones: list[Zone]) -> None:
        super().__init__()
        self._fixed = zones

    def zones(self, *args: object, **kw: object) -> list[Zone]:  # type: ignore[override]
        return self._fixed


def _zone(low: str, high: str, status: ZoneStatus = ZoneStatus.ACTIVE) -> Zone:
    return Zone(D(low), D(high), (), 0, status=status)


def test_anchor_zone_low_of_an_active_support_zone_only() -> None:
    ctx = replace(_ctx(ZDAY, **NOLEVEL), zone_cache=_FakeZones([_zone("1500", "1503")]))
    [s] = detect_failed_breakdown(ctx)[0]
    assert (s.anchor, s.swept_level, s.breakdown_index, s.detected_at_index) == ("ZONE", D("1500"), 6, 7)
    assert s.zone is not None
    inside = replace(_ctx(ZDAY, **NOLEVEL), zone_cache=_FakeZones([_zone("1500", "1507")]))
    assert detect_failed_breakdown(inside)[0] == []  # the close of bar 5 is inside the zone: not support
    broken = replace(
        _ctx(ZDAY, **NOLEVEL), zone_cache=_FakeZones([_zone("1500", "1503", ZoneStatus.BROKEN_FLIPPED)])
    )
    assert detect_failed_breakdown(broken)[0] == []


def _pivot_15m(rows: list[Row], confirmed_bar: int) -> SwingPoint:
    bars = mk(rows)
    return SwingPoint(PivotKind.LOW, 0, D("1500"), bars[0].start, 0, bars[confirmed_bar].end)


def test_anchor_swing_low_15m_and_only_from_its_confirmation() -> None:
    ctx = _ctx(ZDAY, **NOLEVEL)
    known = replace(ctx, pivots_15m=[_pivot_15m(ZDAY, 2)])
    [s] = detect_failed_breakdown(known)[0]
    assert (s.anchor, s.swept_level, s.breakdown_index) == ("SWING_LOW_15M", D("1500"), 6)
    late = replace(ctx, pivots_15m=[_pivot_15m(ZDAY, 6)])  # confirmed by the bar that is the breakdown bar
    assert detect_failed_breakdown(late)[0] == []


# ------------------------------------------------------------------------------- several levels, one close


MULTI: list[Row] = [
    *LEAD,
    ("1482", "1482", "1476", "1477"),  # 5  close 1477 breaks PDL 1480 and the swing/OR levels below it
]


def test_the_level_reclaimed_first_wins_and_a_later_reclaim_cannot_replace_it() -> None:
    """PDL 1480 and a pivot-free OR low 1487 are both broken by bar 5's close region; the bar-3 OR_LOW is separate.

    Here two PDL-type levels are emulated with a second daily level through a 15m pivot at 1478: both are broken
    by the close of bar 5 (1477). Bar 6 reclaims 1478 only; bar 7 reclaims 1480. The earlier reclaim wins, and
    bar 7 does not change the setup found at bar 6 (no look-ahead).
    """
    pivot = SwingPoint(PivotKind.LOW, 0, D("1478"), mk(MULTI)[0].start, 0, mk(MULTI)[2].end)
    rows = [*MULTI, ("1477", "1479", "1476.5", "1478.5"), ("1478.5", "1481", "1478", "1480.5")]
    ctx = replace(_ctx(rows[:7]), pivots_15m=[pivot])
    [early] = detect_failed_breakdown(ctx)[0]
    assert (early.anchor, early.swept_level, early.detected_at_index) == ("SWING_LOW_15M", D("1478"), 6)
    full = replace(_ctx(rows), pivots_15m=[pivot])
    [later] = detect_failed_breakdown(full)[0]
    assert (later.anchor, later.swept_level, later.detected_at_index) == ("SWING_LOW_15M", D("1478"), 6)


def test_when_two_levels_are_reclaimed_on_the_same_bar_the_highest_wins() -> None:
    pivot = SwingPoint(PivotKind.LOW, 0, D("1478"), mk(MULTI)[0].start, 0, mk(MULTI)[2].end)
    rows = [*MULTI, ("1477", "1481", "1476.5", "1480.5")]  # close 1480.5 reclaims 1478 and 1480 together
    [s] = detect_failed_breakdown(replace(_ctx(rows), pivots_15m=[pivot]))[0]
    assert (s.anchor, s.swept_level) == ("PDL", D("1480"))


# ----------------------------------------------------------------------------------------- boundaries


def _row5(close: str, low: str = "1476") -> list[Row]:
    return [*LEAD, ("1482", "1482", low, close), RECLAIM]


def test_breakdown_close_exactly_at_the_buffer_is_not_a_breakdown_just_below_it_is() -> None:
    assert _setups(_row5("1479.26")) == []  # C = Y x (1 - sbuf): not below
    [s] = _setups(_row5("1479.25"))
    assert s.breakdown_index == 5


def test_reclaim_close_exactly_at_the_level_counts_just_below_does_not() -> None:
    [s] = _setups([*LEAD, BREAK, ("1477", "1481", "1476.5", "1480")])
    assert s.detected_at_index == 6
    assert _setups([*LEAD, BREAK, ("1477", "1481", "1476.5", "1479.99")]) == []


def test_confirmation_needs_a_close_strictly_above_the_trigger_buffer() -> None:
    # trigger 1481; 1481 x 1.0005 = 1481.7405
    [at] = _setups([*LEAD, BREAK, RECLAIM, ("1481", "1481.7405", "1481", "1481.7405")])
    [above] = _setups([*LEAD, BREAK, RECLAIM, ("1481", "1481.75", "1481", "1481.75")])
    assert at.status is SetupStatus.AWAITING_CONFIRMATION
    assert (above.status, above.confirmed_at_index) == (SetupStatus.ENTRY_CONFIRMED, 7)


def test_break_resumed_needs_a_close_below_the_buffer_not_at_it() -> None:
    [at] = _setups([*LEAD, BREAK, RECLAIM, ("1480", "1480", "1479", "1479.26")])
    [below] = _setups([*LEAD, BREAK, RECLAIM, ("1480", "1480", "1479", "1479.25")])
    assert at.status is SetupStatus.AWAITING_CONFIRMATION
    assert (below.status, below.end_reason) == (SetupStatus.INVALIDATED, "BREAK_RESUMED")


def test_a_wick_below_the_break_low_that_closes_above_the_buffer_does_not_invalidate() -> None:
    [s] = _setups([*LEAD, BREAK, RECLAIM, ("1480", "1480.5", "1474", "1479.5")])
    assert s.status is SetupStatus.AWAITING_CONFIRMATION  # the rule is a close below Y x (1 - sbuf)


def test_entry_cutoff_boundary() -> None:
    # Reclaim bar 6 ends 09:45 + 5 = 09:50 IST, which is 340 minutes before the 15:30 close.
    assert len(_setups([*LEAD, BREAK, RECLAIM], cutoff_minutes=340)) == 1
    assert _setups([*LEAD, BREAK, RECLAIM], cutoff_minutes=341) == []


# ------------------------------------------------------------------------------------------- lifecycle


def test_expiry_after_expiry_bars() -> None:
    day = [*LEAD, BREAK, RECLAIM, *[HOLD] * 12]  # bars 7..18: age 12 at bar 18
    [live] = _setups(day)
    assert live.status is SetupStatus.AWAITING_CONFIRMATION
    [dead] = _setups([*day, HOLD])  # bar 19: age 13 > 12
    assert (dead.status, dead.end_reason) == (SetupStatus.EXPIRED, "AGED_OUT")


def test_a_level_is_used_once_per_session() -> None:
    # Bar 7 closes below PDL again and bar 8 reclaims it: not a new breakdown, the level was already broken.
    rows = [*SEQ, ("1482", "1482", "1476", "1477"), ("1477", "1481", "1476.5", "1480.5")]
    assert [(s.anchor, s.breakdown_index) for s in _setups(rows)] == [("PDL", 5)]


# ----------------------------------------------------------------------------------------------- data


def test_gap_open_below_pdl_is_a_breakdown_on_the_first_session_bar() -> None:
    yesterday = mk(
        [("1495", "1496", "1494", "1495"), ("1495", "1496", "1494", "1495")], OPEN - timedelta(minutes=10)
    )
    today = mk(
        [
            ("1470", "1472", "1465", "1471"),  # close 1471 < 1479.26
            ("1471", "1483", "1470", "1481"),  # close 1481 >= 1480: reclaim
        ]
    )
    ctx = ctx_for([*yesterday, *today], pdh="1510", pdl="1480", params=FAILED)
    [s] = detect_failed_breakdown(ctx)[0]
    assert (s.anchor, s.breakdown_index, s.detected_at_index) == ("PDL", 2, 3)
    assert (s.stop_base, s.trigger_price) == (D("1465"), D("1483"))


def test_previous_session_bars_never_form_a_setup_in_this_session() -> None:
    yesterday = mk(SEQ, OPEN - timedelta(minutes=5 * len(SEQ)))
    today = mk([("1490", "1492", "1488", "1491")] * 4)
    ctx = ctx_for([*yesterday, *today], pdh="1510", pdl="1470", params=FAILED)
    assert detect_failed_breakdown(ctx)[0] == []


def test_a_missing_candle_is_not_filled() -> None:
    gapped = mk(SEQ)
    del gapped[4]  # a missing 5m bar: the detector sees the bars it is given and invents none
    ctx = ctx_for(gapped, pdh="1510", pdl="1480", params=FAILED)
    for s in detect_failed_breakdown(ctx)[0]:
        assert s.trigger_price == gapped[s.detected_at_index].high


def test_invalid_or_short_input_gives_no_signal() -> None:
    p = load_ruleset("pa-intraday", "0.4.0")
    b5 = mk(SEQ)
    short = analyse(
        b5, b5, OPEN, None, p, session_close=CLOSE, detectors=[detect_failed_breakdown], isolated=True
    )
    assert short.check.status is SnapshotStatus.INSUFFICIENT_HISTORY and short.signal is None
    dup = [*b5, b5[-1]]
    bad = analyse(
        dup, dup, OPEN, None, p, session_close=CLOSE, detectors=[detect_failed_breakdown], isolated=True
    )
    assert bad.check.status is SnapshotStatus.INVALID_INPUT and bad.signal is None


# ------------------------------------------------------------------------------ look-ahead and replay


def _key(s: Setup) -> tuple[object, ...]:
    return (s.anchor, s.swept_level, s.breakdown_index, s.detected_at_index, s.trigger_price, s.stop_base)


def test_a_setup_found_at_bar_k_is_identical_when_the_data_after_k_is_removed() -> None:
    """Every setup detected by bar k, from the full day and from the day cut at k, has the same identity."""
    pivot = SwingPoint(PivotKind.LOW, 0, D("1478"), mk(MULTI)[0].start, 0, mk(MULTI)[2].end)
    rows = [*MULTI, ("1477", "1479", "1476.5", "1478.5"), ("1478.5", "1481", "1478", "1480.5"), CONFIRM]

    def run(n: int) -> list[Setup]:
        return detect_failed_breakdown(replace(_ctx(rows[:n]), pivots_15m=[pivot]))[0]

    full = run(len(rows))
    for k in range(len(rows)):
        cut = {_key(s) for s in run(k + 1)}
        want = {_key(s) for s in full if s.detected_at_index <= k}
        assert cut == want, k


def test_bar_by_bar_replay_confirms_on_the_same_bars_as_a_single_full_run() -> None:
    rows = SEQ
    full = {s.confirmed_at_index for s in _setups(rows) if s.confirmed_at_index is not None}
    seen = set()
    for k in range(len(rows)):
        for s in _setups(rows[: k + 1]):
            if s.confirmed_at_index == k:
                seen.add(k)
    assert seen == full == {7}


# -------------------------------------------------------------------------------- stop-distance limits


def _stop_case(stop_base: str) -> tuple[Setup, SetupContext]:
    ctx = replace(_ctx(SEQ), tick=D("0.05"))
    [s] = detect_failed_breakdown(ctx)[0]
    return replace(s, stop_base=D(stop_base)), ctx


@pytest.mark.parametrize(
    ("stop_base", "stop", "errors"),
    [
        ("1476", "1475.25", []),  # 1476 x 0.9995 = 1475.262 rounds down to the 0.05 tick
        ("1480.5", "1479.75", []),  # distance 2.25 >= 1482 x 0.15% = 2.223
        ("1480.6", "1479.85", ["STOP_TOO_TIGHT"]),  # distance 2.15 < 2.223
        ("1453.2", "1452.45", []),  # distance 29.55 <= 1482 x 2% = 29.64
        ("1453", "1452.25", ["STOP_TOO_WIDE"]),  # distance 29.75 > 29.64
    ],
)
def test_structural_stop_is_tick_rounded_and_the_distance_limits_apply(
    stop_base: str, stop: str, errors: list[str]
) -> None:
    s, ctx = _stop_case(stop_base)
    lv = trade_levels(s, ctx, [])
    assert lv is not None and lv.stop == D(stop)
    assert validate_stop(lv.entry, lv.stop, D("0.05"), D("0.15"), D("2.0")) == errors


def test_a_target_below_the_minimum_reward_to_risk_is_flagged() -> None:
    # Only PDH 1484 (0.30R) and the 1493 session / opening-range highs (1.63R) are above the entry 1482.
    ctx = _ctx(SEQ, pdh="1484", pdl="1480")
    [s] = detect_failed_breakdown(ctx)[0]
    lv = trade_levels(s, ctx, [])
    assert lv is not None and lv.rr_below_min is True
    assert lv.target is not None and lv.rr is not None and lv.rr < D("2")
