"""Canonical serialisation of structure output and `result_hash` (PE-07, TV-NLA-04)."""

from __future__ import annotations

import hashlib
from datetime import UTC
from decimal import Decimal

from app.domain.candles import canonical_json
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
