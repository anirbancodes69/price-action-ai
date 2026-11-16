# ADR-015: Intraday Time Model and Snapshots by Reference

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-17 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [ADR-014](ADR-014-PERSONAL-INTRADAY-WORKSTATION.md) · [ADR-008](ADR-008-DETERMINISTIC-TRADING-ENGINE.md) · [ADR-005](ADR-005-POSTGRESQL-DATABASE.md) · [ARC-03 §2.2](../architecture/03_DATABASE_DESIGN.md#22-intraday-time-model-adr-015-implemented-in-i1) · [ARC-04 §2.9](../architecture/04_API_SPECIFICATION.md#29-intraday-time-conventions-adr-015) · [ENG-05 §12](../engineering/05_DATA_INGESTION_SPECIFICATION.md#12-intraday-ingestion-adr-015) |

## Context

The migrated schema (M1) identifies every bar by a date: `candles` has primary key `(data_source_id, instrument_id, timeframe, trade_date)` and `CHECK (timeframe IN ('1D'))`. Analysis, paper and backtest rows carry dates (`analysis_runs.as_of_date`, `swing_points.confirmed_at_date`, `paper_trades.entry_date`, `backtest_trades.signal_date`). ADR-014 makes 15-minute and 5-minute bars the primary inputs, so a date can no longer identify a bar or a moment.

C-08 and ADR-008 require every analysis to reference an **immutable candle snapshot**. ARC-03 §7.2 implements that by copying the bars into `candle_snapshots.payload`. That suits one daily run per instrument. Intraday, the plan is a run at every 5-minute close for about 50 instruments (about 3,750 runs per session), each needing 15m, 5m and daily inputs, so copying the bars each time would store the same bars thousands of times.

## Decision

1. **Bars are identified by their start time.** `candles` gains `bar_start timestamptz` (stored in UTC, shown in IST) and keeps `trade_date` as the IST session date of the bar. The primary key becomes `(data_source_id, instrument_id, timeframe, bar_start)`. Timeframes are `1m`, `5m`, `15m` and `1D`; `1m` is allowed by the schema but not ingested in the MVP. A bar's end is `bar_start + interval` (for `1D`, the session close). Bars align to the NSE session open (09:15 IST), so a normal session has 75 five-minute and 25 fifteen-minute bars; the last bar of a timeframe ends at the session close.
2. **Only completed bars are stored.** A bar is written only after its end time plus a settle delay, and only as the provider's completed bar. Forming bars are never stored or analysed (TRD-01 MP-03). Corrections increase `revision` as today.
3. **Provider-native timeframes.** In the MVP, 5m, 15m and daily bars are fetched from the provider as such, not aggregated from 1-minute bars. Aggregating 5m into 15m is used only as a consistency check.
4. **Revision history.** Before a stored bar is corrected, its previous values are copied to a new append-only `candle_revisions` table. Any past input set can therefore be rebuilt exactly.
5. **Snapshots by reference.** `candle_snapshots` no longer stores a payload. A snapshot records `(data_source_id, instrument_id, timeframe, from_bar_start, to_bar_start, bar_count, max_revision, content_hash)`. `content_hash` is the sha256 of the canonical serialisation of the referenced bars at the revisions used, so it proves the inputs. It is still immutable (C-08 unchanged in meaning). Rebuilding a snapshot reads `candles`, plus `candle_revisions` when a bar was corrected later.
6. **One run, several inputs.** A new link table `analysis_run_inputs (analysis_run_id, role, candle_snapshot_id)` replaces the single `analysis_runs.candle_snapshot_id`. Roles are `PRIMARY_5M`, `CONTEXT_15M` and `DAILY_CONTEXT`. `analysis_runs` gains `as_of_ts timestamptz` (the end of the last 5m bar used); `as_of_date` remains the session date.
7. **Timestamps for derived objects and trades.** Derived rows carry the bar timestamps they come from (`swing_points.bar_start` and `confirmed_at_bar_start`, structure events, zones, setups). Trading tables gain timestamps beside their dates: plans (`triggered_at`), paper trades (`entry_at`, `exit_at`), actual fills (already timestamps), backtest trades (`signal_at`, `entry_at`, `exit_at`). Integrity checks move to timestamps: entry after signal (next bar at the earliest), and confirmation at or after the bar.
8. **Retention.** Intraday analysis runs that no plan, trade or journal entry references are deleted after a configurable number of days (OPS-04 to set the default). Referenced runs and their snapshots are kept.
9. **No partitioning yet.** NIFTY 50 at 5m and 15m adds about 5,000 bars per session (about 1.3 million per year). Monthly partitioning of `candles` by `bar_start` is deferred until 1-minute bars are ingested.
10. **Migration path.** Expand, migrate, contract (ARC-03 §12): add columns and tables, backfill the daily rows (`bar_start` = session open of `trade_date`), switch the keys and checks, then drop `candle_snapshots.payload` and `analysis_runs.candle_snapshot_id`. No production data exists yet, so this is done in I1 on development databases only.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Keep payload snapshots | Stores the same bars thousands of times per session; storage and write volume grow with the number of runs, not with the data. |
| Make `candles` fully immutable (a new row per revision) | Every read must pick the latest revision; a separate history table keeps the common read simple. |
| Store only 1-minute bars and aggregate everything | More data and more provider load for no MVP benefit; provider-native 5m and 15m are enough. |
| Use a time-series database | A new component for one user and about 50 symbols; PostgreSQL is sufficient (ADR-005). |
| Keep dates and add a bar sequence number | A sequence number has no meaning across sources or corrections; timestamps are unambiguous. |

## Consequences

+ Reproducibility (C-08, ADR-008) is kept, with storage proportional to the market data rather than to the number of runs.
+ One run can use 15m, 5m and daily inputs, each proven by its own content hash.
− Rebuilding a snapshot costs a range query plus a revision lookup instead of reading one payload.
− The I1 migration touches most market-data, analysis and trading tables; `python-engine/app/db/tables.py`, the engine contracts and the OpenAPI file change with it. The schema-diff and contract checks enforce that.
− The ingestion pipeline must know the session calendar to judge completeness (ENG-05 §12).

## Status

Accepted on 2026-11-17. Supersedes the payload snapshot design of ARC-03 §7.2 and the date-only time model of ARC-03 §6.5 and §7–§8. Implemented in milestone I1 (task T-I09).
