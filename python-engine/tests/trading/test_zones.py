"""TV-ZON-01..10 (TRD-03 §3-§7). Expected values are hand-computed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.liquidity import PoolType, equal_levels
from app.domain.types import Direction, PivotKind, SwingPoint
from app.domain.zone_break import evaluate_break
from app.domain.zone_build import build_zones, distance_pct, is_near, nearest, zone_role
from app.domain.zone_strength import TouchStats, strength_score, touch_stats
from app.domain.zones import StrengthBucket, Zone, ZoneMember, ZoneRole, ZoneStatus, cluster_pivots
from app.rulesets import load_ruleset

from ._bars import bars_from

D = Decimal
T0 = datetime(2026, 11, 18, 3, 45, tzinfo=UTC)
TOL, MINW = D("0.0015"), D("0.0005")
BUF = D("0.0005")


def pt(kind: PivotKind, price: str, index: int = 0, conf: int | None = None) -> SwingPoint:
    start = T0 + timedelta(minutes=5 * index)
    c = index + 2 if conf is None else conf
    return SwingPoint(kind, index, D(price), start, c, T0 + timedelta(minutes=5 * (c + 1)))


def member(price: str, index: int = 0, tf: str = "5m", kind: PivotKind = PivotKind.HIGH) -> ZoneMember:
    p = pt(kind, price, index)
    return ZoneMember(tf, p, index, p.confirmed_at_index)  # type: ignore[arg-type]


def test_tv_zon_01_clustering_example() -> None:
    ms = [member(x, i) for i, x in enumerate(["1480.0", "1481.2", "1482.0", "1490.0"])]
    a, b = cluster_pivots(ms, TOL, MINW)
    assert (a.low, a.high, len(a.members)) == (D("1480.0"), D("1482.0"), 3)
    assert len(b.members) == 1
    assert (b.low, b.high) == (D("1489.6275"), D("1490.3725"))  # TRD-03 example: [1489.63, 1490.37]


def test_tv_zon_02_single_pivot_width_is_min_width() -> None:
    [c] = cluster_pivots([member("1490")], TOL, MINW)
    assert (c.high - c.low) / ((c.high + c.low) / 2) == MINW


def test_cluster_anchored_at_low_not_chained() -> None:
    """1000, 1001.4, 1002.8: each step is within 0.15% of the previous, but 1002.8 > 1000 x 1.0015."""
    ms = [member(x, i) for i, x in enumerate(["1000", "1001.4", "1002.8"])]
    assert [len(c.members) for c in cluster_pivots(ms, TOL, MINW)] == [2, 1]


def test_tick_rounding_and_two_tick_minimum() -> None:
    [c] = cluster_pivots([member("1490")], TOL, MINW, tick=D("0.05"))
    assert (c.low, c.high) == (D("1489.60"), D("1490.40"))
    [c] = cluster_pivots([member("100")], TOL, D("0"), tick=D("0.05"))  # width 0 -> 2 ticks
    assert (c.low, c.high) == (D("99.95"), D("100.05"))


def test_overlapping_zones_merge() -> None:
    ms = [member("100.00", 0), member("100.20", 1)]  # 0.2% apart: separate clusters
    assert len(cluster_pivots(ms, TOL, D("0"))) == 2
    [c] = cluster_pivots(ms, TOL, D("0.005"))  # widened to 0.5% each -> overlap -> merged
    assert (c.low, c.high, len(c.members)) == (D("99.75"), D("100.4505"), 2)


ZLOW, ZHIGH = D("100"), D("101")


def closes(*cs: str) -> list:
    return bars_from([(c, str(D(c) + D("0.01")), str(D(c) - D("0.01")), c) for c in ("100.5", *cs)])


def test_tv_zon_03_close_inside_buffer_is_not_a_break() -> None:
    out = evaluate_break(closes("99.96", "100.5"), ZLOW, ZHIGH, 0, 2, 1, BUF)  # 99.95 is the level
    assert out.status is ZoneStatus.ACTIVE
    assert (
        evaluate_break(closes("99.95"), ZLOW, ZHIGH, 0, 1, 1, BUF).status is ZoneStatus.ACTIVE
    )  # exactly at level


def test_tv_zon_04_close_beyond_buffer_breaks_and_flips() -> None:
    out = evaluate_break(closes("99.94"), ZLOW, ZHIGH, 0, 1, 1, BUF)
    assert (out.status, out.broken_direction, out.broken_at_index) == (
        ZoneStatus.BROKEN_FLIPPED,
        Direction.DOWN,
        1,
    )
    up = evaluate_break(closes("101.06"), ZLOW, ZHIGH, 0, 1, 1, BUF)  # level 101.0505
    assert (up.status, up.broken_direction) == (ZoneStatus.BROKEN_FLIPPED, Direction.UP)


def test_tv_zon_05_flipped_zone_broken_again_is_retired() -> None:
    out = evaluate_break(closes("99.94", "101.06"), ZLOW, ZHIGH, 0, 2, 1, BUF)
    assert (out.status, out.broken_at_index, out.retired_at_index) == (ZoneStatus.RETIRED, 1, 2)
    # a further close in the same direction does not retire it
    assert (
        evaluate_break(closes("99.94", "99.90"), ZLOW, ZHIGH, 0, 2, 1, BUF).status
        is ZoneStatus.BROKEN_FLIPPED
    )


def test_two_close_confirmation() -> None:
    assert (
        evaluate_break(closes("99.9", "100.5", "99.9"), ZLOW, ZHIGH, 0, 3, 2, BUF).status is ZoneStatus.ACTIVE
    )
    out = evaluate_break(closes("99.9", "99.8"), ZLOW, ZHIGH, 0, 2, 2, BUF)
    assert (out.status, out.broken_at_index) == (ZoneStatus.BROKEN_FLIPPED, 2)  # at the last confirming close


# Touch fixture: zone [100, 101], one LOW member pivot at bar 0.
TOUCH_BARS = bars_from(
    [
        ("101", "103", "100", "102"),  # 0 pivot bar
        ("102", "104", "101.5", "103"),  # 1 above the zone
        ("103", "103", "100.5", "100.8"),  # 2 enters from above
        ("100.8", "101.5", "100.2", "101.2"),  # 3 still intersecting
        ("101.2", "102.5", "101.2", "102.4"),  # 4 closes above: reaction
        ("102.4", "103.5", "102", "103"),  # 5
        ("103", "103", "102", "102.5"),  # 6
        ("102.5", "102.5", "100.5", "100.7"),  # 7 enters from above again
        ("100.7", "101", "100.1", "100.2"),  # 8 no reaction yet
    ]
)


def test_touches_member_plus_confirmed_reaction() -> None:
    m = [member("100", 0, kind=PivotKind.LOW)]
    s = touch_stats(TOUCH_BARS, m, ZLOW, ZHIGH, 0, 6, 2)
    assert s.touches == 2  # the member plus the bars-2..3 touch
    assert s.last_touch_start == TOUCH_BARS[3].start
    # member reaction: max high 104 in bars 1..6 -> (104 - 101) / 100.5 x 100 = 2.9851 %
    assert s.max_reaction_pct.quantize(D("0.0001")) == D("2.9851")


def test_touch_without_reaction_is_not_counted() -> None:
    m = [member("100", 0, kind=PivotKind.LOW)]
    assert touch_stats(TOUCH_BARS, m, ZLOW, ZHIGH, 0, 8, 2).touches == 2  # bars 7..8 have no reaction


def test_tv_zon_06_strength_components() -> None:
    cur, prev = T0, T0 - timedelta(days=1)
    s = TouchStats(3, D("1.5"), T0)
    assert strength_score(s, cur, prev, True, True) == (95, StrengthBucket.STRONG)  # 45+15+20+5+10
    s = TouchStats(6, D("3.0"), T0 - timedelta(hours=20))
    assert strength_score(s, cur, prev, False, False) == (90, StrengthBucket.STRONG)  # 60+20+10
    assert strength_score(TouchStats(4, D("5"), T0), cur, prev, True, True)[0] == 100  # capped


def test_strength_bucket_boundaries() -> None:
    cur, prev = T0, T0 - timedelta(days=1)
    old = T0 - timedelta(days=3)
    assert strength_score(TouchStats(2, D("0.9"), old), cur, prev, False, False) == (39, StrengthBucket.WEAK)
    assert strength_score(TouchStats(2, D("1.0"), old), cur, prev, False, False) == (
        40,
        StrengthBucket.MODERATE,
    )
    assert strength_score(TouchStats(4, D("0.9"), old), cur, prev, False, False) == (
        69,
        StrengthBucket.MODERATE,
    )
    assert strength_score(TouchStats(4, D("1.0"), old), cur, prev, False, False) == (
        70,
        StrengthBucket.STRONG,
    )


def test_tv_zon_10_recency_points() -> None:
    cur, prev = T0, T0 - timedelta(days=1)
    base = (0, D(0))
    for last, pts in ((T0, 20), (prev + timedelta(hours=1), 10), (prev - timedelta(hours=1), 0)):
        score, _ = strength_score(TouchStats(base[0], base[1], last), cur, prev, False, False)
        assert score == pts


def test_tv_zon_09_15m_pivot_member_only_from_its_confirmation() -> None:
    p = load_ruleset("pa-intraday", "0.1.0")
    bars = bars_from([("100", "100.2", "99.9", "100")] * 8)
    piv = SwingPoint(PivotKind.LOW, 0, D("99.9"), bars[0].start, 2, bars[5].end)  # confirmed at end of bar 5
    kw = {"current_session_open": bars[0].start, "previous_session_open": None}
    assert build_zones(bars, [], [piv], 4, p, **kw) == []  # type: ignore[arg-type]
    for t in (5, 6):
        [z] = build_zones(bars, [], [piv], t, p, **kw)  # type: ignore[arg-type]
        assert (z.members[0].timeframe, z.members[0].known_index_5m, z.formed_at_index) == ("15m", 5, 5)
        assert z.has_htf_member


def test_tv_zon_08_proximity() -> None:
    z = Zone(ZLOW, ZHIGH, (), 0)
    p = load_ruleset("pa-intraday", "0.1.0")
    assert zone_role(z, D("102")) is ZoneRole.SUPPORT
    assert distance_pct(z, D("102")).quantize(D("0.0001")) == D("0.9804")  # 1 / 102 x 100
    assert zone_role(z, D("99")) is ZoneRole.RESISTANCE
    assert distance_pct(z, D("99")).quantize(D("0.0001")) == D("1.0101")  # 1 / 99 x 100
    assert (zone_role(z, D("100.5")), distance_pct(z, D("100.5"))) == (ZoneRole.INSIDE, D(0))
    assert not is_near(z, D("102"), p)  # 0.98 % > 0.50 %
    assert is_near(z, D("101.4"), p)  # 0.3945 %
    other = Zone(D("95"), D("96"), (), 0)
    assert nearest([other, z], D("102"), ZoneRole.SUPPORT) is z
    assert nearest([z], D("102"), ZoneRole.RESISTANCE) is None


def _pool_bars(close_at_4: str = "101") -> list:
    return bars_from(
        [(c, c, c, c) for c in ("101", "101", "100", "101", close_at_4, "101", "100.05", "101", "101")]
    )


def test_equal_lows_pool_and_tv_zon_07() -> None:
    a, b = pt(PivotKind.LOW, "100.0", 2), pt(PivotKind.LOW, "100.05", 6)
    [pool] = equal_levels(_pool_bars(), [a, b], 8, D("0.001"))
    assert (pool.type, pool.level, pool.first_index, pool.second_index) == (
        PoolType.EQUAL_LOWS,
        D("100.0"),
        2,
        6,
    )
    assert pool.confirmed_at_index == 8
    # TV-ZON-07: a close below the level in between: not a pool
    assert equal_levels(_pool_bars("99.9"), [a, b], 8, D("0.001")) == []
    # not yet confirmed at t = 7
    assert equal_levels(_pool_bars(), [a, b], 7, D("0.001")) == []


def test_equal_highs_tolerance_boundary_and_gap() -> None:
    bars = bars_from([(c, c, c, c) for c in ("99",) * 9])
    a = pt(PivotKind.HIGH, "100", 2)
    assert equal_levels(bars, [a, pt(PivotKind.HIGH, "100.1", 6)], 8, D("0.001"))[0].level == D(
        "100.1"
    )  # <= tol
    assert equal_levels(bars, [a, pt(PivotKind.HIGH, "100.11", 6)], 8, D("0.001")) == []
    assert equal_levels(bars, [a, pt(PivotKind.HIGH, "100", 4)], 8, D("0.001")) == []  # 2 bars apart < 3


def test_approach_side_restricts_first_break_direction() -> None:
    """A resistance zone (price below it) is not 'broken' by closes below it; only an upward break counts."""
    down = closes("99.94")
    assert evaluate_break(down, ZLOW, ZHIGH, 0, 1, 1, BUF, Direction.UP).status is ZoneStatus.ACTIVE
    assert evaluate_break(down, ZLOW, ZHIGH, 0, 1, 1, BUF, Direction.DOWN).status is ZoneStatus.BROKEN_FLIPPED
    up = evaluate_break(closes("99.9", "101.06"), ZLOW, ZHIGH, 0, 2, 1, BUF, Direction.UP)
    assert (up.status, up.broken_direction, up.broken_at_index) == (
        ZoneStatus.BROKEN_FLIPPED,
        Direction.UP,
        2,
    )
