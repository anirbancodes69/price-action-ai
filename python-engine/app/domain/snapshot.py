"""Snapshot checks before analysis (TRD-01 §4)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.domain.candles import validate_bars
from app.domain.params import RulesetParams
from app.domain.types import Bar


class SnapshotStatus(StrEnum):
    VALID = "VALID"
    INVALID_INPUT = "INVALID_INPUT"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"


@dataclass(frozen=True, slots=True)
class SnapshotCheck:
    status: SnapshotStatus
    problems: tuple[str, ...]


def check_snapshot(bars_5m: Sequence[Bar], bars_15m: Sequence[Bar], params: RulesetParams) -> SnapshotCheck:
    """Invalid bars win over short history; short history means `NO_TRADE` downstream."""
    problems = [f"5m {p}" for p in validate_bars(bars_5m)] + [f"15m {p}" for p in validate_bars(bars_15m)]
    if problems:
        return SnapshotCheck(SnapshotStatus.INVALID_INPUT, tuple(problems))
    short: list[str] = []
    if len(bars_5m) < params.int_("analysis.min_bars_5m"):
        short.append(f"5m bars {len(bars_5m)} < {params.int_('analysis.min_bars_5m')}")
    if len(bars_15m) < params.int_("analysis.min_bars_15m"):
        short.append(f"15m bars {len(bars_15m)} < {params.int_('analysis.min_bars_15m')}")
    if short:
        return SnapshotCheck(SnapshotStatus.INSUFFICIENT_HISTORY, tuple(short))
    return SnapshotCheck(SnapshotStatus.VALID, ())
