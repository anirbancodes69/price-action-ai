"""In-sample / out-of-sample / holdout and walk-forward windows (TRD-06 §9)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Split:
    in_sample: tuple[date, ...]
    out_of_sample: tuple[date, ...]
    holdout: tuple[date, ...]


@dataclass(frozen=True, slots=True)
class Window:
    in_sample: tuple[date, ...]
    out_of_sample: tuple[date, ...]


def split_sessions(
    sessions: Sequence[date],
    is_share: Decimal = Decimal("0.6"),
    oos_share: Decimal = Decimal("0.2"),
) -> Split:
    """Chronological split; the holdout takes the remainder (500 sessions -> 300 / 100 / 100)."""
    ordered = tuple(sorted(sessions))
    n = len(ordered)
    a = int(n * is_share)
    b = a + int(n * oos_share)
    return Split(ordered[:a], ordered[a:b], ordered[b:])


def walk_forward(sessions: Sequence[date], is_len: int = 120, oos_len: int = 40) -> list[Window]:
    """Rolling windows: `is_len` sessions to explore, then `oos_len` to validate; step `oos_len`."""
    ordered = tuple(sorted(sessions))
    out: list[Window] = []
    start = 0
    while start + is_len + oos_len <= len(ordered):
        out.append(
            Window(ordered[start : start + is_len], ordered[start + is_len : start + is_len + oos_len])
        )
        start += oos_len
    return out


def oos_allows_promotion(oos_avg_r_net: Decimal | None) -> bool:
    """TRD-06 §9: OOS expectancy (net R) <= 0 blocks promotion. Necessary, not sufficient."""
    return oos_avg_r_net is not None and oos_avg_r_net > 0


def walk_forward_positive_in_most(window_avg_r_net: Sequence[Decimal | None]) -> bool:
    """Positive in most (more than half) of the OOS windows, not only in aggregate."""
    if not window_avg_r_net:
        return False
    positive = sum(1 for v in window_avg_r_net if v is not None and v > 0)
    return positive * 2 > len(window_avg_r_net)
