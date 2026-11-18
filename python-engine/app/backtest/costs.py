"""Dated intraday cost schedule for NSE equity (TRD-06 §5). Values are UNVERIFIED (OQ-BT-02)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


def _r(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class CostSchedule:
    version: str = "nse-intraday-assumed-0"
    brokerage_cap: Decimal = Decimal(20)  # rupees per executed order
    brokerage_pct: Decimal = Decimal("0.03")  # of order value
    stt_sell_pct: Decimal = Decimal("0.025")
    exchange_pct: Decimal = Decimal("0.00297")
    sebi_per_crore: Decimal = Decimal(10)
    stamp_buy_pct: Decimal = Decimal("0.003")
    gst_pct: Decimal = Decimal(18)  # on brokerage + exchange + SEBI


@dataclass(frozen=True, slots=True)
class Costs:
    brokerage: Decimal
    stt: Decimal
    exchange: Decimal
    sebi: Decimal
    stamp: Decimal
    gst: Decimal

    @property
    def total(self) -> Decimal:
        return self.brokerage + self.stt + self.exchange + self.sebi + self.stamp + self.gst


def intraday_costs(buy_value: Decimal, sell_value: Decimal, s: CostSchedule) -> Costs:
    """Round-trip charges. Each charge is rounded per side to paise; GST is on the rounded sum."""

    def brokerage(v: Decimal) -> Decimal:
        return _r(min(s.brokerage_cap, v * s.brokerage_pct / 100))

    brok = brokerage(buy_value) + brokerage(sell_value)
    exch = _r(buy_value * s.exchange_pct / 100) + _r(sell_value * s.exchange_pct / 100)
    sebi = _r(buy_value * s.sebi_per_crore / 10_000_000) + _r(sell_value * s.sebi_per_crore / 10_000_000)
    gst = _r((brok + exch + sebi) * s.gst_pct / 100)
    return Costs(
        brok, _r(sell_value * s.stt_sell_pct / 100), exch, sebi, _r(buy_value * s.stamp_buy_pct / 100), gst
    )
