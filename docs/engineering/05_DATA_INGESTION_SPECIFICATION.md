# Data Ingestion Specification

| Field | Value |
|---|---|
| Document ID | ENG-05 |
| Version | 0.1.0 |
| Status | Specification ready (provider limits to verify in M2) |
| Owner | Trading Engine Lead |
| Last updated | 2026-11-15 |
| Related | [ARC-08 Integration](../architecture/08_INTEGRATION_ARCHITECTURE.md) · [ARC-03 §6 Market data](../architecture/03_DATABASE_DESIGN.md#6-market-data) · [ARC-05 §3](../architecture/05_DATA_FLOW.md#3-broker-data-retrieval-and-normalisation) · [TRD-06 §3, §7–8](../trading/06_BACKTESTING_METHODOLOGY.md) |

## 1. Purpose

Defines how instruments, universe membership, daily candles and corporate actions are ingested, normalised, validated and stored, for each data source.

## 2. Job types

| Kind | Trigger | Scope |
|---|---|---|
| `INSTRUMENT_MASTER` | Daily before candles; on connect | Provider instrument list → `instruments`, `instrument_provider_refs`, `instrument_snapshots` |
| `UNIVERSE` | Manual/semi-annual (index reconstitution) + on demand | `universe_memberships` effective dating |
| `DAILY_CANDLES` | EOD pipeline (trading days) | Point-in-time NIFTY 500 + watchlist instruments + indices, window `[last − 5 trading days, d]` |
| `BACKFILL` | On connect; manual (API endpoint M8 in ARC-04) | Range per instrument up to configured years |
| `CORPORATE_ACTIONS` | Daily / manual | `corporate_actions` (source unresolved, OQ-BT-03) |

## 3. Universe management

- Initial NIFTY 500 list loaded from the index provider's published constituent file (manual download in M2; effective_from = load date). Historical membership requires a separate source (OQ-BT-01).
- Changes from reconstitution notices entered as effective-dated rows (`effective_to` on removals, new rows on additions) with `source_ref`.
- Subset universes (NIFTY 50/100/200/MIDCAP 150) are loaded the same way; all are subsets of NIFTY 500.

## 4. Demo data source

- Provider `DEMO` generates deterministic OHLCV using the algorithm ported from `frontend/src/mocks/demo-series.ts` (seeded RNG, templates breakout/pullback/range/breakdown) for the demo universe (`frontend/src/mocks/universe.ts`, ~50 instruments).
- Demo instruments are flagged `is_demo = true` and belong only to the `DEMO` universe; they never mix with real instrument rows even if symbols coincide (separate instrument rows, no ISIN).
- Demo candles end on a fixed "as of" date (currently `2026-11-13` in mocks) or roll forward daily — decision OQ-ING-01.

## 5. Daily pipeline sequencing

1. Check `market_calendar` — skip non-trading days.
2. For PERSONAL sources: verify connection `CONNECTED` and token not expired; otherwise mark run `FAILED` with `PROVIDER_AUTH_EXPIRED` and notify.
3. `INSTRUMENT_MASTER` (if not run today).
4. `DAILY_CANDLES` with rate limiting (ARC-08 §4.5).
5. Completeness check: every universe instrument has a candle for `d` (unless suspended) → else `MISSING_SESSION` issues; run status `PARTIAL` if > 0 and ≤ 5% missing, `FAILED` if > 5% (thresholds are assumptions).
6. On `COMPLETED`/`PARTIAL`: enqueue `analyse_batch`.

## 6. Normalisation

| Field | Rule |
|---|---|
| Date | Provider timestamp converted to Asia/Kolkata and truncated to date = trade date |
| Prices | Decimal, quantised to 0.01 (`ROUND_HALF_UP`); must be > 0 |
| Volume | Integer ≥ 0 |
| Instrument | Provider token → `instrument_provider_refs` valid on date → `instrument_id`; unknown token ⇒ `PROVIDER_GAP` issue and skip |
| Basis | Stored raw; adjustment applied at snapshot build (if provider candles are already adjusted, provider capability flag `adjusted=true` skips adjustment — OQ-INT-02) |

## 7. Validation and data-quality checks

| Check | Rule | Action |
|---|---|---|
| OHLC consistency | `low ≤ min(open, close) ≤ max(open, close) ≤ high` | Reject row, `OHLC_INVALID` ERROR |
| Duplicate | Same instrument + date twice in response | Keep last, `DUPLICATE` INFO |
| Missing session | Trading day in calendar with no candle | `MISSING_SESSION` WARN |
| Non-trading-day candle | Candle on a holiday/weekend | Reject, `PROVIDER_GAP` WARN |
| Price spike | `|close/prev_close − 1| > 20%` without corporate action on that date | Keep, `PRICE_SPIKE` WARN (review) — note NSE circuit bands can allow such moves |
| Zero volume | `volume = 0` on a trading day | Keep, `ZERO_VOLUME` INFO |
| Stale | Identical OHLCV to previous day for ≥ 3 days | `STALE_DATA` WARN |
| Correction | Existing candle differs from fetched one | Update, `revision++`, logged with old/new values in run `error_summary` (first 50) |

Analysis treats candles with open `ERROR` issues as absent; snapshots record a `quality_flags` list in their metadata.

## 8. Corporate actions

Applied at snapshot build: back-adjust prices before each split/bonus ex-date by `ratio_from/ratio_to`; volumes multiplied inversely. Dividends not adjusted (TRD-06 §7). Corporate action source unresolved (OQ-BT-03); until resolved, `PRICE_SPIKE` issues near known split dates are reviewed manually and actions entered via an admin seeder.

## 9. Idempotency and concurrency

- One active run per `(data_source, kind, trade_date)` (partial unique index, ARC-03 §6.7).
- Upserts keyed by candle PK; reruns are safe.
- Backfill and daily runs for the same source are serialised with a Redis lock per data source.

## 10. Observability

Metrics: `ingestion_run_duration_seconds`, `ingestion_instruments_failed_total`, `provider_requests_total{status}`, `provider_rate_limited_total`, `data_quality_issues_total{type}`. Alerts in [OPS-03](../operations/03_MONITORING_AND_OBSERVABILITY.md).

## 11. Open questions

| ID | Question |
|---|---|
| OQ-ING-01 | Should demo data roll forward daily (looks alive, but might be mistaken for live) or stay fixed at a past as-of date (clearer)? Proposed: fixed. |
| OQ-ING-02 | Exact thresholds for PARTIAL vs FAILED runs. |

## 12. Intraday ingestion (ADR-015)

For the intraday direction ([ADR-014](../adr/ADR-014-PERSONAL-INTRADAY-WORKSTATION.md), [ADR-015](../adr/ADR-015-INTRADAY-TIME-AND-SNAPSHOT-MODEL.md)); implemented in milestone I2. Sections 5–9 above describe the daily pipeline, which stays for daily context bars (previous-day levels).

**Process.** One long-running asyncio process in the engine image (a Compose service, not a separate service codebase) runs only while `market_calendar` says the session is open.

1. **Bar-close fetch.** At each 5-minute close plus a settle delay (initial value 20 s, HYPOTHESIS), fetch the just-completed 5m bar for every NIFTY 50 instrument through the provider's historical-bars API, and the 15m bar at each 15-minute close. Forming bars are never requested or stored. Write with an `INTRADAY_BARS` ingestion run per (timeframe, bar close).
2. **Analysis trigger.** When a 5m close is complete for the universe (or the per-bar deadline passes), enqueue one analysis batch for that `as_of_ts`.
3. **Current prices.** Keep the last traded price of open positions and the watchlist in Redis (key per instrument, short TTL) from the provider's quote or streaming API. Current prices are never written to `candles` and never used by analysis; they only feed live P&L and the "distance to level" display.
4. **Session end.** After the close, re-fetch the whole session's 5m and 15m bars and reconcile: insert missing bars, compare stored bars, and correct changed ones (increment `revision`, copy the old values to `candle_revisions`). Then fetch the daily bar as today.

**Quality checks (intraday).**

| Check | Rule | Action |
|---|---|---|
| Completeness | A normal session has 75 5m and 25 15m bars per active instrument (special sessions per calendar) | `MISSING_BAR` issue; the analysis for that bar uses what exists and marks the run inputs incomplete |
| Late bar | Bar not available by the per-bar deadline | Retry with backoff until the next bar close, then `LATE_BAR` issue |
| Alignment | `bar_start` on the 09:15 grid for the timeframe | Reject the bar, `MISALIGNED_BAR` issue |
| Consistency | 15m bar equals the aggregate of its three 5m bars (OHLC exactly, volume within tolerance) | `AGGREGATE_MISMATCH` issue; provider's 15m bar is kept |
| OHLC validity | As for daily (§7) | Reject the bar |
| Outside session | `bar_start` before the open or at/after the close | Reject the bar |

**Rate limits and recovery.** About 50 requests per 5m close (plus 50 per 15m close) are spread to respect the provider's limit (to verify, OQ-INT-01). A provider outage marks runs `PARTIAL`/`FAILED` and the session-end reconciliation backfills. Restarting the process resumes from the last stored bar per instrument.

**Demo data.** The DEMO source gets a deterministic intraday generator (session-shaped 5m bars aggregated to 15m) with the same seeded-random approach as the daily one (`backend/database/seeders/Demo/`), flagged `is_demo`.

