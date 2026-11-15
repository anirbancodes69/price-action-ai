# ADR-003: Python as Quantitative Engine

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-15 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [ENG-04](../engineering/04_PYTHON_ENGINE_ARCHITECTURE.md) · [ARC-08 §5](../architecture/08_INTEGRATION_ARCHITECTURE.md) |

## Context

Market-structure detection, setup rules, risk sizing, backtesting and ingestion are numerical, CPU-bound and require extensive, property-based testing. They must be deterministic and isolated from web request handling.

## Decision

Implement the quantitative engine in **Python 3.13** as one codebase with two runtimes: a **FastAPI** internal service (sync analysis/risk endpoints, job submission) and **arq** workers (ingestion, analysis batches, backtests, paper EOD, LLM explanations). The pure domain library (`app/domain`) has no I/O.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Implement rules in PHP inside Laravel | Single language for backend, but weaker numerical ecosystem and testing tools; long backtests would compete with web workers. |
| Separate microservices per concern (ingestion, analysis, backtest) | Premature; one Python deployable with queues covers the needs. |
| Rust/Go engine | Faster, but slower iteration on rules during validation; can be revisited for hot paths later. |

## Consequences

+ numpy, Decimal, pytest, Hypothesis; quick iteration on rules; isolation of CPU work.
+ Internal API keeps Laravel decoupled from engine internals.
− Cross-language contracts must be kept in sync (contracts/engine JSON Schemas, CI checks).

## Status

Accepted on 2026-11-15. Superseding requires a new ADR referencing this one.
