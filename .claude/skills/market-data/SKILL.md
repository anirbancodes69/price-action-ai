---
name: market-data
description: Market-data engineering workflow for PriceAction AI - the MarketDataProvider abstraction, DEMO and Zerodha Kite Connect adapters, instrument master sync, universe membership, daily candle and backfill ingestion, candle normalisation, duplicate and missing-session detection, NSE market calendar and holidays, corporate-action adjustment, data-quality issues, data modes (DEMO / PERSONAL / LICENSED) and provider licensing limits. Use when working on python-engine/app/providers, app/ingestion, market-data tables (instruments, candles, universes, market_calendar, ingestion_runs, data_quality_issues, corporate_actions), demo data seeders, or anything that fetches, stores or serves candles.
---

# Market data

Keeps every candle trustworthy, attributable to a data source, and legally usable. Authority: [ADR-007](../../../docs/adr/ADR-007-MARKET-DATA-PROVIDER-ABSTRACTION.md), [ADR-011](../../../docs/adr/ADR-011-DATA-MODES-AND-TENANT-ISOLATION.md), [ARC-08 §2–§4](../../../docs/architecture/08_INTEGRATION_ARCHITECTURE.md), [ENG-05](../../../docs/engineering/05_DATA_INGESTION_SPECIFICATION.md), [ARC-03 §6](../../../docs/architecture/03_DATABASE_DESIGN.md#6-market-data).

> Current state: the market-data **tables** exist (ARC-03 §6, migrated in PR #14). There is **no provider, ingestion job or seeder code** yet. The DEMO seeder is T-102 (M1). Providers and ingestion are M2, and Kite verification is blocked on OQ-INT-01/02 and OQ-SEC-01 (T-201). Every Kite limit in ARC-08 §4 is an unverified placeholder.

## Required context

1. CURRENT.md and the M2 section of [ENG-01](../../../docs/engineering/01_IMPLEMENTATION_ROADMAP.md) (or T-102 in TASKS.md for demo seeding).
2. ARC-08 §2 data modes and §3 interface, ENG-05 for the step you touch (§4 demo, §5 pipeline, §6 normalisation, §7 quality checks, §8 corporate actions, §9 idempotency).
3. The ARC-03 §6 table definitions and the §2.1 "as migrated" deviations. For example, `candles.ingestion_run_id` is NOT NULL, so even seeders create an ingestion run first.
4. For anything touching Kite tokens, also use the `security-guardrails` skill.

## Workflow

1. **Stay behind the interface.** Provider SDKs and provider field names live only in `app/providers/<provider>/`. Everything else sees normalised `ProviderCandle` / `ProviderInstrument` and the normalised error types (ARC-08 §3).
2. **Normalise exactly as ENG-05 §6 says:** IST trade date, `Decimal` prices quantised to 0.01, integer volume, and provider token → `instrument_id` via the provider ref valid on that date. Store candles raw and apply adjustments at snapshot build.
3. **Run the ENG-05 §7 quality checks** and record them as `data_quality_issues`, never as silent fixes: OHLC validity, duplicates (keep last + `DUPLICATE`), missing sessions against `market_calendar`, candles on non-trading days, price spikes, zero volume, stale data, corrections (`revision++`).
4. **Calendar first.** Skip non-trading days using `market_calendar`; never infer trading days from weekdays alone.
5. **Idempotency.** Upsert by the candle PK; at most one active run per `(data_source, kind, trade_date)`; serialise backfill and daily runs per source (ENG-05 §9).
6. **Test with recorded fixtures only.** Provider adapters are tested with recorded HTTP fixtures (respx) with tokens scrubbed. Never make live calls in CI, and never commit real provider data (ENG-07 §4, licensing).

## Hard rules

| Rule | Source |
|---|---|
| All market data flows through `MarketDataProvider`. No direct provider calls from Laravel, the frontend or domain code | ADR-007, CLAUDE.md §3 |
| Every candle, snapshot and analysis row carries `data_source_id`. The mode derives from it | ARC-08 §2 rule 1 |
| PERSONAL (Kite) data is visible only to the owning tenant: never in shared caches, shared AI summaries, bulk exports or other tenants' results | ARC-08 §2 rule 2, C-04 |
| DEMO data is flagged (`is_demo`, DEMO universe, separate instrument rows without ISIN) and is never presented as live | ENG-05 §4, C-03 |
| The DEMO generator is deterministic (seeded) and ported from `frontend/src/mocks/demo-series.ts`. The as-of date policy is OQ-ING-01: do not decide it silently | ENG-05 §4 |
| LICENSED or commercial redistribution needs a signed licence and legal review. Do not design features that redistribute PERSONAL data | C-05, OPS-05 |
| Engine-worker is the writer of instruments, candles, ingestion runs and quality issues. Laravel reads only | ARC-01 §6 |
| Historical candles are versioned by `revision`. Snapshots are immutable once built | ARC-03 §6.5, §7.2 |
| Universe membership is effective-dated. Never overwrite history with today's constituents | ENG-05 §3, TRD-06 §8 |
| Kite access tokens are fetched just in time, held in memory only, and never logged or put in job payloads | ARC-06 §5 |

## Validation

- Quality-check tests cover each ENG-05 §7 row, including holiday and duplicate cases.
- An idempotency test shows a rerun of the same range changes nothing.
- A DEMO data-mode test shows rows are flagged and separated from real instruments.
- Adapter tests run offline on fixtures, and a redaction test shows tokens do not appear in logs.

## Deliverables

- Code plus tests, real test output, and any provider assumption verified or still open, recorded in ARC-08 (with OQ-INT-* status).
- Documentation sync per the `docs-sync` skill (ARC-08, ENG-05, ARC-03 §2.1 if the schema deviates).
