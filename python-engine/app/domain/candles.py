"""Candle validation and canonical serialisation (TRD-01 §4, PE-07)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC

from app.domain.types import Bar


def validate_bars(bars: Sequence[Bar]) -> list[str]:
    """Problems that make a snapshot `INVALID_INPUT`; empty list when valid.

    Rejects: L <= min(O,C) <= max(O,C) <= H violated, non-positive price,
    duplicate or out-of-order bar starts, and a bar whose end is not after its start.
    """
    problems: list[str] = []
    for i, b in enumerate(bars):
        if min(b.open, b.high, b.low, b.close) <= 0:
            problems.append(f"bar {i}: non-positive price")
        if not (b.low <= min(b.open, b.close) <= max(b.open, b.close) <= b.high):
            problems.append(f"bar {i}: OHLC out of order")
        if b.end <= b.start:
            problems.append(f"bar {i}: end not after start")
        if i > 0:
            if b.start == bars[i - 1].start:
                problems.append(f"bar {i}: duplicate start")
            elif b.start < bars[i - 1].start:
                problems.append(f"bar {i}: out of order")
    return problems


def canonical_bar(b: Bar) -> dict[str, str]:
    """Fixed-form mapping: UTC ISO timestamps, decimal strings."""
    return {
        "start": b.start.astimezone(UTC).isoformat(),
        "end": b.end.astimezone(UTC).isoformat(),
        "open": format(b.open, "f"),
        "high": format(b.high, "f"),
        "low": format(b.low, "f"),
        "close": format(b.close, "f"),
    }


def canonical_json(obj: object) -> str:
    """Sorted keys, no whitespace: byte-stable across runs."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def candles_hash(bars: Sequence[Bar]) -> str:
    """SHA-256 of the canonical bar list (input identity of an analysis)."""
    return hashlib.sha256(canonical_json([canonical_bar(b) for b in bars]).encode()).hexdigest()
