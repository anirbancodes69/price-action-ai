"""TV-REF-01..03, TV-SES-01..03, snapshot status and analyse (TRD-01 §4, TRD-03 §8, TRD-02 §10)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.analyse import analyse
from app.domain.candles import missing_bar_starts
from app.domain.params import RulesetParams
from app.domain.serialise import analysis_hash, analysis_to_canonical
from app.domain.session import DailyLevels, entry_cutoff, session_exit_time, session_levels
from app.domain.snapshot import SnapshotStatus, check_snapshot
from app.domain.types import Bar, EventType, StructureState
from app.rulesets import load_ruleset

from ._bars import bars_from, bars_hlc
from .test_structure import BASE, BOS_BAR, BUF, EQ, TAIL, run  # noqa: F401

OPEN = datetime(2026, 11, 18, 3, 45, tzinfo=UTC)  # 09:15 IST
D = Decimal


def five_min(rows: list[tuple[str, str, str, str]], start: datetime = OPEN) -> list[Bar]:
    out = []
    for i, (o, h, lo, c) in enumerate(rows):
        s = start + timedelta(minutes=5 * i)
        out.append(Bar(s, s + timedelta(minutes=5), D(o), D(h), D(lo), D(c)))
    return out


SESSION = [
    ("100", "102", "99", "101"),  # 09:15-09:20
    ("101", "104", "100", "103"),  # 09:20-09:25
    ("103", "105", "101", "102"),  # 09:25-09:30  last OR bar
    ("102", "110", "98", "109"),  # 09:30-09:35
]
PREV = DailyLevels(D("120"), D("90"), D("95"))


def test_tv_ref_01_opening_range() -> None:
    bars = five_min(SESSION)
    lv = session_levels(bars[:3], OPEN, PREV, 15)
    assert (lv.or_high, lv.or_low) == (D("105"), D("99"))
    # absent while the last OR bar (ending 09:30) has not closed
    lv2 = session_levels(bars[:2], OPEN, PREV, 15)
    assert (lv2.or_high, lv2.or_low) == (None, None)
    # later bars never change it
    lv3 = session_levels(bars, OPEN, PREV, 15)
    assert (lv3.or_high, lv3.or_low) == (D("105"), D("99"))


def test_tv_ref_02_missing_previous_session() -> None:
    lv = session_levels(five_min(SESSION), OPEN, None, 15)
    assert (lv.pdh, lv.pdl, lv.pdc) == (None, None, None)
    lv = session_levels(five_min(SESSION), OPEN, PREV, 15)
    assert (lv.pdh, lv.pdl, lv.pdc) == (D("120"), D("90"), D("95"))


def test_tv_ref_03_session_high_low_exclude_previous_session() -> None:
    prev_session = five_min([("500", "600", "400", "500")], OPEN - timedelta(days=1))
    lv = session_levels([*prev_session, *five_min(SESSION)], OPEN, PREV, 15)
    assert (lv.session_high, lv.session_low) == (D("110"), D("98"))
    assert session_levels([], OPEN, PREV, 15).session_high is None


def test_entry_cutoff_and_exit_time() -> None:
    close = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)  # 15:30 IST
    assert entry_cutoff(close, 45) == datetime(2026, 11, 18, 9, 15, tzinfo=UTC)  # 14:45 IST
    assert session_exit_time(close, 15) == datetime(2026, 11, 18, 9, 45, tzinfo=UTC)  # 15:15 IST


def test_tv_ses_01_structure_crosses_session_boundary() -> None:
    """The series is continuous across sessions: a pivot on the previous day's last bars is
    confirmed by the next session's first bars, and a break happens on the second session's bars."""
    day2 = OPEN + timedelta(days=1)
    rows = [*BASE, BOS_BAR]
    split = 9  # bars 0..8 on day 1; 9.. on day 2 (HIGH@8 is confirmed by day-2 bars)
    d1 = bars_hlc(rows)[:split]
    d2 = [
        replace(b, start=day2 + timedelta(minutes=5 * i), end=day2 + timedelta(minutes=5 * (i + 1)))
        for i, b in enumerate(bars_hlc(rows)[split:])
    ]
    series = [*d1, *d2]
    from app.domain.pivots import detect_pivots, label_pivots
    from app.domain.structure import run_structure

    r = run_structure(series, label_pivots(detect_pivots(series, 2, 2), EQ), BUF)
    assert r.states[-1].state is StructureState.BULLISH
    assert [e.type for e in r.events] == [EventType.BOS]
    assert r.events[0].level_pivot_index == 8 and r.events[0].break_index == 11


def test_tv_ses_02_opening_gap_closing_beyond_level_breaks_on_first_bar() -> None:
    """Day-2 first bar gaps above HIGH@8 (107) and closes at 109: BOS on that very bar (index 11)."""
    day2 = OPEN + timedelta(days=1)
    rows = bars_hlc([*BASE, ("112", "108", "109")])
    series = [*rows[:11], replace(rows[11], start=day2, end=day2 + timedelta(minutes=5))]
    from app.domain.pivots import detect_pivots, label_pivots
    from app.domain.structure import run_structure

    r = run_structure(series, label_pivots(detect_pivots(series, 2, 2), EQ), BUF)
    assert [(e.type, e.break_index) for e in r.events] == [(EventType.BOS, 11)]


def test_tv_ses_03_missing_bar_marks_inputs_incomplete() -> None:
    bars = five_min(SESSION)
    del bars[1]
    step = timedelta(minutes=5)
    assert missing_bar_starts(bars, step) == [OPEN + timedelta(minutes=5)]
    # the series is still analysed as stored
    p = replace_params(min5=1, min15=1)
    assert check_snapshot(bars, five_min(SESSION), p).status is SnapshotStatus.VALID
    # an overnight gap is a session break, not missing bars
    day2 = five_min(SESSION, OPEN + timedelta(days=1))
    assert missing_bar_starts([*five_min(SESSION), *day2], step, session_gap=timedelta(hours=12)) == []


def replace_params(min5: int, min15: int) -> RulesetParams:
    base = load_ruleset("pa-intraday", "0.1.0")
    return RulesetParams(
        base.code, base.version, {**base.values, "analysis.min_bars_5m": min5, "analysis.min_bars_15m": min15}
    )


def test_snapshot_status() -> None:
    p = load_ruleset("pa-intraday", "0.1.0")
    bars = five_min(SESSION)
    assert check_snapshot(bars, bars, p).status is SnapshotStatus.INSUFFICIENT_HISTORY
    bad = bars_from([("10", "9", "8", "11")])
    chk = check_snapshot(bad, bars, p)  # invalid input wins over short history
    assert chk.status is SnapshotStatus.INVALID_INPUT and chk.problems == ("5m bar 0: OHLC out of order",)
    assert check_snapshot(bars, bars, replace_params(4, 4)).status is SnapshotStatus.VALID
    assert check_snapshot(bars, bars, replace_params(5, 4)).status is SnapshotStatus.INSUFFICIENT_HISTORY


def test_analyse_not_valid_has_no_analysis() -> None:
    p = load_ruleset("pa-intraday", "0.1.0")
    bars = five_min(SESSION)
    r = analyse(bars, bars, OPEN, PREV, p)
    assert r.check.status is SnapshotStatus.INSUFFICIENT_HISTORY
    assert (r.structure_5m, r.structure_15m, r.htf, r.levels) == (None, None, None, None)


def test_analyse_valid_run_is_deterministic_and_complete() -> None:
    p = replace_params(10, 10)
    rows = [*BASE, BOS_BAR, *TAIL]
    b5 = bars_from([(c, h, lo, c) for h, lo, c in rows])  # open = close keeps every bar valid
    b15 = [replace(b, end=b.start + timedelta(minutes=15)) for b in b5]  # stand-in 15m series
    r1 = analyse(b5, b15, b5[0].start, PREV, p)
    r2 = analyse(b5, b15, b5[0].start, PREV, p)
    assert r1.check.status is SnapshotStatus.VALID
    assert r1.structure_5m is not None and r1.structure_5m.final.state is StructureState.BEARISH
    assert r1.htf is not None and r1.htf.index is not None
    assert r1.levels is not None and (r1.levels.session_high, r1.levels.session_low) == (D("110"), D("94"))
    assert analysis_to_canonical(r1) == analysis_to_canonical(r2)
    assert analysis_hash(r1) == analysis_hash(r2)
    changed = analyse(b5[:-1], b15[:-1], b5[0].start, PREV, p)
    assert analysis_hash(changed) != analysis_hash(r1)
