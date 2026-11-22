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


# Groww's published equity intraday charges read on 2026-11-23 (DX-6, framework-diagnosis-report.md):
# brokerage 0.1% per order capped at 20 rupees; NSE exchange charge 0.00307% (its pricing page; the help
# page says 0.00297%); the other items are unchanged. The investor-protection-fund charge (0.0001%, both
# sides) is not modelled. Not used by any run unless chosen; no dated history is verified (OQ-BT-02).
GROWW_PUBLISHED = CostSchedule(
    version="groww-published-2026-11-23", brokerage_pct=Decimal("0.1"), exchange_pct=Decimal("0.00307")
)


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


@dataclass(frozen=True, slots=True)
class DeliverySchedule:
    """Equity delivery charges (ADR-019): UNVERIFIED published rates (OQ-HP-04)."""

    version: str = "groww-delivery-published-2026-11-23"
    brokerage_cap: Decimal = Decimal(20)  # rupees per executed order
    brokerage_pct: Decimal = Decimal("0.1")  # of order value
    stt_pct: Decimal = Decimal("0.1")  # both sides
    exchange_pct: Decimal = Decimal("0.00307")  # NSE; the help page says 0.00297
    sebi_pct: Decimal = Decimal("0.0001")  # 10 rupees per crore
    ipft_pct: Decimal = Decimal("0.0001")  # investor-protection-fund trust charge, NSE
    stamp_buy_pct: Decimal = Decimal("0.015")
    dp_per_sell: Decimal = Decimal(20)  # depository 3.50 + broker 16.50
    gst_pct: Decimal = Decimal(18)  # on brokerage, exchange, SEBI, IPFT and DP; not on STT or stamp duty


@dataclass(frozen=True, slots=True)
class DeliveryCosts:
    brokerage: Decimal
    stt: Decimal
    exchange: Decimal
    sebi: Decimal
    ipft: Decimal
    stamp: Decimal
    dp: Decimal
    gst: Decimal

    @property
    def total(self) -> Decimal:
        return (
            self.brokerage
            + self.stt
            + self.exchange
            + self.sebi
            + self.ipft
            + self.stamp
            + self.dp
            + self.gst
        )


def delivery_costs(buy_value: Decimal, sell_value: Decimal, s: DeliverySchedule) -> DeliveryCosts:
    """Round-trip delivery charges. Each charge is rounded per side to paise; GST is on the rounded sum."""

    def brokerage(v: Decimal) -> Decimal:
        return _r(min(s.brokerage_cap, v * s.brokerage_pct / 100))

    brok = brokerage(buy_value) + brokerage(sell_value)
    exch = _r(buy_value * s.exchange_pct / 100) + _r(sell_value * s.exchange_pct / 100)
    sebi = _r(buy_value * s.sebi_pct / 100) + _r(sell_value * s.sebi_pct / 100)
    ipft = _r(buy_value * s.ipft_pct / 100) + _r(sell_value * s.ipft_pct / 100)
    gst = _r((brok + exch + sebi + ipft + s.dp_per_sell) * s.gst_pct / 100)
    stt = _r(buy_value * s.stt_pct / 100) + _r(sell_value * s.stt_pct / 100)
    return DeliveryCosts(
        brok, stt, exch, sebi, ipft, _r(buy_value * s.stamp_buy_pct / 100), s.dp_per_sell, gst
    )
