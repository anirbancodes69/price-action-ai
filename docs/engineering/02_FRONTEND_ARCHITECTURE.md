# Frontend Architecture

| Field | Value |
|---|---|
| Document ID | ENG-02 |
| Version | 0.1.0 |
| Status | Reflects implemented code (2026-11-15) + integration plan |
| Owner | Frontend Lead |
| Last updated | 2026-11-15 |
| Related | [PRD-07 UI/UX](../product/07_UI_UX_SPECIFICATION.md) · [ARC-04 API](../architecture/04_API_SPECIFICATION.md) · [ADR-001](../adr/ADR-001-FRONTEND-ARCHITECTURE.md) · `frontend/README.md` |

## 1. Purpose

Documents the actual Next.js frontend structure, its data boundary, and the plan for connecting it to the Laravel API without redesigning screens. Contains the authoritative **route → feature → API → entity mapping** (§8) and the **discrepancy register** (§9).

## 2. Stack (existing)

Next.js 16.4.6 (App Router, `cacheComponents`, `partialPrefetching`, standalone output), React 19.3, TypeScript strict, Tailwind CSS 4.3 via `@tailwindcss/turbopack`, Lightweight Charts 5.3, lucide-react, clsx, tailwind-merge. ESLint 9 with `eslint-config-next`. No test framework yet. See `frontend/AGENTS.md`: Next.js 16 conventions differ from older versions — consult `node_modules/next/dist/docs/` before framework-level changes.

## 3. Directory structure (existing)

```
frontend/
  Dockerfile            multi-stage, standalone runtime, HEALTHCHECK GET /login
  Dockerfile.dev        hot reload (bind mount, WATCHPACK_POLLING)
  next.config.ts        redirects: / → /login, /analysis → /analysis/RELIANCE
  src/
    app/                routes only — thin server components calling `data` and rendering a feature view
      (auth)/           login, register, forgot-password (split-screen layout)
      (app)/            authenticated shell: dashboard, market-scanner, analysis/[symbol], watchlists,
                        trade-plans, portfolio, journal, backtesting, settings; loading.tsx
      onboarding/       multi-step onboarding
      layout.tsx        fonts, ThemeScript, ToastProvider; not-found.tsx
    features/<area>/    page compositions + feature-local state
    components/         ui · layout · data · trading · charts
    lib/
      data/             DataSource interface (source.ts) + mock adapter (mock-source.ts) + active export (index.ts)
      labels.ts         enum → label/tone/description
      format.ts         en-IN / Asia/Kolkata formatting
      navigation.ts     nav groups, breadcrumbs, DEFAULT_ANALYSIS_SYMBOL
      chart/            chart theme from CSS tokens, timeframe aggregation (daily → weekly/monthly)
    hooks/              useSort, usePersistentState (localStorage), useMarketSession (IST clock)
    types/              domain types (market, analysis, trading, user)
    mocks/              deterministic sample universe, series generator, demo analysis heuristic, trading mocks
    styles/tokens.css   design tokens
```

## 4. Rendering and data loading

- Pages under `app/` are **server components** that `await data.getX()` and pass plain props to `"use client"` feature views. Example: `app/(app)/analysis/[symbol]/page.tsx` uses `generateStaticParams` over demo symbols and `notFound()` for unknown symbols.
- `(app)/layout.tsx` loads user, notifications, stocks (for search) and watchlists once for the shell.
- Client state: React state per feature; `WatchlistProvider` (context) for session watchlists; `usePersistentState` for theme and sidebar only.

When the HTTP adapter arrives, `generateStaticParams` for analysis must be removed (dynamic, user-specific data) and user-specific fetches must opt out of caching.

## 5. Data boundary

`DataSource` (`src/lib/data/source.ts`) is the only way pages obtain data:

```ts
interface DataSource {
  readonly kind: "sample" | "live"; readonly asOf: string;
  getIndices(); getStocks(); getScannerRows(); getAnalysis(symbol); getAnalysisSymbols();
  getDashboardSummary(); getActivity(); getTriggers();
  getWatchlists(); getTradePlans(); getHoldings(); getExecutedOrders();
  getPortfolioSummary(); getAllocation(); getJournal(); getBacktestStrategies();
  getPlaceholderEquityCurve(); getCurrentUser(); getNotifications();
}
```

Integration plan (M7):

1. Add `src/lib/data/http-source.ts` implementing the read methods via `/api/v1` (server-side fetch forwarding cookies; see [ARC-04 §2.2](../architecture/04_API_SPECIFICATION.md#22-authentication)).
2. Add a **mutations client** (`src/lib/api/`) for writes (plans, watchlists, settings, onboarding, journal, backtests, integrations) — the current interface is read-only; mutations today are local state + toasts.
3. Generate API types from `contracts/api/openapi.yaml` into `src/lib/api/schema.ts`; map API schemas to existing view types in `src/lib/data/mappers/` so components stay unchanged (enum mapping per [TRD-04 §12](../trading/04_SETUP_DETECTION_RULES.md#12-frontend-vocabulary-reconciliation); price strings → numbers for display only).
4. Replace global `DataSource.kind` with per-response `meta.data_mode`; render `SampleDataBadge` when `DEMO`.
5. Select adapter with `NEXT_PUBLIC_DATA_SOURCE=mock|http` (server-only env preferred: `DATA_SOURCE`), keeping the mock adapter for Storybook-style development and frontend tests.
6. Remove `getPlaceholderEquityCurve` once backtest results exist.

## 6. State management, forms, errors

| Concern | Current | Target |
|---|---|---|
| Server data | Server components + props | Same; `router.refresh()` after mutations; no client cache library required initially (revisit TanStack Query if polling grows) |
| Polling (jobs) | — | Small `usePoll(jobId)` hook against `/api/v1/jobs/{id}` |
| Forms | Controlled inputs + local validators (`features/auth/validation.ts`, inline checks) | Same pattern; map API 422 `field_errors` onto inputs |
| Toasts | `ToastProvider` | Same; show `request_id` on errors |
| Errors | `not-found.tsx` only | Add `error.tsx` per route group; typed `ApiError` from adapter |
| Auth guard | None | Next.js request interception (middleware/`proxy` per Next 16 docs) calling `/api/v1/me`; redirect rules in PRD-05 §7 |

## 7. Charts

`components/charts/price-chart.tsx` renders Lightweight Charts with custom primitives (`primitives.ts`) for zones and BOS/CHoCH segments; theme reads CSS tokens (`lib/chart/theme.ts`); weekly/monthly aggregation in `lib/chart/aggregate.ts` (display only). Required additions: unconfirmed-bar marker, wick-breach markers, dashed reference levels for SHORT setups ([PRD-07 §7](../product/07_UI_UX_SPECIFICATION.md#7-chart-annotation-rules)).

## 8. Route → feature → API → entity mapping

| Route | Screen | Features | Required API (ARC-04) | DB entities (ARC-03) | Current status |
|---|---|---|---|---|---|
| `/` | Redirect | F-01 | A9 | users | Static redirect to `/login` |
| `/login` | Login | F-01 | A1, A3, A9 | users, audit_logs | Mock (any valid-format credentials) |
| `/register` | Register | F-01, F-04 | A1, A2 | tenants, users, tenant_memberships, user_profiles, onboarding_progress, subscription_entitlements, paper_accounts | Mock |
| `/forgot-password` | Forgot password | F-02 | A5 | password_reset_tokens | Mock |
| `/reset-password` | Reset password (**missing**) | F-02 | A6 | password_reset_tokens | Not built |
| `/onboarding` | Onboarding | F-04, F-05, F-06, F-07, F-20 | O1–O4, I1, P5 | onboarding_progress, user_profiles, trading_preferences, data_source_selections, risk_profiles, provider_connections | Mock (local state) |
| `/dashboard` | Dashboard | F-16, F-15, F-19, F-28, F-31 | N3, N4, M6, M7, W1, N1 | analysis_batches, analysis_runs, detected_setups, trade_plans, watchlists, notifications, candles (indices) | Mock |
| `/market-scanner` | Scanner | F-15, F-34 | N1, N2 | analysis_batches, analysis_runs, detected_setups, instruments, universe_memberships | Mock (client filters) |
| `/analysis` | Redirect | — | — | — | Redirect to `/analysis/RELIANCE` |
| `/analysis/[symbol]` | Stock analysis | F-17, F-10–F-14, F-19, F-21, F-27 | N5, N6, N13–N15, W5/W6, R (8.1), T2 | analysis_runs, candle_snapshots, swing_points, structure_events, price_zones, liquidity_events, detected_setups, ai_explanations, ruleset_versions | Mock (demo heuristic) |
| `/watchlists` | Watchlists | F-19 | W1–W6, N1 (`watchlist=`) | watchlists, watchlist_items | Mock (session store) |
| `/trade-plans` | Trade plans | F-21, F-23 | T1–T5, X8 | trade_plans, actual_trades | Mock |
| `/portfolio` | Portfolio | F-24, F-22, F-23 | X1–X10 | paper_accounts, paper_trades, actual_trades, actual_trade_fills | Mock (single "holdings" book) |
| `/journal` | Journal | F-25 | J1–J4 | journal_entries, paper_trades, actual_trades | Mock |
| `/backtesting` | Backtesting | F-26 | B1–B6, N16 | backtest_runs, backtest_trades, ruleset_versions | Mock (engine not connected; placeholder curve) |
| `/settings` | Settings | F-29, F-06, F-07, F-20, F-28, F-30 | A10–A12, P1–P7, I1–I4, M8–M10 | user_profiles, trading_preferences, risk_profiles, data_sources, data_source_selections, provider_connections, ingestion_runs | Mock (session-only saves) |
| shell (all `(app)`) | Top nav, search, notifications | F-18, F-28, F-31 | A9, M1, Z1–Z3, M7 | users, instruments, notifications, market_calendar | Mock |
| `*` | Not found | — | — | — | Implemented |

## 9. Discrepancy register

Differences between the current frontend and the specified product. None is fixed in this documentation phase; each is assigned to a milestone. "Adapter" means it can be absorbed in the HTTP mapper without UI change.

| ID | Area | Current frontend | Specification | Resolution | Milestone |
|---|---|---|---|---|---|
| D-01 | Setup types | `breakout-retest`, `pullback-to-support`, `range-breakout`, `breakdown-retest`, `trend-continuation`, `range-bound` | 4 canonical types (TRD-04) | Update `SetupType` + `SETUP_TYPES` labels; mapping table TRD-04 §12 | M7 |
| D-02 | Setup status | No `expired`; `detected` | `FORMING`, …, `EXPIRED` | Add `expired`; rename label of `detected` → "Forming" | M7 |
| D-03 | Universe options | NIFTY 50/100/200/MIDCAP 150, "All NSE equities"; default NIFTY 100 | NIFTY 500 default; subsets only | Add NIFTY 500, remove All NSE, change default | M7 |
| D-04 | Types `Exchange`, `IndexMembership` | `BSE` allowed; index list lacks NIFTY 500 | NSE only; universes from API | Narrow types / use API universes | M7 |
| D-05 | Analysis logic | Demo zigzag (3% threshold) heuristic in `mocks/demo-analysis.ts` | Fractal pivots L=R=2 etc. (TRD-02) | Engine replaces; mock stays labelled demo heuristic for frontend-only development | M3–M7 |
| D-06 | Plan sizing | Quantity computed in `create-plan-dialog.tsx` from a ₹ risk input | Engine-computed from risk profile (%); API preview | Dialog calls `/risk/calculate`; risk input becomes % with profile default | M7 |
| D-07 | Plan statuses | `pending`, `entry-confirmed`, `active`, `completed`, `invalidated`, `cancelled` | `PENDING`, `TRIGGERED`, `FILLED`, `SKIPPED`, `INVALIDATED`, `EXPIRED`, `CANCELLED`; open/closed from linked trade | Map `active`/`completed` from `FILLED` + trade status; add tabs | M7 |
| D-08 | Trade records | `Holding`, `ExecutedOrder` (comment: "broker-confirmed in future phases") | Separate paper trades vs manual actual trades; no broker sync in MVP | Add paper trade types; portfolio book toggle; actual trade form | M9 |
| D-09 | Journal | No paper/actual distinction | `trade_kind` filter | Add filter | M9 |
| D-10 | Analysis provenance | `StockAnalysis` lacks run id, ruleset version, snapshot id; global `DataSource.kind` | Per-response `data_mode`, run/ruleset ids | Extend types (additive) | M7 |
| D-11 | Auth | Mock sign-in; no guard; no reset page; logout toast | Real auth + guard + reset | Implement | M7 |
| D-12 | Onboarding | Local state; Zerodha disabled "Placeholder" | Persisted per step; connect flow | Implement | M7 |
| D-13 | Risk defaults | Settings: 6 positions, 2% heat; onboarding: 5 positions | 5 positions, 5% heat, 25% max position (OQ-RM-04) | Read from API; confirm values | M6/M7 |
| D-14 | Backtest strategies | Breakout & Retest, Pullback to Support, Range Breakout | 4 canonical setup types | Use `B1` strategies endpoint | M9 |
| D-15 | Market session | Clock only, ignores holidays | `market_calendar` API | Use M7 endpoint | M7 |
| D-16 | Data sources in settings | "Sample data", "NSE end-of-day (coming soon)"; Upstox "Planned" | DEMO, PERSONAL (Zerodha), LICENSED (future) | Rename rows; keep Upstox as future | M7 |
| D-17 | Quality factors | Free-form `QualityFactor[]` | Five fixed PAQS components | Adapter maps components | M7 |
| D-18 | Levels for NO TRADE | `levels` always present | `levels` null when not applicable | Make optional in types; UI hides | M7 |
| D-19 | Chart events | `breakout`/`retest`/`breakdown` | `BOS`/`CHOCH`/`WICK_BREACH` + setup stage markers | Adapter + new marker types | M7 |
| D-20 | Error handling | No `error.tsx` | Route error boundaries | Add | M7 |
| D-21 | Tooling | ~~No tests, no `typecheck` script~~ **Resolved in M0:** Vitest 5 (`npm test`), `npm run typecheck` | Vitest, `tsc --noEmit` in CI | Done | M0 |
| D-22 | Scanner exchange filter | NSE/BSE filter | Remove (NSE only) | Remove | M7 |
| D-23 | Plan sizing input | Risk budget ₹5,000 default in dialog | Risk % from profile (₹ shown as derived) | See D-06 | M7 |
| D-24 | Prices | `number` in types | Strings in API | Adapter parses | M7 |

## 10. Testing (frontend)

Unit (Vitest): formatters, labels completeness vs enums, mappers, validators, `applyFilters`, journal stats (until server-side). Component (Testing Library): SignalBadge accessibility labels, plan dialog error rendering. E2E (Playwright, M7): login → onboarding (demo) → analysis → create plan (against a seeded backend in Docker). See [ENG-07](07_TESTING_STRATEGY.md).
