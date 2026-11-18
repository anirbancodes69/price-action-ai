"""TV-PIV-01..06 and TV-STR-08 (TRD-02 §3, §4). Expected values are hand-computed."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.domain.pivots import detect_pivots, label_pivots
from app.domain.types import PivotKind, SwingLabel, SwingPoint

from ._bars import bars_from, bars_hlc

# TRD-02 §3.5 example, L=R=2. (high, low, close); bar 12 is the swing high 104.0.
SEC_3_5 = [
    ("100.0", "97.0", "99.0"),  # 8
    ("100.5", "97.5", "99.5"),  # 9
    ("101.0", "98.0", "100.0"),  # 10
    ("102.5", "99.0", "101.0"),  # 11
    ("104.0", "100.5", "103.0"),  # 12
    ("103.2", "100.0", "101.0"),  # 13
    ("104.0", "99.6", "100.0"),  # 14
    ("102.0", "98.8", "99.0"),  # 15
]


def test_tv_piv_01_clean_swing_high() -> None:
    """TRD-02 §3.5: pivot at bar 12 (index 4 here), confirmed at index 6 = i + R."""
    bars = bars_hlc(SEC_3_5)
    highs = [p for p in detect_pivots(bars, 2, 2) if p.kind is PivotKind.HIGH]
    assert [(p.index, p.price, p.confirmed_at_index) for p in highs] == [(4, Decimal("104.0"), 6)]
    assert highs[0].confirmed_at == bars[6].end
    assert highs[0].bar_start == bars[4].start


def test_tv_piv_02_truncated_before_confirmation() -> None:
    """Snapshot ending at i+1 (index 5) must not contain the pivot."""
    bars = bars_hlc(SEC_3_5)[:6]
    assert [p for p in detect_pivots(bars, 2, 2) if p.kind is PivotKind.HIGH] == []
    # ...and it appears as soon as bar i+2 has closed.
    bars = bars_hlc(SEC_3_5)[:7]
    assert len([p for p in detect_pivots(bars, 2, 2) if p.kind is PivotKind.HIGH]) == 1


def test_tv_piv_03_equal_highs_only_first() -> None:
    """Consecutive equal highs: only the first can be a pivot (strict left test)."""
    rows = [
        ("100", "95", "98"),
        ("101", "96", "99"),
        ("105", "97", "104"),
        ("105", "98", "104"),
        ("103", "97", "100"),
        ("102", "96", "99"),
        ("101", "95", "98"),
    ]
    highs = [p for p in detect_pivots(bars_hlc(rows), 2, 2) if p.kind is PivotKind.HIGH]
    assert [p.index for p in highs] == [2]


def test_tv_piv_04_equal_high_on_right_side_still_valid() -> None:
    """§3.5: H[i+2] = H[i] keeps the pivot (non-strict right test); bar 14 is not a pivot."""
    highs = [p for p in detect_pivots(bars_hlc(SEC_3_5), 2, 2) if p.kind is PivotKind.HIGH]
    assert [p.index for p in highs] == [4]  # index 6 (bar 14, equal high) is absent


def test_tv_piv_05_outside_bar_emits_both_ordered_by_colour() -> None:
    """Bar 2 is higher and lower than 2 bars each side. Bullish -> low first; bearish -> high first."""

    def rows(open_: str, close: str) -> list[tuple[str, str, str, str]]:
        return [
            ("100", "101", "99", "100"),
            ("100", "101", "99", "100"),
            (open_, "110", "90", close),
            ("100", "101", "99", "100"),
            ("100", "101", "99", "100"),
        ]

    bull = detect_pivots(bars_from(rows("95", "105")), 2, 2)
    assert [(p.kind, p.index) for p in bull] == [(PivotKind.LOW, 2), (PivotKind.HIGH, 2)]
    bear = detect_pivots(bars_from(rows("105", "95")), 2, 2)
    assert [(p.kind, p.index) for p in bear] == [(PivotKind.HIGH, 2), (PivotKind.LOW, 2)]
    flat = detect_pivots(bars_from(rows("100", "100")), 2, 2)  # close >= open counts as bullish
    assert [p.kind for p in flat] == [PivotKind.LOW, PivotKind.HIGH]


def test_tv_piv_06_first_left_bars_never_pivots() -> None:
    """Bars 0 and 1 (L=2) cannot be pivots even if extreme."""
    rows = [
        ("200", "50", "100"),
        ("190", "60", "100"),
        ("100", "90", "95"),
        ("100", "91", "95"),
        ("100", "92", "95"),
    ]
    assert all(p.index >= 2 for p in detect_pivots(bars_hlc(rows), 2, 2))


def _pt(kind: PivotKind, price: str) -> SwingPoint:
    t = datetime(2026, 11, 18, tzinfo=UTC)
    return SwingPoint(kind, 0, Decimal(price), t, 0, t)


def test_tv_str_08_equal_tolerance_boundaries() -> None:
    """TRD-02 §4 at +-0.10% (eq = 0.001) around a previous pivot at 100."""
    eq = Decimal("0.001")
    cases_high = [
        ("100.1001", SwingLabel.HH),
        ("100.1", SwingLabel.EQH),  # exactly +0.10% is not strictly greater
        ("99.9", SwingLabel.EQH),  # exactly -0.10% is not strictly lower
        ("99.8999", SwingLabel.LH),
    ]
    for price, expected in cases_high:
        out = label_pivots([_pt(PivotKind.HIGH, "100"), _pt(PivotKind.HIGH, price)], eq)
        assert [p.label for p in out] == [SwingLabel.NONE, expected], price
    cases_low = [
        ("100.1001", SwingLabel.HL),
        ("100.1", SwingLabel.EQL),
        ("99.9", SwingLabel.EQL),
        ("99.8999", SwingLabel.LL),
    ]
    for price, expected in cases_low:
        out = label_pivots([_pt(PivotKind.LOW, "100"), _pt(PivotKind.LOW, price)], eq)
        assert out[1].label is expected, price


def test_labels_compare_same_kind_only() -> None:
    """A low between two highs does not change which pivot the second high is compared to."""
    pts = [_pt(PivotKind.HIGH, "100"), _pt(PivotKind.LOW, "50"), _pt(PivotKind.HIGH, "101")]
    assert [p.label for p in label_pivots(pts, Decimal("0.001"))] == [
        SwingLabel.NONE,
        SwingLabel.NONE,
        SwingLabel.HH,
    ]
