# ADR-017: Trade Plans Without Stored Analysis Runs (Personal Mode)

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-19 |
| Deciders | Product owner |
| Version | 1.0 |
| Related | [ADR-010](ADR-010-MANUAL-TRADE-EXECUTION-MVP.md) · [ADR-014](ADR-014-PERSONAL-INTRADAY-WORKSTATION.md) · [ADR-016](ADR-016-LIVE-ENGINE-PROXY-FOR-SCANNER-AND-ANALYSIS.md) · [ARC-03 §8](../architecture/03_DATABASE_DESIGN.md) · [ARC-04 §8](../architecture/04_API_SPECIFICATION.md) |

## Context

[ADR-016](ADR-016-LIVE-ENGINE-PROXY-FOR-SCANNER-AND-ANALYSIS.md) serves the scanner and the analysis live from the engine and stores no analysis runs. `trade_plans.analysis_run_id` is `NOT NULL` ([ARC-03 §8](../architecture/03_DATABASE_DESIGN.md)), and ARC-04 T2 creates a plan from a stored run (`analysis_run_id`, `setup_id`, `ANALYSIS_STALE`). With no stored runs, no plan can be created, so the flow scan, analyse, plan, execute, journal stops at the plan.

## Decision

1. A trade plan may exist **without** a stored analysis run: `trade_plans.analysis_run_id` becomes nullable.
2. The plan carries its own record of what it was made from: `setup_type`, `paqs`, `as_of_ts` (end of the 5m bar analysed), `setup_key`, the engine's levels (`engine_*_price`), `ruleset_version_id` and `risk_profile_id`. These make the plan self-explaining and auditable without the run.
3. `POST /trade-plans` in personal mode takes `instrument` and optionally `setup_type`, not an `analysis_run_id`. With a setup type, Laravel analyses the instrument live through the engine and uses that setup's levels; without one, the plan is manual and needs all three levels. Quantity is always the engine's (`risk/position-size`); a client-supplied quantity is not accepted.
4. A plan is refused when the setup is not actionable (`SETUP_NOT_ACTIONABLE`), has ended (`SETUP_TERMINAL`) or its entry window has elapsed (`ENTRY_WINDOW_ELAPSED`). `ANALYSIS_STALE` does not apply, because the analysis is taken at request time.
5. Persisted analysis runs ([ADR-016](ADR-016-LIVE-ENGINE-PROXY-FOR-SCANNER-AND-ANALYSIS.md) decision 4) remain deferred, not removed. When they return, new plans fill `analysis_run_id` and the extra columns stay as a denormalised record.

## Alternatives considered

| Option | Why not now |
|---|---|
| Persist the run when a plan is created (engine write path with immutability triggers) | About two extra batches of engine work before any plan exists; the audit value is covered by the plan's own record for one owner. |
| Keep `analysis_run_id` required and invent a placeholder run | A fake run misrepresents what was analysed and breaks the immutability meaning of runs. |

## Consequences

- Migration `2026_11_19_000002`: `analysis_run_id` nullable; new nullable `setup_type`, `paqs`, `as_of_ts`. Existing rows are unaffected (none exist in personal mode).
- Contract: `TradePlan.analysis_run_id` and `setup_id` nullable; `TradePlanCreate` takes `setup_type` and no longer requires `analysis_run_id` in personal mode. ARC-04 T2 and ARC-03 §8 are updated in the same change.
- A plan cannot be traced to a stored run, only to its own recorded setup, levels and bar time.
- Status transitions by bar close (triggered, invalidated, expired) are the engine's and are not built yet: a plan stays `PENDING` until the owner cancels it or its entry cutoff passes. The cutoff rule is a pure time rule and runs in Laravel (`plans:expire`, T-I130): `PENDING` becomes `EXPIRED`, an unfilled `TRIGGERED` plan `SKIPPED`.
