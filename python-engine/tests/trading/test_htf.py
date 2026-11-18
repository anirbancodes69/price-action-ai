"""TV-HTF-01..04 (TRD-02 §9) and candle validation / canonical hash (TRD-01 §4, PE-07)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.candles import candles_hash, validate_bars
from app.domain.htf import align_htf
from app.domain.serialise import result_hash, structure_to_canonical
from app.domain.structure import run_structure
from app.domain.types import Bar, StructureState

from ._bars import bars_from, bars_hlc
from .test_structure import BASE, BOS_BAR, BUF, TAIL, run

DAY = datetime(2026, 11, 18, tzinfo=UTC)


def _ist(h: int, m: int) -> datetime:
    return DAY + timedelta(hours=h, minutes=m) - timedelta(hours=5, minutes=30)


def _htf_bar(end_h: int, end_m: int, o: str = "100", c: str = "100") -> Bar:
    end = _ist(end_h, end_m)
    d = Decimal
    return Bar(end - timedelta(minutes=15), end, d(o), max(d(o), d(c)) + 1, min(d(o), d(c)) - 1, d(c))


def test_tv_htf_01_forming_15m_bar_is_ignored() -> None:
    """15m bars end 10:00, 10:15, 10:30. 5m end 10:25 sees the 10:15 bar only."""
    htf = [_htf_bar(10, 0), _htf_bar(10, 15), _htf_bar(10, 30)]
    res = run_structure(htf, [], BUF)
    ctx = align_htf([_ist(10, 25)], htf, res)
    assert ctx[0].index == 1


def test_tv_htf_02_same_end_is_included() -> None:
    htf = [_htf_bar(10, 0), _htf_bar(10, 15), _htf_bar(10, 30)]
    ctx = align_htf([_ist(10, 30)], htf, run_structure(htf, [], BUF))
    assert ctx[0].index == 2


def test_before_first_15m_bar_has_no_context() -> None:
    htf = [_htf_bar(9, 30)]
    ctx = align_htf([_ist(9, 20), _ist(9, 25), _ist(9, 30)], htf, run_structure(htf, [], BUF))
    assert [c.index for c in ctx] == [None, None, 0]
    assert ctx[0].state is None


def test_tv_htf_03_choch_visible_only_from_its_bar_end() -> None:
    """Reuse the structure fixture as a 15m series; its CHoCH is bar 12. 5m runs before that bar's end see
    BULLISH (bar 11), from the end on they see TRANSITION."""
    bars = bars_hlc([*BASE, BOS_BAR, *TAIL])
    rows = [*BASE, BOS_BAR, *TAIL]
    result = run(rows)
    end12 = bars[12].end
    ctx = align_htf([end12 - timedelta(minutes=5), end12], bars, result)
    assert ctx[0].state is not None and ctx[0].state.state is StructureState.BULLISH
    assert ctx[1].state is not None and ctx[1].state.state is StructureState.TRANSITION


def test_tv_htf_04_later_bars_do_not_change_earlier_context() -> None:
    """Mutating 15m bars after `t` (the forming bar and beyond) leaves the context at `t` unchanged."""
    rows = [*BASE, BOS_BAR, *TAIL]
    bars = bars_hlc(rows)
    t_end = bars[12].end  # bar 13 and later have not closed
    a = align_htf([t_end], bars, run(rows))[0]
    mutated_rows = [*rows[:13], *[("500", "1", "2")] * (len(rows) - 13)]
    b = align_htf([t_end], bars_hlc(mutated_rows), run(mutated_rows))[0]
    assert a.index == b.index == 12
    assert a.state == b.state


def test_validate_bars() -> None:
    good = bars_from([("10", "12", "9", "11"), ("11", "13", "10", "12")])
    assert validate_bars(good) == []
    bad_ohlc = bars_from([("10", "9", "8", "11")])
    assert validate_bars(bad_ohlc) == ["bar 0: OHLC out of order"]
    assert validate_bars(bars_from([("0", "1", "0", "1")]))[0] == "bar 0: non-positive price"
    assert validate_bars([good[0], good[0]]) == ["bar 1: duplicate start"]
    assert validate_bars([good[1], good[0]]) == ["bar 1: out of order"]


def test_candles_hash_is_stable_and_sensitive() -> None:
    bars = bars_hlc(BASE)
    assert candles_hash(bars) == candles_hash(bars_hlc(BASE))
    changed = [*BASE[:-1], ("107", "103", "104")]
    assert candles_hash(bars) != candles_hash(bars_hlc(changed))
    assert len(candles_hash(bars)) == 64


def test_result_hash_canonical_and_deterministic() -> None:
    """TV-NLA-04: two runs give byte-identical canonical output and the same hash."""
    rows = [*BASE, BOS_BAR, *TAIL]
    r1, r2 = run(rows), run(rows)
    assert structure_to_canonical(r1) == structure_to_canonical(r2)
    assert result_hash(r1) == result_hash(r2)
    assert result_hash(run(rows[:-1])) != result_hash(r1)
    assert " " not in structure_to_canonical(r1)
