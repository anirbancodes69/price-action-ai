# ADR-007: Market Data Provider Abstraction

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-15 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [ARC-08](../architecture/08_INTEGRATION_ARCHITECTURE.md) · [ENG-05](../engineering/05_DATA_INGESTION_SPECIFICATION.md) |

## Context

Zerodha Kite Connect is the initial data provider, but SaaS requires a licensed vendor and future users may use other brokers (Upstox is listed as planned in the UI). Hard-coding Kite across the system would make these changes expensive and risky.

## Decision

Define a **`MarketDataProvider`** interface in the Python engine (instruments, daily candles, index candles, capabilities) and a **`BrokerConnector`** interface in Laravel (connect flow only). Kite is one adapter in each. Provider-specific fields and SDKs are confined to `providers/<name>/` and `Connectors/<Name>/`; the rest of the system uses normalised types and internal instrument IDs (ISIN-based).

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Use Kite types directly everywhere | Fastest initially; locks the schema and logic to one provider. |
| Third-party market-data aggregator SDK | Adds a dependency without solving licensing. |

## Consequences

+ Adding DEMO, licensed vendor or another broker is additive.
+ Errors normalised (auth expired, rate limited, unavailable, data error).
− Slight upfront design cost; capabilities differences (adjusted prices, delisted coverage) must be modelled explicitly.

## Status

Accepted on 2026-11-15. Superseding requires a new ADR referencing this one.
