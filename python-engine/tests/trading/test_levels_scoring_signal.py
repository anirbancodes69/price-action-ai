"""TV-SET-08/09/11/12/18, PAQS tables, signal mapping and analyse integration (TRD-04 §8, §10, §12)."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from app.domain.analyse import analyse
from app.domain.levels import pick_target, round_down, stop_price, trade_levels
from app.domain.params import RulesetParams
from app.domain.serialise import analysis_hash
from app.domain.session import DailyLevels
from app.domain.setups.opening_range import detect_opening_range
from app.domain.setups.scoring import (
    Paqs,
    checklist_component,
    entry_points,
    level_component,
    rr_points,
    score_setup,
    structure_points,
)
from app.domain.setups.signal import ScoredSetup, Signal, choose_signal
from app.domain.setups.types import Setup, SetupDirection, SetupStatus, SetupType
from app.domain.snapshot import SnapshotStatus
from app.domain.types import Direction, StructureState
from app.domain.zones import Zone
from app.rulesets import load_ruleset

from ._session import CLOSE, OPEN, PARAMS, ctx_for, flat_htf, mk
from .test_setups_session import ORB_DAY

D = Decimal
TICK = D("0.05")


def test_stop_and_rounding() -> None:
    assert stop_price(D("1486"), D("0.0005"), TICK) == D("1485.25")  # 1485.257 rounded down (TRD-04 §3)
    assert round_down(D("1529.04"), TICK) == D("1529.00")
    assert round_down(D("10.123"), None) == D("10.123")


def test_tv_set_08_ladder_skips_measured_move_that_fails_rr() -> None:
    cands = [("MEASURED_OPENING_RANGE", D("1507.00")), ("ZONE", D("1529.00"))]
    target, source, rr, below = pick_target(D("1498.10"), D("1485.25"), cands, D("2"), TICK)
    assert (target, source, below) == (D("1529.00"), "ZONE", False)
    assert rr is not None and rr.quantize(D("0.01")) == D("2.40")  # 30.90 / 12.85


def test_tv_set_09_no_candidate_meets_rr_flags_nearest() -> None:
    cands = [("ZONE", D("1510.00")), ("MEASURED_OPENING_RANGE", D("1507.00"))]
    target, source, rr, below = pick_target(D("1498.10"), D("1485.25"), cands, D("2"), TICK)
    assert (target, source, below) == (D("1507.00"), "MEASURED_OPENING_RANGE", True)
    assert rr is not None and rr.quantize(D("0.01")) == D("0.69")  # 8.90 / 12.85
    assert pick_target(D("1498.10"), D("1485.25"), [], D("2"), TICK) == (None, None, None, True)


def test_candidates_within_one_tick_of_entry_are_skipped() -> None:
    entry, stop = D("100"), D("99")
    assert pick_target(entry, stop, [("A", D("100.04"))], D("2"), TICK)[0] is None
    assert pick_target(entry, stop, [("A", D("100.05"))], D("2"), TICK)[0] == D("100.05")


def _orb_long(rows=ORB_DAY, pdh: str | None = None):  # type: ignore[no-untyped-def]
    ctx = ctx_for(mk(rows), pdh=pdh, pdl="1400" if pdh else None)
    long = next(s for s in detect_opening_range(ctx)[0] if s.direction is SetupDirection.LONG)
    return ctx, long


def test_trade_levels_orb_example_is_below_min_rr_without_overhead_structure() -> None:
    ctx, long = _orb_long()
    lv = trade_levels(long, ctx, [])
    assert lv is not None
    assert (lv.entry, lv.stop) == (D("1498.10"), D("1486.0") * D("0.9995"))  # ctx has no tick: unrounded
    # the nearest usable candidate is SESSION_HIGH 1498.5 (the confirmation bar's high), rr far below 2
    assert (lv.target, lv.target_source, lv.rr_below_min) == (D("1498.5"), "SESSION_HIGH", True)


def test_trade_levels_with_pdh_target() -> None:
    ctx, long = _orb_long(pdh="1530")
    lv = trade_levels(long, ctx, [])
    assert lv is not None and (lv.target, lv.target_source, lv.rr_below_min) == (D("1530"), "PDH", False)


def test_trade_levels_none_for_informational() -> None:
    ctx = ctx_for(mk(ORB_DAY), htf=flat_htf(7, StructureState.SIDEWAYS))
    short = next(s for s in detect_opening_range(ctx)[0] if s.direction is SetupDirection.SHORT)
    assert trade_levels(short, ctx, []) is None
    assert score_setup(short, ctx, [], None) is None


def test_structure_points_table() -> None:
    B, S, T, X = (
        StructureState.BULLISH,
        StructureState.SIDEWAYS,
        StructureState.TRANSITION,
        StructureState.BEARISH,
    )
    assert structure_points(B, None, B) == 25
    assert structure_points(B, None, S) == 18
    assert structure_points(S, None, B) == 15
    assert structure_points(T, Direction.UP, B) == 15
    assert structure_points(S, None, S) == 8
    assert structure_points(T, Direction.UP, S) == 8
    assert structure_points(X, None, B) == 0
    assert structure_points(T, Direction.DOWN, B) == 0
    assert structure_points(None, None, B) == 0


def test_rr_points_boundaries() -> None:
    m = D("2")
    got = [rr_points(D(x), m) for x in ("3.0", "2.99", "2.5", "2.49", "2.0", "1.99")]
    assert got == [10, 8, 8, 6, 6, 0]
    assert rr_points(None, m) == 0


def test_tv_set_11_paqs_worked_example_components() -> None:
    """TRD-04 §10: 25 + 14 + 25 + 20 + 6 = 90 for the opening range breakout."""
    ctx, long = _orb_long()
    assert structure_points(StructureState.BULLISH, None, StructureState.BULLISH) == 25
    assert level_component(long, ctx, []).points == 14  # OR_HIGH anchor, no zone confluence
    assert checklist_component(long, ctx).points == 25  # width 0.71%, top 30% close, 6 bars after the open
    assert entry_points(long, ctx.bars) == 20  # confirmation close in the upper half of its range
    assert rr_points(D("2.40"), D("2")) == 6
    assert 25 + 14 + 25 + 20 + 6 == 90


def test_level_component_confluence_and_zone_anchor() -> None:
    ctx, long = _orb_long()
    zone_at_or_high = Zone(D("1496"), D("1497"), (), 0)
    assert level_component(long, ctx, [zone_at_or_high]).points == 18  # 14 + 4
    pdh = replace(long, anchor="PDH")
    ctx2, _ = _orb_long(pdh="1500")
    assert level_component(pdh, ctx2, [Zone(D("1499"), D("1501"), (), 0)]).points == 20  # 16 + 4, cap 20
    zone_setup = replace(long, anchor="ZONE", zone=replace(Zone(D("1"), D("2"), (), 0), strength=87))
    assert level_component(zone_setup, ctx, []).points == 17  # round(87 x 0.20)


def test_tv_set_12_missing_zone_component_scores_zero_without_renormalising() -> None:
    ctx, long = _orb_long(pdh="1530")
    broken = replace(long, anchor="ZONE", zone=None)
    lv = trade_levels(broken, ctx, [])
    paqs = score_setup(broken, ctx, [], lv)
    assert paqs is not None
    comp = next(c for c in paqs.components if c.name == "key_level_quality")
    assert (comp.points, comp.missing) == (0, True)
    assert paqs.total == sum(c.points for c in paqs.components)  # not re-normalised


def _scored(ctx, s: Setup, total: int, rr_ok: bool = True) -> ScoredSetup:  # type: ignore[no-untyped-def]
    from app.domain.levels import TradeLevels

    lv = TradeLevels(D("100"), D("99"), D("103"), "X", D("1"), D("3"), not rr_ok)
    return ScoredSetup(s, Paqs("t", total, ()), lv)


def test_tv_set_18_signals_and_timestamps() -> None:
    ctx, long = _orb_long(pdh="1530")  # confirmed at bar 6 = T
    assert long.confirmed_at_index == ctx.t == 6
    res = choose_signal([_scored(ctx, long, 80)], ctx)
    assert res.signal is Signal.ENTRY_CONFIRMED
    assert res.signal_at == ctx.bars[6].end
    assert res.valid_until == ctx.bars[6].end + timedelta(minutes=5)  # end of bar T+1

    watch = replace(
        long, status=SetupStatus.AWAITING_CONFIRMATION, confirmed_at_index=None, confirm_close=None
    )
    res = choose_signal([_scored(ctx, watch, 70)], ctx)
    expiry_end = ctx.bars[watch.detected_at_index].end + timedelta(minutes=5 * 12)
    assert (res.signal, res.valid_until) == (Signal.BUY_WATCH, min(expiry_end, ctx.cutoff))


def test_signal_no_trade_reasons() -> None:
    ctx, long = _orb_long(pdh="1530")
    assert choose_signal([_scored(ctx, long, 59)], ctx).reasons == ("LOW_SCORE",)
    assert choose_signal([_scored(ctx, long, 80, rr_ok=False)], ctx).reasons == ("RR_BELOW_MINIMUM",)
    none = choose_signal([], ctx, ["OR_TOO_NARROW"])
    assert (none.signal, none.reasons) == (Signal.NO_TRADE, ("NO_SETUP", "OR_TOO_NARROW"))
    short = replace(long, direction=SetupDirection.SHORT)
    assert choose_signal([_scored(ctx, short, 90)], ctx).signal is Signal.NO_TRADE  # informational only
    stale = replace(long, confirmed_at_index=3)  # confirmed earlier than T: not eligible
    assert choose_signal([_scored(ctx, stale, 90)], ctx).primary is None


def test_primary_prefers_confirmed_then_score_then_recency() -> None:
    ctx, long = _orb_long(pdh="1530")
    awaiting = replace(
        long, status=SetupStatus.AWAITING_CONFIRMATION, confirmed_at_index=None, confirm_close=None
    )
    res = choose_signal([_scored(ctx, awaiting, 99), _scored(ctx, long, 70)], ctx)
    assert res.primary is not None and res.primary.setup.status is SetupStatus.ENTRY_CONFIRMED
    a = replace(awaiting, type=SetupType.BREAKOUT_RETEST, detected_at_index=4)
    b = replace(awaiting, detected_at_index=2)
    res = choose_signal([_scored(ctx, b, 70), _scored(ctx, a, 70)], ctx)
    assert res.primary is not None and res.primary.setup.detected_at_index == 4  # more recent wins the tie


def _small(params: RulesetParams = PARAMS) -> RulesetParams:
    return RulesetParams(
        params.code, params.version, {**params.values, "analysis.min_bars_5m": 5, "analysis.min_bars_15m": 5}
    )


def test_analyse_runs_setups_and_is_deterministic() -> None:
    p = _small(load_ruleset("pa-intraday", "0.1.0"))
    b5 = mk(ORB_DAY)
    kw = {"previous_session_open": None, "session_close": CLOSE}
    prev = DailyLevels(D("1530"), D("1400"), D("1450"))
    r1 = analyse(b5, b5, OPEN, prev, p, **kw)  # type: ignore[arg-type]
    r2 = analyse(b5, b5, OPEN, prev, p, **kw)  # type: ignore[arg-type]
    assert r1.check.status is SnapshotStatus.VALID
    assert r1.setups and any(s.setup.type is SetupType.OPENING_RANGE_BREAKOUT for s in r1.setups)
    assert r1.signal is not None and r1.signal.signal_at == b5[-1].end
    assert analysis_hash(r1) == analysis_hash(r2)
    assert analysis_hash(analyse(b5[:-1], b5[:-1], OPEN, prev, p, **kw)) != analysis_hash(r1)  # type: ignore[arg-type]
    # without a session close no setup detection runs
    assert analyse(b5, b5, OPEN, prev, p).setups is None
