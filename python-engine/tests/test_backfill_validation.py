"""A corrupt provider bar is rejected and reported, never stored and never fatal (the `candles` constraints)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.ingestion.backfill import invalid_bar_reason
from app.ingestion.session import IST
from app.providers.base import ProviderBar

D = Decimal
T = datetime(2024, 6, 25, 9, 15, tzinfo=IST)


def bar(o: str, h: str, lo: str, c: str, v: int = 1000) -> ProviderBar:
    return ProviderBar(T, "5m", D(o), D(h), D(lo), D(c), v)


def test_a_valid_bar_is_accepted() -> None:
    assert invalid_bar_reason(bar("100", "101", "99", "100.5")) is None
    assert invalid_bar_reason(bar("100", "100", "100", "100", 0)) is None  # flat bar, no volume


def test_the_bar_kite_returned_on_2024_06_25_is_rejected() -> None:
    assert invalid_bar_reason(bar("1434.00", "1429.85", "1422.30", "1424.55")) == "OHLC out of order"


def test_each_broken_rule_is_named() -> None:
    assert (
        invalid_bar_reason(bar("100", "101", "100.5", "100.2")) == "OHLC out of order"
    )  # low above the open
    assert invalid_bar_reason(bar("100", "99", "98", "98.5")) == "OHLC out of order"  # high below the open
    assert invalid_bar_reason(bar("0", "1", "0", "1")) == "non-positive price"
    assert invalid_bar_reason(bar("100", "101", "99", "100", -1)) == "negative volume"
