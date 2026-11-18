"""Map an `AnalysisResult` to the analysis-detail contract (no new calculation)."""

from __future__ import annotations

from app.backtest.replay import SessionSpec, SymbolData
from app.domain.analyse import AnalysisResult
from app.domain.zone_build import zone_role
from app.schemas.analysis_detail import (
    AnalysisDetail,
    EventModel,
    PaqsComponentModel,
    PivotModel,
    PoolModel,
    SessionLevelsModel,
    SetupModel,
    SignalModel,
    ZoneModel,
)

MAX_PIVOTS, MAX_EVENTS = 40, 25


def to_detail(sym: SymbolData, spec: SessionSpec, res: AnalysisResult) -> AnalysisDetail:
    bars = sym.bars_5m
    s5, htf = res.structure_5m, res.htf
    final = s5.states[-1] if s5 and s5.states else None
    s5.states[-1] if s5 and s5.states else None
    pivots: list[PivotModel] = []
    events: list[EventModel] = []
    if s5 is not None:
        pivots = [
            PivotModel(
                kind=p.kind.value,
                bar_start=p.bar_start,
                price=p.price,
                label=p.label.value,
                confirmed_at=p.confirmed_at,
            )
            for p in s5.pivots[-MAX_PIVOTS:]
        ]
        events = [
            EventModel(
                type=e.type.value,
                direction=e.direction.value,
                level=e.level,
                break_bar_start=e.break_bar_start,
                close=e.close,
                close_inside_buffer=e.close_inside_buffer,
            )
            for e in s5.events[-MAX_EVENTS:]
        ]
    close = bars[-1].close
    zones = [
        ZoneModel(
            role=zone_role(z, close).value,
            low=z.low,
            high=z.high,
            touches=z.touches,
            strength=z.strength,
            strength_bucket=z.bucket.value,
            status=z.status.value,
            role_reversed=z.role_reversed,
            htf_member=z.has_htf_member,
        )
        for z in (res.zones or ())
    ]
    setups: list[SetupModel] = []
    for x in res.setups or ():
        s, lv, p = x.setup, x.levels, x.paqs
        setups.append(
            SetupModel(
                type=s.type.value,
                direction=s.direction.value,
                informational=s.informational,
                status=s.status.value,
                detected_at=bars[s.detected_at_index].end,
                trigger_price=s.trigger_price,
                entry=lv.entry if lv else None,
                stop=lv.stop if lv else None,
                target=lv.target if lv else None,
                target_source=lv.target_source if lv else None,
                rr=lv.rr if lv else None,
                rr_below_min=lv.rr_below_min if lv else None,
                paqs=p.total if p else None,
                paqs_version=p.version if p else None,
                paqs_components=[
                    PaqsComponentModel(name=c.name, points=c.points, maximum=c.maximum, missing=c.missing)
                    for c in (p.components if p else ())
                ],
                end_reason=s.end_reason,
            )
        )
    lv_ = res.levels
    sig = res.signal
    return AnalysisDetail(
        symbol=sym.symbol,
        session_date=spec.session_date.isoformat(),
        as_of_ts=bars[-1].end,
        status=res.check.status.value,
        problems=list(res.check.problems),
        ruleset_version=f"{res.ruleset_code} {res.ruleset_version}",
        state_5m=final.state.value if final else None,
        transition_direction_5m=(
            final.transition_direction.value if final and final.transition_direction else None
        ),
        state_15m=htf.state.state.value if htf and htf.state else None,
        levels=SessionLevelsModel(
            pdh=lv_.pdh,
            pdl=lv_.pdl,
            pdc=lv_.pdc,
            or_high=lv_.or_high,
            or_low=lv_.or_low,
            session_high=lv_.session_high,
            session_low=lv_.session_low,
        )
        if lv_
        else None,
        pivots=pivots,
        events=events,
        zones=zones,
        pools=[PoolModel(type=x.type.value, level=x.level) for x in (res.pools or ())],
        setups=setups,
        signal=SignalModel(
            signal=sig.signal.value,
            reasons=list(sig.reasons),
            signal_at=sig.signal_at,
            valid_until=sig.valid_until,
        )
        if sig
        else None,
        no_setup_reasons=list(res.no_setup_reasons),
    )
