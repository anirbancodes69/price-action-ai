"""Canonical serialisation of structure output and `result_hash` (PE-07, TV-NLA-04)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC
from decimal import Decimal

from app.domain.analyse import AnalysisResult
from app.domain.candles import canonical_json
from app.domain.htf import HtfContext
from app.domain.liquidity import LiquidityPool
from app.domain.setups.signal import ScoredSetup, SignalResult
from app.domain.types import BarState, StructureEvent, StructureResult, SwingPoint
from app.domain.zones import Zone


def _price(p: Decimal) -> str:
    return format(p, "f")


def _pivot(p: SwingPoint) -> dict[str, object]:
    return {
        "kind": p.kind.value,
        "index": p.index,
        "price": _price(p.price),
        "bar_start": p.bar_start.astimezone(UTC).isoformat(),
        "confirmed_at_index": p.confirmed_at_index,
        "confirmed_at": p.confirmed_at.astimezone(UTC).isoformat(),
        "label": p.label.value,
    }


def _event(e: StructureEvent) -> dict[str, object]:
    return {
        "type": e.type.value,
        "direction": e.direction.value,
        "level": _price(e.level),
        "level_pivot_index": e.level_pivot_index,
        "break_index": e.break_index,
        "break_bar_start": e.break_bar_start.astimezone(UTC).isoformat(),
        "close": _price(e.close),
        "close_inside_buffer": e.close_inside_buffer,
    }


def _state(s: BarState) -> dict[str, object]:
    return {
        "state": s.state.value,
        "transition_direction": s.transition_direction.value if s.transition_direction else None,
        "protected_low": s.protected_low.index if s.protected_low else None,
        "protected_high": s.protected_high.index if s.protected_high else None,
    }


def structure_to_canonical(r: StructureResult) -> str:
    return canonical_json(
        {
            "pivots": [_pivot(p) for p in r.pivots],
            "events": [_event(e) for e in r.events],
            "states": [_state(s) for s in r.states],
        }
    )


def result_hash(r: StructureResult) -> str:
    return hashlib.sha256(structure_to_canonical(r).encode()).hexdigest()


def _zone(z: Zone) -> dict[str, object]:
    return {
        "low": _price(z.low),
        "high": _price(z.high),
        "members": [
            [m.timeframe, m.pivot.index, m.pivot.kind.value, _price(m.pivot.price)] for m in z.members
        ],
        "formed_at_index": z.formed_at_index,
        "status": z.status.value,
        "broken_direction": z.broken_direction.value if z.broken_direction else None,
        "broken_at_index": z.broken_at_index,
        "touches": z.touches,
        "strength": z.strength,
        "bucket": z.bucket.value,
    }


def _pool(p: LiquidityPool) -> dict[str, object]:
    return {
        "type": p.type.value,
        "level": _price(p.level),
        "first_index": p.first_index,
        "second_index": p.second_index,
        "confirmed_at_index": p.confirmed_at_index,
    }


def _opt(v: Decimal | None) -> str | None:
    return None if v is None else _price(v)


def _scored(x: ScoredSetup) -> dict[str, object]:
    s, lv, p = x.setup, x.levels, x.paqs
    return {
        "type": s.type.value,
        "direction": s.direction.value,
        "status": s.status.value,
        "detected_at_index": s.detected_at_index,
        "trigger_price": _price(s.trigger_price),
        "anchor": s.anchor,
        "confirmed_at_index": s.confirmed_at_index,
        "end_reason": s.end_reason,
        "ended_at_index": s.ended_at_index,
        "informational": s.informational,
        "levels": None
        if lv is None
        else {
            "entry": _price(lv.entry),
            "stop": _price(lv.stop),
            "target": _opt(lv.target),
            "target_source": lv.target_source,
            "rr": _opt(lv.rr.quantize(Decimal("0.0001")) if lv.rr is not None else None),
            "rr_below_min": lv.rr_below_min,
        },
        "paqs": None
        if p is None
        else {
            "version": p.version,
            "total": p.total,
            "components": [[c.name, c.points, c.maximum, c.missing] for c in p.components],
        },
    }


def _signal(r: SignalResult | None) -> dict[str, object] | None:
    if r is None:
        return None
    return {
        "signal": r.signal.value,
        "primary": None
        if r.primary is None
        else [r.primary.setup.type.value, r.primary.setup.detected_at_index],
        "reasons": list(r.reasons),
        "signal_at": r.signal_at.astimezone(UTC).isoformat(),
        "valid_until": r.valid_until.astimezone(UTC).isoformat() if r.valid_until else None,
    }


def _htf(h: HtfContext | None) -> dict[str, object] | None:
    if h is None:
        return None
    return {"index": h.index, "state": _state(h.state) if h.state else None}


def analysis_to_canonical(a: AnalysisResult) -> str:
    """Canonical form of a whole analysis (status, input hashes, structure, context, levels)."""
    lv = a.levels
    return canonical_json(
        {
            "ruleset": [a.ruleset_code, a.ruleset_version],
            "status": a.check.status.value,
            "problems": list(a.check.problems),
            "input_hash_5m": a.input_hash_5m,
            "input_hash_15m": a.input_hash_15m,
            "structure_5m": json.loads(structure_to_canonical(a.structure_5m)) if a.structure_5m else None,
            "structure_15m": json.loads(structure_to_canonical(a.structure_15m)) if a.structure_15m else None,
            "htf": {"index": a.htf.index, "state": _state(a.htf.state) if a.htf.state else None}
            if a.htf
            else None,
            "setups": [_scored(x) for x in a.setups] if a.setups is not None else None,
            "signal": _signal(a.signal),
            "no_setup_reasons": list(a.no_setup_reasons),
            "zones": [_zone(z) for z in a.zones] if a.zones is not None else None,
            "pools": [_pool(x) for x in a.pools] if a.pools is not None else None,
            "levels": {k: (None if v is None else _price(v)) for k, v in asdict(lv).items()} if lv else None,
        }
    )


def analysis_hash(a: AnalysisResult) -> str:
    return hashlib.sha256(analysis_to_canonical(a).encode()).hexdigest()
