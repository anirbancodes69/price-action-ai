"""Effective-dated, instrument-specific tick resolution (OD-8 Step 2, decision D2).

Pure and deterministic. There is no default tick: a symbol and date that no row covers resolve to `UNKNOWN`,
never to 0.05. Overlapping, duplicate or conflicting rows make the table invalid (it fails to build), so a
conflict can never be resolved silently.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from itertools import pairwise

RESOLVER_VERSION = "tick-resolver-1.0.0"

UNKNOWN_NO_ROW = "NO_TICK_ROW_COVERS_DATE"


class TickTableError(ValueError):
    """The tick table is internally inconsistent; the run must not start."""


@dataclass(frozen=True, slots=True)
class TickResolution:
    """`RESOLVED(value, basis)` or `UNKNOWN(reason)`; never a silent default."""

    value: Decimal | None
    basis: str | None = None
    reason: str | None = None

    @property
    def resolved(self) -> bool:
        return self.value is not None

    @staticmethod
    def resolved_as(value: Decimal, basis: str) -> TickResolution:
        if not value.is_finite() or value <= 0:
            raise ValueError("tick must be a positive finite Decimal")
        return TickResolution(value, basis, None)

    @staticmethod
    def unknown(reason: str) -> TickResolution:
        return TickResolution(None, None, reason)


@dataclass(frozen=True, slots=True)
class TickRow:
    symbol: str
    effective_from: date
    effective_to: date | None  # inclusive; None = open ended
    tick: Decimal
    basis: str  # evidence reference, for example the NSE circular number


class TickTable:
    """Rows validated at construction; `resolve` is a pure lookup."""

    def __init__(self, rows: Iterable[TickRow]) -> None:
        by_symbol: dict[str, list[TickRow]] = {}
        for r in rows:
            if not r.tick.is_finite() or r.tick <= 0:
                raise TickTableError(f"{r.symbol}: tick must be positive and finite, got {r.tick}")
            if r.effective_to is not None and r.effective_to < r.effective_from:
                raise TickTableError(f"{r.symbol}: effective_to before effective_from")
            by_symbol.setdefault(r.symbol, []).append(r)
        for sym, rs in by_symbol.items():
            rs.sort(key=lambda r: r.effective_from)
            for a, b in pairwise(rs):
                if a.effective_from == b.effective_from:
                    raise TickTableError(f"{sym}: duplicate row for {a.effective_from}")
                if a.effective_to is None or a.effective_to >= b.effective_from:
                    kind = "conflicting" if a.tick != b.tick else "overlapping"
                    raise TickTableError(f"{sym}: {kind} rows at {b.effective_from}")
        self._rows: dict[str, tuple[TickRow, ...]] = {s: tuple(r) for s, r in by_symbol.items()}

    @property
    def rows(self) -> Sequence[TickRow]:
        return [r for s in sorted(self._rows) for r in self._rows[s]]

    def resolve(self, symbol: str, day: date) -> TickResolution:
        for r in self._rows.get(symbol, ()):
            if r.effective_from <= day and (r.effective_to is None or day <= r.effective_to):
                return TickResolution.resolved_as(r.tick, r.basis)
        return TickResolution.unknown(UNKNOWN_NO_ROW)
