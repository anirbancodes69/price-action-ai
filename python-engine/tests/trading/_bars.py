"""Hand-built 5-minute bar fixtures (timestamps do not affect the rules)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.types import Bar

_T0 = datetime(2026, 11, 18, 3, 45, tzinfo=UTC)  # 09:15 IST


def bars_from(rows: list[tuple[str, str, str, str]]) -> list[Bar]:
    """Rows are (open, high, low, close) strings -> Decimal bars."""
    out: list[Bar] = []
    for i, (o, h, lo, c) in enumerate(rows):
        start = _T0 + timedelta(minutes=5 * i)
        out.append(Bar(start, start + timedelta(minutes=5), Decimal(o), Decimal(h), Decimal(lo), Decimal(c)))
    return out


def bars_hlc(rows: list[tuple[str, str, str]]) -> list[Bar]:
    """Rows are (high, low, close); open = previous close (first: low)."""
    full: list[tuple[str, str, str, str]] = []
    prev = None
    for h, lo, c in rows:
        full.append((prev if prev is not None else lo, h, lo, c))
        prev = c
    return bars_from(full)
