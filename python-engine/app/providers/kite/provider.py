"""Zerodha Kite Connect adapter (REST, read-only market data).

ASSUMPTION - unverified until T-201 (needs a Kite developer app): endpoint shapes follow the
public Kite Connect v3 documentation as remembered; history depth and rate limits are placeholders.
Never place orders: ADR-010.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.providers.base import (
    ProviderAuthExpired,
    ProviderBar,
    ProviderCapabilities,
    ProviderContext,
    ProviderDataError,
    ProviderInstrument,
    ProviderInstrumentRef,
    ProviderNotSupported,
    ProviderRateLimited,
    ProviderUnavailable,
    Timeframe,
)

IST = ZoneInfo("Asia/Kolkata")
BASE_URL = "https://api.kite.trade"
_INTERVALS: dict[str, str] = {"5m": "5minute", "15m": "15minute", "1D": "day"}
_PRICE_QUANTUM = Decimal("0.01")


class KiteProvider:
    provider_code = "ZERODHA_KITE"

    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(base_url=BASE_URL, timeout=15.0)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            timeframes=("5m", "15m", "1D"),
            max_days_per_request={"5m": 100, "15m": 200, "1D": 2000},  # placeholders
            requests_per_second=3.0,  # placeholder
            adjusted=False,
            verified=False,
        )

    def fetch_instruments(self, ctx: ProviderContext) -> list[ProviderInstrument]:
        text = self._get(ctx, "/instruments/NSE").text
        out: list[ProviderInstrument] = []
        for row in csv.DictReader(io.StringIO(text)):
            segment = row.get("segment", "")
            is_index = segment == "INDICES"
            if not is_index and not (segment == "NSE" and row.get("instrument_type") == "EQ"):
                continue
            try:
                out.append(
                    ProviderInstrument(
                        ref=ProviderInstrumentRef(row["instrument_token"], row["tradingsymbol"]),
                        name=row.get("name", ""),
                        exchange=row.get("exchange", "NSE"),
                        segment=segment,
                        tick_size=Decimal(row.get("tick_size") or "0.05"),
                        lot_size=int(row.get("lot_size") or 1),
                        is_index=is_index,
                    )
                )
            except (KeyError, ValueError, InvalidOperation) as exc:
                raise ProviderDataError("malformed instrument row") from exc
        return out

    def fetch_bars(
        self,
        ctx: ProviderContext,
        ref: ProviderInstrumentRef,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[ProviderBar]:
        interval = _INTERVALS.get(timeframe)
        if interval is None:
            raise ProviderNotSupported(f"timeframe {timeframe}")
        fmt = "%Y-%m-%d %H:%M:%S"
        params = {"from": start.astimezone(IST).strftime(fmt), "to": end.astimezone(IST).strftime(fmt)}
        payload = self._get(ctx, f"/instruments/historical/{ref.token}/{interval}", params).json()
        try:
            candles = payload["data"]["candles"]
            bars = [self._bar(c, timeframe) for c in candles]
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise ProviderDataError("malformed candle payload") from exc
        # Duplicates collapse to the last one received (ENG-05 §6); output is time-ordered.
        unique = {b.bar_start: b for b in bars}
        return [unique[k] for k in sorted(unique)]

    @staticmethod
    def _bar(c: list[Any], timeframe: Timeframe) -> ProviderBar:
        ts = datetime.strptime(str(c[0]), "%Y-%m-%dT%H:%M:%S%z").astimezone(IST)

        def price(v: Any) -> Decimal:
            return Decimal(str(v)).quantize(_PRICE_QUANTUM)

        return ProviderBar(ts, timeframe, price(c[1]), price(c[2]), price(c[3]), price(c[4]), int(c[5]))

    def _get(self, ctx: ProviderContext, path: str, params: dict[str, str] | None = None) -> httpx.Response:
        # JIT token: obtained per call, held only in this local header.
        headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self._api_key}:{ctx.credentials_supplier()}",
        }
        try:
            resp = self._client.get(path, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(type(exc).__name__) from None
        status = resp.status_code
        if status in (401, 403):
            raise ProviderAuthExpired("Kite rejected the access token")
        if status == 429:
            raise ProviderRateLimited("Kite rate limit")
        if status >= 500:
            raise ProviderUnavailable(f"Kite HTTP {status}")
        if status >= 400:
            raise ProviderDataError(f"Kite HTTP {status}")
        return resp
