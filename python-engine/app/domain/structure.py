"""Structure state machine: BOS, CHoCH, wick breaches (TRD-02 §5-§8, §10)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.types import (
    Bar,
    BarState,
    Direction,
    EventType,
    PivotKind,
    StructureEvent,
    StructureResult,
    StructureState,
    SwingLabel,
    SwingPoint,
)

_UP_OK = (SwingLabel.HL, SwingLabel.EQL)  # §5.3: last_sl label allowing SIDEWAYS -> BULLISH
_DOWN_OK = (SwingLabel.LH, SwingLabel.EQH)  # mirror for last_sh


@dataclass(slots=True)
class _Machine:
    state: StructureState = StructureState.SIDEWAYS
    direction: Direction | None = None
    choch_index: int = -1
    protected_low: SwingPoint | None = None
    protected_high: SwingPoint | None = None


def run_structure(
    bars: Sequence[Bar],
    pivots: Sequence[SwingPoint],
    buffer: Decimal,
) -> StructureResult:
    """Run the machine bar by bar. `pivots` are labelled, in confirmation order.

    Per bar `t`: (1) pivots confirmed at `t` become known, (2) closes are tested
    against pivots confirmed at `t-1` or earlier (§6: a pivot cannot be broken by
    the bar that confirms it).
    """
    m = _Machine()
    known: list[SwingPoint] = []
    broken: set[tuple[PivotKind, int]] = set()
    events: list[StructureEvent] = []
    states: list[BarState] = []
    cursor = 0

    def last(kind: PivotKind) -> SwingPoint | None:
        return next((p for p in reversed(known) if p.kind is kind), None)

    def last_before(kind: PivotKind, t: int) -> SwingPoint | None:
        return next((p for p in reversed(known) if p.kind is kind and p.index < t), None)

    for t, bar in enumerate(bars):
        while cursor < len(pivots) and pivots[cursor].confirmed_at_index <= t:
            known.append(pivots[cursor])
            cursor += 1

        def testable(kind: PivotKind, t: int = t) -> SwingPoint | None:
            p = last(kind)
            if p is None or p.confirmed_at_index > t - 1 or (p.kind, p.index) in broken:
                return None
            return p

        sh, sl = testable(PivotKind.HIGH), testable(PivotKind.LOW)
        up_level = sh.price * (1 + buffer) if sh else None
        down_level = sl.price * (1 - buffer) if sl else None
        close = bar.close

        def emit(
            kind: EventType,
            d: Direction,
            piv: SwingPoint,
            inside: bool = False,
            t: int = t,
            bar: Bar = bar,
        ) -> None:
            events.append(StructureEvent(kind, d, piv.price, piv.index, t, bar.start, bar.close, t, inside))

        bos_up = (
            sh is not None
            and up_level is not None
            and close > up_level
            and (
                m.state is StructureState.BULLISH
                or (
                    m.state is StructureState.SIDEWAYS
                    and (x := last(PivotKind.LOW)) is not None
                    and x.label in _UP_OK
                )
                or (
                    m.state is StructureState.TRANSITION
                    and m.direction is Direction.UP
                    and sh.confirmed_at_index > m.choch_index
                )
            )
        )
        bos_down = (
            sl is not None
            and down_level is not None
            and close < down_level
            and (
                m.state is StructureState.BEARISH
                or (
                    m.state is StructureState.SIDEWAYS
                    and (x := last(PivotKind.HIGH)) is not None
                    and x.label in _DOWN_OK
                )
                or (
                    m.state is StructureState.TRANSITION
                    and m.direction is Direction.DOWN
                    and sl.confirmed_at_index > m.choch_index
                )
            )
        )

        in_up = m.state is StructureState.BULLISH or (
            m.state is StructureState.TRANSITION and m.direction is Direction.UP
        )
        in_down = m.state is StructureState.BEARISH or (
            m.state is StructureState.TRANSITION and m.direction is Direction.DOWN
        )
        choch_down = in_up and m.protected_low is not None and close < m.protected_low.price * (1 - buffer)
        choch_up = in_down and m.protected_high is not None and close > m.protected_high.price * (1 + buffer)

        if choch_down and m.protected_low is not None:
            emit(EventType.CHOCH, Direction.DOWN, m.protected_low)
            m.state, m.direction, m.choch_index = StructureState.TRANSITION, Direction.DOWN, t
            m.protected_high = last_before(PivotKind.HIGH, t)
        elif choch_up and m.protected_high is not None:
            emit(EventType.CHOCH, Direction.UP, m.protected_high)
            m.state, m.direction, m.choch_index = StructureState.TRANSITION, Direction.UP, t
            m.protected_low = last_before(PivotKind.LOW, t)
        elif bos_up and sh is not None:
            emit(EventType.BOS, Direction.UP, sh)
            m.state, m.direction = StructureState.BULLISH, None
            m.protected_low = last_before(PivotKind.LOW, t)
        elif bos_down and sl is not None:
            emit(EventType.BOS, Direction.DOWN, sl)
            m.state, m.direction = StructureState.BEARISH, None
            m.protected_high = last_before(PivotKind.HIGH, t)

        # Wick breaches of last_sh / last_sl (§8) and silent breaking of older levels (§10).
        for kind in (PivotKind.HIGH, PivotKind.LOW):
            for p in known:
                if p.kind is not kind or p.confirmed_at_index > t - 1 or (p.kind, p.index) in broken:
                    continue
                if kind is PivotKind.HIGH:
                    lvl = p.price * (1 + buffer)
                    closed = close > lvl
                    wick = bar.high > p.price and not closed
                else:
                    lvl = p.price * (1 - buffer)
                    closed = close < lvl
                    wick = bar.low < p.price and not closed
                if closed:
                    broken.add((p.kind, p.index))
                elif wick and p is (sh if kind is PivotKind.HIGH else sl):
                    inside = close > p.price if kind is PivotKind.HIGH else close < p.price
                    emit(
                        EventType.WICK_BREACH,
                        Direction.UP if kind is PivotKind.HIGH else Direction.DOWN,
                        p,
                        inside,
                    )

        states.append(BarState(m.state, m.direction, m.protected_low, m.protected_high))

    return StructureResult(tuple(pivots), tuple(events), tuple(states))
