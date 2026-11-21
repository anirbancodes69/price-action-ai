"""TV-SET-19..28: LIQUIDITY_SWEEP_REVERSAL (TRD-04 §7, §8.3, §10). Every expected value is hand-computed.

Constants of the fixtures (`pa-intraday 0.2.0`): sbuf = 0.05%, bb = 0.05%, sb = 0.05%, tick unset (no rounding).
Level `Y` = PDL = 1480.0: `Y x (1 - sbuf)` = 1479.26. Sweep bar low 1478: stop base 1478, stop 1478 x 0.9995 = 1477.261.
"""

from __future__ import annotations

from app.domain.levels import trade_levels
from app.domain.setups.liquidity_sweep import detect_liquidity_sweep, liquidity_sweep_enabled
from app.domain.setups.scoring import checklist_component, level_component, score_setup
from app.domain.setups.types import Setup, SetupContext, SetupDirection, SetupStatus, SetupType
from app.domain.types import StructureState
from app.rulesets import load_ruleset

from ._session import D, ctx_for, flat_htf, mk

SWEEP = load_ruleset("pa-intraday", "0.2.0")

# Bars 0-4 drift down to 1481 without touching PDL 1480 or any other level that could be swept.
LEAD = [
    ("1490", "1492", "1488", "1491"),  # 0
    ("1491", "1493", "1489", "1490"),  # 1
    ("1490", "1491", "1487", "1488"),  # 2  opening range complete: OR low 1487
    (
        "1488",
        "1489",
        "1485",
        "1486",
    ),  # 3  close 1486 < 1487 x 0.9995 = 1486.2565: OR low is broken for later bars
    ("1486", "1487", "1481", "1482"),  # 4
]
SAME_BAR = [
    *LEAD,
    ("1482", "1483", "1478", "1481"),
    ("1481", "1486", "1480.5", "1485"),
]  # 5 sweep+reclaim, 6 confirm


def _ctx(rows: list[tuple[str, str, str, str]], **kw: object) -> SetupContext:
    kw.setdefault("pdh", "1510")
    kw.setdefault("pdl", "1480")
    kw.setdefault("params", SWEEP)
    return ctx_for(mk(rows), **kw)  # type: ignore[arg-type]


def _setups(rows: list[tuple[str, str, str, str]], **kw: object) -> list[Setup]:
    return detect_liquidity_sweep(_ctx(rows, **kw))[0]


def test_tv_set_19_disabled_in_0_1_0_and_enabled_in_0_2_0() -> None:
    from app.rulesets import load_ruleset as load

    assert not liquidity_sweep_enabled(load("pa-intraday", "0.1.0"))
    assert liquidity_sweep_enabled(SWEEP)
    # Same bars, 0.1.0: never emitted.
    assert detect_liquidity_sweep(ctx_for(mk(SAME_BAR), pdh="1510", pdl="1480")) == ([], [])


def test_tv_set_20_same_bar_sweep_reclaim_and_confirmation() -> None:
    [s] = _setups(SAME_BAR)
    # Bar 5: L 1478 < 1479.26 and C 1481 >= 1480 -> detected on bar 5; trigger = H[5] = 1483.
    assert (s.type, s.direction, s.anchor) == (SetupType.LIQUIDITY_SWEEP_REVERSAL, SetupDirection.LONG, "PDL")
    assert (s.detected_at_index, s.trigger_price, s.sweep_low, s.stop_base) == (
        5,
        D("1483"),
        D("1478"),
        D("1478"),
    )
    assert (s.swept_level, s.same_bar_reclaim) == (D("1480"), True)
    # Bar 6 closes 1485 > 1483 x 1.0005 = 1483.7415 -> confirmed.
    assert (s.status, s.confirmed_at_index, s.confirm_close) == (SetupStatus.ENTRY_CONFIRMED, 6, D("1485"))
    # The earlier opening-range low (1487) was broken on bar 3 and is not a level for bar 5.


def test_tv_set_20_awaiting_confirmation_before_the_trigger_closes() -> None:
    [s] = _setups(SAME_BAR[:6])
    assert (s.status, s.detected_at_index, s.confirmed_at_index) == (
        SetupStatus.AWAITING_CONFIRMATION,
        5,
        None,
    )


def test_tv_set_21_two_bar_reclaim() -> None:
    rows = [*LEAD, ("1482", "1483", "1478", "1479.5"), ("1479.5", "1484", "1478.2", "1481")]
    # Bar 5: L 1478 < 1479.26; C 1479.5 < 1480 but >= 1479.26 (no structural break).
    # Bar 6: C 1481 >= 1480 and L 1478.2 >= 1478 x 0.9995 = 1477.261 -> reclaim on bar 6.
    [s] = _setups(rows)
    assert (s.detected_at_index, s.trigger_price, s.sweep_low, s.same_bar_reclaim) == (
        6,
        D("1484"),
        D("1478"),
        False,
    )
    assert s.status is SetupStatus.AWAITING_CONFIRMATION


def test_tv_set_22_no_sweep_without_a_timely_reclaim_or_after_a_new_low() -> None:
    no_reclaim = [
        *LEAD,
        ("1482", "1483", "1478", "1479.5"),
        ("1479.5", "1481", "1478.2", "1479"),
    ]  # C[6] 1479 < 1480
    assert _setups(no_reclaim) == []
    # A deeper low on the reclaim bar is not a two-bar sweep (L[6] 1477 < 1478 x 0.9995 = 1477.261) but bar 6 is
    # itself a same-bar sweep and reclaim of the still-unbroken level (C[5] 1479.5 >= 1479.26): a new setup.
    deeper = [*LEAD, ("1482", "1483", "1478", "1479.5"), ("1479.5", "1484", "1477", "1481")]
    [s6] = _setups(deeper)
    assert (s6.detected_at_index, s6.sweep_low, s6.same_bar_reclaim) == (6, D("1477"), True)
    broken = [
        *LEAD,
        ("1482", "1483", "1478", "1479.2"),
        ("1479.2", "1484", "1478.2", "1481"),
    ]  # C[5] 1479.2 < 1479.26
    assert _setups(broken) == []  # a close beyond the buffer is a structural break, not a sweep


def test_tv_set_23_sweep_depth_boundary() -> None:
    at = [*LEAD, ("1482", "1483", "1479.26", "1481")]  # L = 1479.26: not below Y x (1 - sbuf)
    below = [*LEAD, ("1482", "1483", "1479.25", "1481")]  # L = 1479.25 < 1479.26
    assert _setups(at) == []
    [s] = _setups(below)
    assert (s.detected_at_index, s.sweep_low) == (5, D("1479.25"))


def test_tv_set_24_sweep_failed_when_a_close_goes_below_the_sweep_low() -> None:
    rows = [*SAME_BAR[:6], ("1481", "1481", "1470", "1476")]  # C 1476 < sweep_low 1478
    [s] = _setups(rows)
    assert (s.status, s.end_reason, s.ended_at_index) == (SetupStatus.INVALIDATED, "SWEEP_FAILED", 6)


def test_tv_set_25_bearish_15m_context_does_not_block_the_sweep_but_scores_zero() -> None:
    bearish = flat_htf(len(SAME_BAR), StructureState.BEARISH)
    ctx = _ctx(SAME_BAR, htf=bearish)
    [s] = detect_liquidity_sweep(ctx)[0]
    assert s.status is SetupStatus.ENTRY_CONFIRMED  # SD-05 exception
    levels = trade_levels(s, ctx, [])
    paqs = score_setup(s, ctx, [], levels)
    assert paqs is not None
    parts = {c.name: c for c in paqs.components}
    assert parts["structure_alignment"].points == 0  # 15m against
    assert (parts["key_level_quality"].points, parts["key_level_quality"].missing) == (0, True)  # OQ-SD-07
    # setup quality 25 + entry confirmation 20 (close 1485 >= bar mid 1483.25) + risk/reward 10 (rr 3.23 >= 3.0)
    assert (parts["setup_quality"].points, parts["entry_confirmation"].points) == (25, 20)
    assert (parts["risk_reward"].points, paqs.total) == (10, 55)


def test_tv_set_26_levels_stop_and_target_ladder() -> None:
    ctx = _ctx(SAME_BAR)
    [s] = detect_liquidity_sweep(ctx)[0]
    lv = trade_levels(s, ctx, [])
    assert lv is not None
    # stop 1478 x 0.9995 = 1477.261; entry 1485; risk 7.739. SESSION_HIGH/OR_HIGH 1493 give rr 1.03 < 2,
    # PDH 1510 gives (1510 - 1485) / 7.739 = 3.23.
    assert (lv.entry, lv.stop, lv.target, lv.target_source) == (D("1485"), D("1477.261"), D("1510"), "PDH")
    assert lv.rr is not None and round(lv.rr, 2) == D("3.23") and not lv.rr_below_min


# Two equal highs (1530.0 on bar 2, 1530.2 on bar 7) form an EQUAL_HIGHS pool at 1530.2 (confirmed on bar 9).
POOL_DAY = [
    ("1505", "1508", "1503", "1506"),  # 0
    ("1506", "1509", "1504", "1507"),  # 1
    ("1507", "1530", "1506", "1512"),  # 2  pivot high 1530
    ("1512", "1514", "1505", "1506"),  # 3
    ("1506", "1510", "1500", "1502"),  # 4
    ("1502", "1505", "1496", "1498"),  # 5
    ("1498", "1503", "1494", "1495"),  # 6
    ("1495", "1530.2", "1492", "1500"),  # 7  pivot high 1530.2
    ("1500", "1502", "1490", "1492"),  # 8
    ("1492", "1496", "1488", "1494"),  # 9
    ("1494", "1495", "1484", "1488"),  # 10 sweep of PDL 1485: L 1484 < 1484.2575, C 1488 >= 1485
    ("1488", "1500", "1486", "1498"),  # 11 C 1498 > 1495 x 1.0005 = 1495.7475: confirmed
]


def test_tv_set_27_equal_highs_pool_is_the_first_target_candidate() -> None:
    ctx = _ctx(POOL_DAY, pdh="1528", pdl="1485")
    [s] = detect_liquidity_sweep(ctx)[0]
    assert (s.anchor, s.detected_at_index, s.status, s.confirm_close) == (
        "PDL",
        10,
        SetupStatus.ENTRY_CONFIRMED,
        D("1498"),
    )
    lv = trade_levels(s, ctx, [])
    assert lv is not None
    # stop 1484 x 0.9995 = 1483.258, risk 14.742. EQUAL_HIGHS 1530.2: reward 32.2 -> rr 2.18 >= 2.
    # The ladder's own PDH (1528) would also pass (rr 2.03) and is nearer, but the setup-specific candidate comes first.
    assert (lv.stop, lv.target, lv.target_source) == (D("1483.258"), D("1530.2"), "EQUAL_HIGHS")
    assert lv.rr is not None and round(lv.rr, 2) == D("2.18")


def test_tv_set_28_checklist_points() -> None:
    def setup(anchor: str, y: str, low: str, same_bar: bool) -> Setup:
        return Setup(
            SetupType.LIQUIDITY_SWEEP_REVERSAL,
            SetupDirection.LONG,
            SetupStatus.AWAITING_CONFIRMATION,
            5,
            D("1483"),
            anchor,
            stop_base=D(low),
            swept_level=D(y),
            sweep_low=D(low),
            same_bar_reclaim=same_bar,
        )

    ctx = _ctx(SAME_BAR)
    # same-bar (9) + PDL anchor (8) + depth (1480 - 1475.56) / 1480 = 0.30% <= 0.30 (8)
    assert checklist_component(setup("PDL", "1480", "1475.56", True), ctx).points == 25
    # depth (1480 - 1475.55) / 1480 = 0.3007% > 0.30: 17
    assert checklist_component(setup("PDL", "1480", "1475.55", True), ctx).points == 17
    # two-bar reclaim loses the 9; a 5m swing-low anchor is not in the listed anchors (no 8)
    assert checklist_component(setup("SWING_LOW_5M", "1480", "1478", False), ctx).points == 8
    # a non-zone anchor has no key-level points defined (OQ-SD-07): scored 0 and flagged missing
    comp = level_component(setup("EQUAL_LOWS", "1480", "1478", True), ctx, [])
    assert (comp.points, comp.missing) == (0, True)


def test_the_sweep_is_not_emitted_after_the_entry_cutoff() -> None:
    # cutoff 350 minutes before the close = 09:40 IST; bar 5 ends 09:45 > cutoff (SD-08)
    assert _setups(SAME_BAR, cutoff_minutes=350) == []


def test_no_look_ahead_a_setup_detected_on_bar_k_is_the_same_on_truncated_data() -> None:
    """PE-03/MP-04: running on the series cut at bar k gives the setups detected on or before k, unchanged."""
    for rows, kw in ((SAME_BAR, {}), (POOL_DAY, {"pdh": "1528", "pdl": "1485"})):
        full = _setups(rows, **kw)
        for k in range(5, len(rows)):
            cut = _setups(rows[: k + 1], **kw)
            want = {
                (s.detected_at_index, s.anchor, s.trigger_price, s.stop_base)
                for s in full
                if s.detected_at_index <= k
            }
            got = {(s.detected_at_index, s.anchor, s.trigger_price, s.stop_base) for s in cut}
            assert got == want, (len(rows), k)
