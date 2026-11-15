# ADR-011: Demo, Personal and Licensed Data Modes with Tenant Isolation

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-15 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [ARC-08 §2](../architecture/08_INTEGRATION_ARCHITECTURE.md#2-data-modes) · [ARC-03 §5.5](../architecture/03_DATABASE_DESIGN.md) · [ARC-06 §4](../architecture/06_SECURITY_ARCHITECTURE.md#4-tenant-isolation) · [OPS-05 §3](../operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md#3-market-data-licensing-hard-gate) |

## Context

The product starts personal (owner's Zerodha data) but is designed for SaaS. Personal broker API data is not assumed to be redistributable; demo data must never be mistaken for live data; SaaS requires licensed data. These concerns must be structural, not conventions.

## Decision

Introduce **`data_sources`** with mode `DEMO` (synthetic, global), `PERSONAL` (tenant-scoped, tied to a provider connection) or `LICENSED` (global, entitlement-gated). Every candle, snapshot and analysis row references a data source; each tenant selects exactly one active source. PERSONAL data is never visible to other tenants, never used in shared caches or shared AI summaries, and never bulk-exported. Every market-data API response carries `meta.data_mode`; the UI badges DEMO. Tenant isolation is enforced by scoping, 404 on foreign IDs, tests, and RLS before SaaS. Licensed data and legal review are release gates for SaaS.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Single global market-data store | Simplest, but personal data would leak across tenants and violate likely terms. |
| Separate database per tenant | Strong isolation, heavy operations; unnecessary with scoping + RLS. |
| Flag demo data only in the UI | Fragile; backend could mix data. |

## Consequences

+ Licensing and honesty constraints enforced by schema and API.
+ Licensed data is ingested once and shared efficiently.
− Personal sources duplicate storage per tenant; queries must always include data-source filters.

## Status

Accepted on 2026-11-15. Superseding requires a new ADR referencing this one.
