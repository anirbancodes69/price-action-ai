"""Setup types, lifecycle states and the detection context (TRD-04 §2)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.htf import HtfContext
from app.domain.params import RulesetParams
from app.domain.session import SessionLevels
from app.domain.types import Bar, StructureResult, SwingPoint
from app.domain.zone_cache import ZoneCache
from app.domain.zones import Zone


class SetupType(StrEnum):
    """Canonical order is the tie-break order of TRD-04 §12 (TRD-01 §7)."""

    OPENING_RANGE_BREAKOUT = "OPENING_RANGE_BREAKOUT"
    PREV_DAY_HIGH_BREAK = "PREV_DAY_HIGH_BREAK"
    PREV_DAY_LOW_BREAK = "PREV_DAY_LOW_BREAK"
    BREAKOUT_RETEST = "BREAKOUT_RETEST"


TYPE_ORDER = {t: i for i, t in enumerate(SetupType)}


class SetupStatus(StrEnum):
    FORMING = "FORMING"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    ENTRY_CONFIRMED = "ENTRY_CONFIRMED"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


TERMINAL = (SetupStatus.INVALIDATED, SetupStatus.EXPIRED)


class SetupDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class Setup:
    type: SetupType
    direction: SetupDirection
    status: SetupStatus
    detected_at_index: int
    trigger_price: Decimal
    anchor: str  # OR_HIGH, OR_LOW, PDH, PDL, ZONE
    stop_base: Decimal | None = None  # structural price the stop buffer applies to
    confirmed_at_index: int | None = None
    confirm_close: Decimal | None = None
    end_reason: str | None = None
    ended_at_index: int | None = None
    width_pct: Decimal | None = None  # opening range width
    zone: Zone | None = None  # anchor zone or level pseudo-zone
    breakout_index: int | None = None
    retest_index: int | None = None
    retest_closes_hold: bool | None = None

    @property
    def informational(self) -> bool:
        """SD-06: SHORT setups are never actionable."""
        return self.direction is SetupDirection.SHORT

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL


@dataclass(frozen=True, slots=True)
class SetupContext:
    """Everything a detector may read: closed bars up to `t` and structure derived from them."""

    bars: Sequence[Bar]
    first: int  # index of the session's first 5m bar
    t: int  # last closed 5m bar
    session_open: datetime
    cutoff: datetime  # entry cutoff (TRD-01 §4.1)
    levels: SessionLevels
    htf: Sequence[HtfContext]  # aligned 15m context for every 5m bar
    structure: StructureResult  # 5m
    pivots_5m: Sequence[SwingPoint]
    pivots_15m: Sequence[SwingPoint]
    previous_session_open: datetime | None
    params: RulesetParams
    tick: Decimal | None = None
    zone_cache: ZoneCache | None = None  # optional memo of `build_zones` (a speed-up only)
