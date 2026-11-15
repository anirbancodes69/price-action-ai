# ADR-008: Deterministic, Versioned Trading Calculations

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-15 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [TRD-01](../trading/01_TRADING_METHODOLOGY.md) · [TRD-08](../trading/08_TRADING_ENGINE_VALIDATION.md) · [ENG-04](../engineering/04_PYTHON_ENGINE_ARCHITECTURE.md) |

## Context

Users must be able to trust and audit why a setup was flagged; backtests must be reproducible and free of look-ahead; rule changes must be measurable. Non-deterministic or opaque calculations (including ML or LLM-generated levels) undermine all three.

## Decision

All trading calculations — candle validation, pivots, structure, BOS/CHoCH, zones, liquidity, setups, levels, quality score, risk sizing, execution simulation — are **pure deterministic functions** in `python-engine/app/domain`, parameterised by an **immutable, versioned ruleset** (`pa-core x.y.z`). Every analysis references an **immutable candle snapshot** (content-hashed) and the ruleset version; outputs are hashed (`result_hash`) and checked nightly. Parameters are labelled hypotheses until validated by backtests.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Machine-learning signal models | Potentially adaptive, but opaque, hard to explain, prone to overfitting, and conflicts with the explainable price-action positioning. |
| Rules without versioning | Simpler, but past analyses become unreproducible and backtests incomparable. |
| Recompute analyses from current candles on read | Corrections would silently change history. |

## Consequences

+ Reproducibility, auditability, testability (TRD-08 catalogue as required CI).
+ Clear ruleset change management.
− Snapshot storage overhead; every behaviour change needs a version bump and golden-file updates.

## Status

Accepted on 2026-11-15. Superseding requires a new ADR referencing this one.
