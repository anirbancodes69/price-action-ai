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
from app.domain.types import BarState, StructureEvent, StructureResult, SwingPoint


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
            "levels": {k: (None if v is None else _price(v)) for k, v in asdict(lv).items()} if lv else None,
        }
    )


def analysis_hash(a: AnalysisResult) -> str:
    return hashlib.sha256(analysis_to_canonical(a).encode()).hexdigest()
