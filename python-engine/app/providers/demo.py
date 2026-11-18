"""DEMO provider: deterministic SAMPLE intraday bars, no network (ENG-05 §4, ADR-011).

Never market data and never presented as live. Seeded per (symbol, date) with SHA-256, so the same
inputs give the same bars on any machine. Not bar-for-bar identical to the PHP/TS demo generators
(those are tied to the seeded daily series); it only has to be deterministic and self-consistent.
"""

from __future__ import annotations

import hashlib
import random
from datetime import date, datetime
from decimal import Decimal

from app.ingestion.session import bar_minutes, session_bar_starts
from app.providers.base import (
    ProviderBar,
    ProviderCapabilities,
    ProviderContext,
    ProviderInstrument,
    ProviderInstrumentRef,
    ProviderNotSupported,
    Timeframe,
)

_SYMBOLS = ("DEMOA", "DEMOB", "DEMOC", "DEMOD", "DEMOE")
_Q = Decimal("0.05")


def _tick(x: float) -> Decimal:
    return (Decimal(str(round(x, 4))) / _Q).quantize(Decimal(1)) * _Q


class DemoProvider:
    provider_code = "DEMO"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            timeframes=("5m", "15m"),
            max_days_per_request={"5m": 365, "15m": 365},
            requests_per_second=1000.0,
            adjusted=True,
            verified=True,
        )

    def fetch_instruments(self, ctx: ProviderContext) -> list[ProviderInstrument]:
        return [
            ProviderInstrument(
                ref=ProviderInstrumentRef(str(1000 + i), s),
                name=f"{s} (sample)",
                exchange="NSE",
                segment="DEMO",
                tick_size=_Q,
                lot_size=1,
                is_index=False,
            )
            for i, s in enumerate(_SYMBOLS)
        ]

    def fetch_ltp(self, ctx: ProviderContext, symbols: list[str]) -> dict[str, Decimal]:
        # SAMPLE price: close of the latest generated weekday's last bar.
        day = date.today()
        while day.weekday() >= 5:
            day = day.fromordinal(day.toordinal() - 1)
        return {s: self._five_minute(s, day)[-1].close for s in symbols}

    def fetch_bars(
        self,
        ctx: ProviderContext,
        ref: ProviderInstrumentRef,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[ProviderBar]:
        if timeframe not in ("5m", "15m"):
            raise ProviderNotSupported(f"timeframe {timeframe}")
        out: list[ProviderBar] = []
        day = start.date()
        while day <= end.date():
            if day.weekday() < 5:  # calendar holidays are not known to the DEMO source
                five = self._five_minute(ref.symbol, day)
                bars = five if timeframe == "5m" else self._aggregate(five)
                out += [b for b in bars if start <= b.bar_start < end]
            day = day.fromordinal(day.toordinal() + 1)
        return out

    @staticmethod
    def _five_minute(symbol: str, day: date) -> list[ProviderBar]:
        seed = int.from_bytes(hashlib.sha256(f"{symbol}@{day}".encode()).digest()[:8], "big")
        rnd = random.Random(seed)  # noqa: S311 - sample data, not security
        price = 100 + rnd.random() * 2000
        starts = session_bar_starts(day, "5m")
        n = len(starts)
        bars: list[ProviderBar] = []
        for k, ts in enumerate(starts):
            o = price
            c = max(1.0, o * (1 + rnd.gauss(0, 0.0015)))
            hi = max(o, c) * (1 + abs(rnd.gauss(0, 0.0007)))
            lo = min(o, c) * (1 - abs(rnd.gauss(0, 0.0007)))
            u = 1 + 2.0 * abs(2 * (k + 0.5) / n - 1) ** 2  # U-shaped volume
            vol = int(5000 * u * (0.7 + 0.6 * rnd.random()))
            bars.append(ProviderBar(ts, "5m", _tick(o), _tick(hi), _tick(lo), _tick(c), vol))
            price = c
        return [
            ProviderBar(
                b.bar_start,
                "5m",
                b.open,
                max(b.high, b.open, b.close),
                min(b.low, b.open, b.close),
                b.close,
                b.volume,
            )
            for b in bars
        ]

    @staticmethod
    def _aggregate(five: list[ProviderBar]) -> list[ProviderBar]:
        group = bar_minutes("15m") // bar_minutes("5m")
        out: list[ProviderBar] = []
        for i in range(0, len(five) - group + 1, group):
            g = five[i : i + group]
            out.append(
                ProviderBar(
                    g[0].bar_start,
                    "15m",
                    g[0].open,
                    max(b.high for b in g),
                    min(b.low for b in g),
                    g[-1].close,
                    sum(b.volume for b in g),
                )
            )
        return out
