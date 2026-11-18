"""Market-data provider abstraction (ADR-007, ARC-08 §3).

Provider SDKs and field names live only in ``app/providers/<provider>/``.
"""

from app.providers.base import (
    MarketDataProvider,
    ProviderAuthExpired,
    ProviderBar,
    ProviderCapabilities,
    ProviderContext,
    ProviderDataError,
    ProviderError,
    ProviderInstrument,
    ProviderInstrumentRef,
    ProviderNotSupported,
    ProviderRateLimited,
    ProviderUnavailable,
    Timeframe,
)

__all__ = [
    "MarketDataProvider",
    "ProviderAuthExpired",
    "ProviderBar",
    "ProviderCapabilities",
    "ProviderContext",
    "ProviderDataError",
    "ProviderError",
    "ProviderInstrument",
    "ProviderInstrumentRef",
    "ProviderNotSupported",
    "ProviderRateLimited",
    "ProviderUnavailable",
    "Timeframe",
]
