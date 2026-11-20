"""The zone cache is a pure speed-up: it never changes a result, and never serves a different input.

The property it relies on: zones at bar `t` depend only on bars up to `t` and pivots confirmed by `t`, so they are
the same whether computed on the series as it was at `t` or on the longer series of a later analysis.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.params import RulesetParams
from app.domain.pivots import detect_pivots
from app.domain.types import Bar
from app.domain.zone_build import build_zones
from app.domain.zone_cache import ZoneCache
from app.rulesets import load_ruleset

D = Decimal
BASE = load_ruleset("pa-intraday", "0.1.0")
OPEN = datetime(2026, 11, 18, 3, 45, tzinfo=UTC)
TICK = D("0.05")


def _walk(n: int, seed: int) -> list[Bar]:
    rnd = random.Random(seed)  # noqa: S311 - a seeded fixture, not security
    price = D("1000")
    out: list[Bar] = []
    for i in range(n):
        o = price
        c = (o + D(rnd.randint(-40, 40)) / 10).quantize(TICK)
        h = max(o, c) + D(rnd.randint(0, 15)) / 10
        lo = min(o, c) - D(rnd.randint(0, 15)) / 10
        s = OPEN + timedelta(minutes=5 * i)
        out.append(Bar(s, s + timedelta(minutes=5), o, h, lo, c))
        price = c
    return out


def _fifteen(five: list[Bar]) -> list[Bar]:
    return [
        Bar(g[0].start, g[-1].end, g[0].open, max(b.high for b in g), min(b.low for b in g), g[-1].close)
        for g in (five[i : i + 3] for i in range(0, len(five) - 2, 3))
    ]


def _args(params: RulesetParams, bars: list[Bar]):  # type: ignore[no-untyped-def]
    p5 = detect_pivots(bars, params.pivot_left("5m"), params.pivot_right("5m"))
    p15 = detect_pivots(_fifteen(bars), params.pivot_left("15m"), params.pivot_right("15m"))
    return p5, p15


def test_zones_at_t_do_not_depend_on_later_bars() -> None:
    bars = _walk(240, seed=7)
    full5, full15 = _args(BASE, bars)
    nonempty = 0
    for t in range(40, len(bars), 7):
        prefix = bars[: t + 1]
        pre5, pre15 = _args(BASE, prefix)
        a = build_zones(prefix, pre5, pre15, t, BASE, OPEN, None, TICK)
        b = build_zones(bars, full5, full15, t, BASE, OPEN, None, TICK)
        assert a == b, f"zones at bar {t} changed with later data"
        nonempty += bool(a)
    assert nonempty > 5, "the fixture must produce zones, or the check proves nothing"


def test_cache_returns_exactly_what_build_zones_returns() -> None:
    bars = _walk(240, seed=11)
    p5, p15 = _args(BASE, bars)
    cache = ZoneCache()
    for t in list(range(40, len(bars), 5)) * 2:  # the second pass is all hits
        assert cache.zones(bars, p5, p15, t, BASE, OPEN, None, TICK) == build_zones(
            bars, p5, p15, t, BASE, OPEN, None, TICK
        )


def test_cache_never_serves_a_different_input() -> None:
    a, b = _walk(200, seed=1), _walk(200, seed=2)
    pa, qa = _args(BASE, a)
    pb, qb = _args(BASE, b)
    cache = ZoneCache()
    cache.zones(a, pa, qa, 150, BASE, OPEN, None, TICK)
    assert cache.zones(b, pb, qb, 150, BASE, OPEN, None, TICK) == build_zones(
        b, pb, qb, 150, BASE, OPEN, None, TICK
    )
    later = OPEN + timedelta(days=1)  # another session open is another input
    assert cache.zones(a, pa, qa, 150, BASE, later, OPEN, TICK) == build_zones(
        a, pa, qa, 150, BASE, later, OPEN, TICK
    )


def test_callers_cannot_alter_the_cached_list() -> None:
    bars = _walk(200, seed=3)
    p5, p15 = _args(BASE, bars)
    cache = ZoneCache()
    first = cache.zones(bars, p5, p15, 150, BASE, OPEN, None, TICK)
    first.clear()
    assert cache.zones(bars, p5, p15, 150, BASE, OPEN, None, TICK) == build_zones(
        bars, p5, p15, 150, BASE, OPEN, None, TICK
    )
