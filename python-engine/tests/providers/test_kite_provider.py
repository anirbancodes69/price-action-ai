"""Offline tests: httpx MockTransport, synthetic payloads, no live calls (ENG-07 §4)."""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.providers import (
    ProviderAuthExpired,
    ProviderContext,
    ProviderDataError,
    ProviderInstrumentRef,
    ProviderNotSupported,
    ProviderRateLimited,
    ProviderUnavailable,
)
from app.providers.kite import KiteProvider

IST = ZoneInfo("Asia/Kolkata")
SECRET = "SECRET-TOKEN-123"
CTX = ProviderContext("ds-1", lambda: SECRET)
REF = ProviderInstrumentRef("738561", "RELIANCE")
T0, T1 = datetime(2026, 11, 17, 9, 15, tzinfo=IST), datetime(2026, 11, 17, 10, 0, tzinfo=IST)


def make(handler: httpx.MockTransport | object) -> KiteProvider:
    client = httpx.Client(base_url="https://api.kite.trade", transport=httpx.MockTransport(handler))  # type: ignore[arg-type]
    return KiteProvider("KEY", client)


def test_fetch_bars_normalises_dedupes_and_sends_jit_token() -> None:
    seen: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["auth"] = req.headers["Authorization"]
        seen["version"] = req.headers["X-Kite-Version"]
        seen["path"] = req.url.path
        seen["from"] = req.url.params["from"]
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "candles": [
                        ["2026-11-17T09:20:00+0530", 101, 103.456, 100, 102, 500],
                        ["2026-11-17T09:15:00+0530", 100, 102, 99.5, 101, 400],
                        ["2026-11-17T09:15:00+0530", 100, 102, 99.5, 101.5, 450],
                    ]
                },
            },
        )

    bars = make(handler).fetch_bars(CTX, REF, "5m", T0, T1)
    assert seen["auth"] == f"token KEY:{SECRET}"
    assert seen["version"] == "3"
    assert seen["path"] == "/instruments/historical/738561/5minute"
    assert seen["from"] == "2026-11-17 09:15:00"
    assert [b.bar_start.hour * 60 + b.bar_start.minute for b in bars] == [555, 560]
    assert bars[0].close == Decimal("101.50") and bars[0].volume == 450  # last duplicate wins
    assert bars[1].high == Decimal("103.46")
    assert bars[0].bar_start.utcoffset() is not None


def test_unsupported_timeframe() -> None:
    with pytest.raises(ProviderNotSupported):
        make(lambda r: httpx.Response(200)).fetch_bars(CTX, REF, "1m", T0, T1)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("status", "exc"),
    [
        (403, ProviderAuthExpired),
        (429, ProviderRateLimited),
        (503, ProviderUnavailable),
        (400, ProviderDataError),
    ],
)
def test_errors_are_normalised_without_leaking_the_token(status: int, exc: type[Exception]) -> None:
    with pytest.raises(exc) as info:
        make(lambda r: httpx.Response(status, text="x")).fetch_bars(CTX, REF, "5m", T0, T1)
    assert SECRET not in str(info.value)


def test_network_failure_is_unavailable() -> None:
    def boom(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=req)

    with pytest.raises(ProviderUnavailable):
        make(boom).fetch_bars(CTX, REF, "5m", T0, T1)


def test_malformed_payload_is_data_error() -> None:
    with pytest.raises(ProviderDataError):
        make(lambda r: httpx.Response(200, json={"data": {}})).fetch_bars(CTX, REF, "5m", T0, T1)


def test_instrument_master_filters_equities_and_indices() -> None:
    csv_text = (
        "instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,"
        "instrument_type,segment,exchange\n"
        "738561,2885,RELIANCE,RELIANCE INDUSTRIES,0,,0,0.05,1,EQ,NSE,NSE\n"
        "256265,1001,NIFTY 50,NIFTY 50,0,,0,0,0,EQ,INDICES,NSE\n"
        "999,1,RELIANCE-BE,X,0,,0,0.05,1,BE,NSE,NSE\n"
    )
    out = make(lambda r: httpx.Response(200, text=csv_text)).fetch_instruments(CTX)
    assert [(i.ref.symbol, i.is_index) for i in out] == [("RELIANCE", False), ("NIFTY 50", True)]
    assert out[0].tick_size == Decimal("0.05")


def test_capabilities_are_marked_unverified() -> None:
    assert make(lambda r: httpx.Response(200)).capabilities().verified is False
