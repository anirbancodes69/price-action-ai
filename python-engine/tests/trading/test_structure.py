"""TV-STR-01..07 and TV-NLA-01/02/04 for the structure machine (TRD-02 §5-§8).

Fixture (L=R=2, buffer 0.0005), rows are (high, low, close). Hand-computed pivots:
  LOW@2 97 (conf 4, NONE)   HIGH@4 108 (conf 6, NONE)
  LOW@6 100 (conf 8, HL)    HIGH@8 107 (conf 10, LH)
  HIGH@11 110 (conf 13, HH) LOW@13 96 (conf 15, LL)
"""

from __future__ import annotations

import random
from decimal import Decimal

from app.domain.pivots import detect_pivots, label_pivots
from app.domain.structure import run_structure
from app.domain.types import (
    Direction,
    EventType,
    PivotKind,
    StructureResult,
    StructureState,
    SwingLabel,
)

from ._bars import bars_hlc

BUF = Decimal("0.0005")
EQ = Decimal("0.001")

BASE = [
    ("100", "98", "99"),  # 0
    ("101", "99", "100"),  # 1
    ("102", "97", "101"),  # 2  swing low 97
    ("105", "100", "104"),  # 3
    ("108", "102", "107"),  # 4  swing high 108
    ("106", "101", "102"),  # 5
    ("104", "100", "101"),  # 6  swing low 100
    ("105", "102", "104"),  # 7
    ("107", "103", "106"),  # 8  swing high 107
    ("106", "104", "105"),  # 9
    ("107", "103", "103"),  # 10
]
BOS_BAR = ("110", "104", "109")  # 11: closes above 107 x 1.0005 = 107.0535 (and above 108 x 1.0005)
TAIL = [
    ("105", "98", "99"),  # 12 close < 100 x 0.9995 = 99.95 -> bearish CHoCH
    ("103", "96", "100"),  # 13 swing low 96
    ("102", "99", "101"),  # 14
    ("103", "100", "102"),  # 15
    ("99", "94", "95"),  # 16 close < 96 x 0.9995 = 95.952 -> bearish BOS
]


def run(rows: list[tuple[str, str, str]]) -> StructureResult:
    bars = bars_hlc(rows)
    pivots = label_pivots(detect_pivots(bars, 2, 2), EQ)
    return run_structure(bars, pivots, BUF)


def test_fixture_pivots_and_labels() -> None:
    bars = bars_hlc([*BASE, BOS_BAR, *TAIL])
    got = [
        (p.kind, p.index, str(p.price), p.confirmed_at_index, p.label)
        for p in label_pivots(detect_pivots(bars, 2, 2), EQ)
    ]
    K, H, L = PivotKind, SwingLabel, None  # noqa: F841
    assert got == [
        (K.LOW, 2, "97", 4, H.NONE),
        (K.HIGH, 4, "108", 6, H.NONE),
        (K.LOW, 6, "100", 8, H.HL),
        (K.HIGH, 8, "107", 10, H.LH),
        (K.HIGH, 11, "110", 13, H.HH),
        (K.LOW, 13, "96", 15, H.LL),
    ]


def test_tv_str_01_bullish_bos_and_state() -> None:
    r = run([*BASE, BOS_BAR])
    assert all(s.state is StructureState.SIDEWAYS for s in r.states[:11])
    assert r.states[11].state is StructureState.BULLISH
    assert r.states[11].protected_low is not None and r.states[11].protected_low.index == 6
    assert len(r.events) == 1
    e = r.events[0]
    assert (e.type, e.direction, e.level, e.level_pivot_index, e.break_index) == (
        EventType.BOS,
        Direction.UP,
        Decimal("107"),
        8,
        11,
    )


def test_tv_str_02_close_exactly_at_buffer_is_not_a_break() -> None:
    r = run([*BASE, ("110", "104", "107.0535")])
    assert r.states[11].state is StructureState.SIDEWAYS
    [e] = r.events
    assert (e.type, e.level_pivot_index, e.close_inside_buffer) == (EventType.WICK_BREACH, 8, True)
    # one tick above the buffer is a break
    assert run([*BASE, ("110", "104", "107.0536")]).states[11].state is StructureState.BULLISH


def test_tv_str_03_wick_above_close_below_level() -> None:
    r = run([*BASE, ("110", "104", "106")])
    assert r.states[11].state is StructureState.SIDEWAYS
    [e] = r.events
    assert (e.type, e.close_inside_buffer) == (EventType.WICK_BREACH, False)


def test_tv_str_04_pivot_cannot_be_broken_on_its_confirmation_bar() -> None:
    """HIGH@8 is confirmed at bar 10. A close above it needs a high above it, which would have
    prevented the pivot, so the same-bar case cannot arise for the confirming pivot itself. What is
    testable: bar 10 never produces an event, and the first possible break is bar 11."""
    r = run([*BASE, BOS_BAR])
    assert all(e.break_index >= 11 for e in r.events)
    assert r.states[10].state is StructureState.SIDEWAYS


def test_tv_str_05_bearish_choch() -> None:
    r = run([*BASE, BOS_BAR, TAIL[0]])
    assert r.states[12].state is StructureState.TRANSITION
    assert r.states[12].transition_direction is Direction.DOWN
    assert r.states[12].protected_high is not None and r.states[12].protected_high.index == 8
    e = r.events[-1]
    assert (e.type, e.direction, e.level, e.level_pivot_index, e.break_index) == (
        EventType.CHOCH,
        Direction.DOWN,
        Decimal("100"),
        6,
        12,
    )


def test_tv_str_06_transition_then_bearish_bos() -> None:
    r = run([*BASE, BOS_BAR, *TAIL])
    assert [s.state for s in r.states[12:16]] == [StructureState.TRANSITION] * 4
    assert r.states[16].state is StructureState.BEARISH
    assert r.states[16].protected_high is not None and r.states[16].protected_high.index == 11
    assert [(e.type, e.direction, e.break_index) for e in r.events] == [
        (EventType.BOS, Direction.UP, 11),
        (EventType.CHOCH, Direction.DOWN, 12),
        (EventType.BOS, Direction.DOWN, 16),
    ]


def test_bos_down_needs_a_new_pivot_after_choch() -> None:
    """A close under the old low right after the CHoCH is not a BOS (TRD-02 §7)."""
    rows = [*BASE, BOS_BAR, TAIL[0], ("100", "90", "92")]  # bar 13 also far below everything
    r = run(rows)
    assert r.states[13].state is StructureState.TRANSITION
    assert [e.type for e in r.events] == [EventType.BOS, EventType.CHOCH]


def test_tv_str_07_one_bar_breaking_two_swing_highs_emits_one_bos() -> None:
    """Bar 11 closes above HIGH@8 (107) and HIGH@4 (108): one BOS, the older one is broken silently."""
    r = run([*BASE, BOS_BAR])
    assert [e.type for e in r.events] == [EventType.BOS]
    # the older high is not re-used for another break later
    r2 = run([*BASE, BOS_BAR, ("112", "108", "111")])
    assert [e.type for e in r2.events] == [EventType.BOS]


def test_sideways_without_higher_low_does_not_turn_bullish() -> None:
    """§5.3: last low labelled LL blocks SIDEWAYS -> BULLISH. Lower LOW@6 (96 < 97) -> LL."""
    rows = list(BASE)
    rows[6] = ("104", "96", "101")
    r = run([*rows, BOS_BAR])
    assert r.states[11].state is StructureState.SIDEWAYS


def _random_rows(seed: int, n: int) -> list[tuple[str, str, str]]:
    rng = random.Random(seed)  # noqa: S311 - test data
    price = Decimal("100")
    rows = []
    for _ in range(n):
        price = max(Decimal("10"), price + Decimal(rng.randint(-150, 150)) / 100)
        hi = price + Decimal(rng.randint(0, 80)) / 100
        lo = price - Decimal(rng.randint(0, 80)) / 100
        rows.append((str(hi), str(lo), str(price)))
    return rows


def _prefix(r: StructureResult, t: int) -> tuple[object, ...]:
    return (
        r.states[: t + 1],
        tuple(e for e in r.events if e.break_index <= t),
        tuple(p for p in r.pivots if p.confirmed_at_index <= t),
    )


def test_tv_nla_01_truncation_invariance() -> None:
    for seed in range(5):
        rows = _random_rows(seed, 120)
        full = run(rows)
        assert full.events, "fixture should exercise the machine"
        for t in range(4, len(rows), 7):
            assert _prefix(run(rows[: t + 1]), t) == _prefix(full, t)


def test_tv_nla_02_future_perturbation() -> None:
    rows = _random_rows(11, 120)
    base = run(rows)
    rng = random.Random(3)  # noqa: S311 - test data
    for t in (30, 61, 90):
        mutated = rows[: t + 1] + [
            (str(Decimal(150) + rng.randint(0, 50)), str(Decimal(20) + rng.randint(0, 10)), "60")
            for _ in range(len(rows) - t - 1)
        ]
        assert _prefix(run(mutated), t) == _prefix(base, t)


def test_tv_nla_04_determinism() -> None:
    rows = _random_rows(7, 150)
    assert run(rows) == run(rows)
