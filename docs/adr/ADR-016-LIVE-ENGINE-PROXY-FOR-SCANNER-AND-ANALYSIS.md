# ADR-016: Live Engine Proxy for the Scanner and Analysis (Personal Mode)

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-18 |
| Deciders | Product owner |
| Version | 1.0 |
| Related | [ADR-004](ADR-004-MODULAR-MONOLITH.md) · [ADR-014](ADR-014-PERSONAL-INTRADAY-WORKSTATION.md) · [ADR-015](ADR-015-INTRADAY-TIME-AND-SNAPSHOT-MODEL.md) · [ARC-04](../architecture/04_API_SPECIFICATION.md) · [ARC-08 §5](../architecture/08_INTEGRATION_ARCHITECTURE.md#5-internal-engine-api-laravel--engine) |

## Context

[ARC-04](../architecture/04_API_SPECIFICATION.md) and `contracts/api/openapi.yaml` define `GET /api/v1/scanner` and `GET /api/v1/analysis/{symbol}` as reads of **persisted** analysis: a batch is analysed after each bar close, written to `analysis_batches`, `analysis_runs` and their child tables, and the API returns the latest completed batch (`409 NO_ANALYSIS_AVAILABLE` when there is none, `meta.batch`, `analysis_run_id`). That model was designed for a many-user product where analysis is computed once and read many times.

Since [ADR-014](ADR-014-PERSONAL-INTRADAY-WORKSTATION.md) the product is a single-owner workstation over about 50 symbols. The engine now exposes `POST /internal/v1/scan` and `POST /internal/v1/analysis` (T-I79, T-I80): they analyse stored bars on demand in well under a second for the whole universe and size the plans with the caller's account state. Persisting batches would need a write path in the engine (analysis runs, swing points, events, zones, setups: ARC-03 §7, append-only with immutability triggers) before the API could return anything.

## Decision

1. In personal mode Laravel serves the scanner and the per-symbol analysis by **calling the engine live** on each request (service-token authenticated, `/internal/v1`), and maps the engine response to the API shape. Nothing is persisted for these two reads.
2. The public contract is amended accordingly (T-I87): `analysis_run_id` is nullable (null in live mode), `meta.batch` is omitted, `409 NO_ANALYSIS_AVAILABLE` is replaced by `503 ENGINE_UNAVAILABLE` / `404 NO_BARS_FOR_SYMBOL`, and `meta` always carries `data_mode`, `as_of` and `next_bar_close`.
3. The frontend still talks only to Laravel. The engine stays internal (ADR-004, C-01).
4. Persisted analysis (ARC-03 §7) is **deferred, not removed**. It is required again for: history of past signals, audit of what was shown when, backtest comparison with live signals, and any multi-user mode. Adding it later means the engine writes the runs and Laravel reads them for the same endpoints; the response shapes do not change.

## Alternatives considered

| Option | Why not now |
|---|---|
| Persist analysis batches in the engine first, Laravel reads them (the current contract) | About two extra batches of engine work (writer, idempotency, immutability, batch lifecycle) before any API response exists. The extra properties (history, audit) are not needed to use the tool today. |
| Frontend calls the engine directly | Violates API-first and the security boundary (ARC-06); the engine is not exposed. |

## Consequences

- Responses always reflect the latest closed bar; there is no stale batch. A request costs one scan of the universe, which is acceptable for one user; the endpoint is rate-limited (ARC-04 §2.8) and the engine call has a timeout.
- No history of what the scanner showed. The paper and actual trade tables remain the record of what was acted on.
- `analysis_run_id` is not available, so features that link to a run (explanations, setup detail by id) wait for persistence. LLM explanations are already deferred (ADR-014).
- Migration: none (no schema change). Contract change: the amendments above, with `contracts/` and ARC-04 updated in the same change.
