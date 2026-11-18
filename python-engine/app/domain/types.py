"""Frozen domain types (ENG-04 §2). Pure data: no I/O, no clock."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

Timeframe = Literal["5m", "15m"]


class PivotKind(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


class SwingLabel(StrEnum):
    """TRD-02 §4."""

    HH = "HH"
    LH = "LH"
    EQH = "EQH"
    HL = "HL"
    LL = "LL"
    EQL = "EQL"
    NONE = "NONE"


class StructureState(StrEnum):
    """TRD-02 §5.2."""

    SIDEWAYS = "SIDEWAYS"
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    TRANSITION = "TRANSITION"


class Direction(StrEnum):
    UP = "UP"
    DOWN = "DOWN"


class EventType(StrEnum):
    BOS = "BOS"
    CHOCH = "CHOCH"
    WICK_BREACH = "WICK_BREACH"


@dataclass(frozen=True, slots=True)
class Bar:
    """One closed bar. `start`/`end` are timestamps (ADR-015)."""

    start: datetime
    end: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class SwingPoint:
    """TRD-02 §3, §11. `confirmed_at_index = index + right_bars` (PE-03)."""

    kind: PivotKind
    index: int
    price: Decimal
    bar_start: datetime
    confirmed_at_index: int
    confirmed_at: datetime
    label: SwingLabel = SwingLabel.NONE


@dataclass(frozen=True, slots=True)
class StructureEvent:
    """TRD-02 §6-§8, §11."""

    type: EventType
    direction: Direction
    level: Decimal
    level_pivot_index: int
    break_index: int
    break_bar_start: datetime
    close: Decimal
    confirmed_at_index: int
    close_inside_buffer: bool = False


@dataclass(frozen=True, slots=True)
class BarState:
    """Machine state after processing one bar (TRD-02 §5, §9)."""

    state: StructureState
    transition_direction: Direction | None
    protected_low: SwingPoint | None
    protected_high: SwingPoint | None


@dataclass(frozen=True, slots=True)
class StructureResult:
    pivots: tuple[SwingPoint, ...]
    events: tuple[StructureEvent, ...]
    states: tuple[BarState, ...]  # one per bar, index-aligned with the input series

    @property
    def final(self) -> BarState:
        return self.states[-1]
