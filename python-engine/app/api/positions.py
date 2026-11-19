"""``POST /internal/v1/positions/evaluate`` (TRD-07 §7.1): HOLD or EXIT for open positions on closed bars."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import ruleset_for
from app.api.scan import SnapshotSource, get_analyse_fn, get_snapshot_source
from app.backtest.replay import AnalyseFn, SessionSpec
from app.domain.risk.monitor import monitor_position
from app.domain.types import Bar, Direction, EventType
from app.schemas.positions import PositionsEvaluation, PositionsEvaluationRequest, PositionSignalModel
from app.settings import Settings, get_settings

router = APIRouter(prefix="/positions")


@router.post("/evaluate")
def evaluate(
    req: PositionsEvaluationRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    source: Annotated[SnapshotSource, Depends(get_snapshot_source)],
    analyse_fn: Annotated[AnalyseFn, Depends(get_analyse_fn)],
) -> PositionsEvaluation:
    """Each position's signal: the first exit condition met on a closed bar since entry, else HOLD."""
    params = ruleset_for(settings)
    if source.source_info(req.data_source_id) is None:
        raise HTTPException(404, detail="DATA_SOURCE_NOT_FOUND")
    lookback = params.int_("analysis.lookback_sessions")
    structure_on = bool(params.get("exit.structure_exit_enabled"))
    session_on = bool(params.get("exit.session_end_exit_enabled"))
    exit_minutes = params.int_("session.exit_minutes_before_close")

    cache: dict[str, tuple[Sequence[Bar], frozenset[int], SessionSpec] | None] = {}
    out: list[PositionSignalModel] = []
    for p in req.positions:
        if p.symbol not in cache:
            snap = source.symbol(req.data_source_id, p.symbol, req.as_of_ts, lookback)
            if snap is None:
                cache[p.symbol] = None
            else:
                sym, spec = snap
                res = analyse_fn(sym, len(sym.bars_5m), spec, params)
                events = res.structure_5m.events if res.structure_5m else ()
                choch_down = frozenset(
                    e.break_index
                    for e in events
                    if e.type is EventType.CHOCH and e.direction is Direction.DOWN
                )
                cache[p.symbol] = (sym.bars_5m, choch_down, spec)
        hit = cache[p.symbol]
        if hit is None:
            out.append(
                PositionSignalModel(
                    id=p.id, symbol=p.symbol, signal=None, reason=None, bar_end=None, as_of_ts=None
                )
            )
            continue
        bars, choch_down, spec = hit
        sig = monitor_position(
            bars,
            p.entry_at,
            p.stop,
            p.target,
            choch_down,
            spec.session_close - timedelta(minutes=exit_minutes),
            structure_on,
            session_on,
        )
        out.append(
            PositionSignalModel(
                id=p.id,
                symbol=p.symbol,
                signal=sig.signal,
                reason=sig.reason,
                bar_end=sig.bar_end,
                as_of_ts=bars[-1].end,
            )
        )
    return PositionsEvaluation(ruleset_version=f"{params.code} {params.version}", positions=out)
