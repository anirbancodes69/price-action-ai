# ADR-010: Manual Trade Execution in MVP

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-15 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [TRD-07](../trading/07_PAPER_TRADING_SPECIFICATION.md) · [PRD-02 BRQ-002](../product/02_BRD.md) · [OPS-05](../operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md) |

## Context

Automated order placement through broker APIs brings regulatory requirements, operational risk (duplicate/erroneous orders), security risk (trading-capable tokens) and scope expansion. The MVP's value is analysis, planning, paper trading and journaling.

## Decision

The MVP **does not place, modify or cancel broker orders**. Users execute on their broker's platform themselves and may record actual executions manually (`actual_trades` + fills), optionally linked to a plan. Plans are proposals; paper trades are simulations. No API endpoint, job or UI control for order placement exists.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Order placement with confirmation | Convenient, but triggers regulatory and safety requirements beyond MVP. |
| GTT/alert creation at broker | Smaller step but still an order-related action; deferred. |
| Read-only broker sync of trades/holdings | Useful and lower risk; deferred to future scope (F-36). |

## Consequences

+ Lower regulatory and security exposure; smaller scope; tokens only need data access.
− Manual entry of actual trades is friction; journaling of actual trades depends on user discipline.

## Status

Accepted on 2026-11-15. Superseding requires a new ADR referencing this one.
