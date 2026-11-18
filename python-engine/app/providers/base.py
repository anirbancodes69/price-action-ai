"""Normalised provider types, errors and the ``MarketDataProvider`` protocol."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol

Timeframe = Literal["5m", "15m", "1D"]


class ProviderError(Exception):
    """Base class of normalised provider errors."""


class ProviderAuthExpired(ProviderError):
    """The access token is missing, invalid or expired (Kite tokens expire daily)."""


class ProviderRateLimited(ProviderError):
    """The provider throttled the request."""


class ProviderUnavailable(ProviderError):
    """Network failure or provider 5xx."""


class ProviderDataError(ProviderError):
    """The provider answered, but the payload is unusable (4xx, malformed)."""


class ProviderNotSupported(ProviderError):
    """The provider cannot serve this request (e.g. timeframe)."""


@dataclass(frozen=True, slots=True)
class ProviderInstrumentRef:
    """Provider-side identity of an instrument (token is opaque outside the adapter)."""

    token: str
    symbol: str


@dataclass(frozen=True, slots=True)
class ProviderInstrument:
    ref: ProviderInstrumentRef
    name: str
    exchange: str
    segment: str
    tick_size: Decimal
    lot_size: int
    is_index: bool


@dataclass(frozen=True, slots=True)
class ProviderBar:
    """A closed bar. ``bar_start`` is timezone-aware (Asia/Kolkata for NSE)."""

    bar_start: datetime
    timeframe: Timeframe
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Provider limits. Every value is an UNVERIFIED placeholder until T-201 (OQ-INT-01)."""

    timeframes: tuple[Timeframe, ...]
    max_days_per_request: dict[str, int]
    requests_per_second: float
    adjusted: bool
    verified: bool = False


@dataclass(frozen=True, slots=True)
class ProviderContext:
    """Per-call context. ``credentials_supplier`` performs the just-in-time token fetch
    (ARC-06 §5); the token is never stored on this object, logged or put in a job payload."""

    data_source_id: str
    credentials_supplier: Callable[[], str]


class MarketDataProvider(Protocol):
    provider_code: str

    def fetch_instruments(self, ctx: ProviderContext) -> list[ProviderInstrument]: ...

    def fetch_bars(
        self,
        ctx: ProviderContext,
        ref: ProviderInstrumentRef,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[ProviderBar]: ...

    def capabilities(self) -> ProviderCapabilities: ...
