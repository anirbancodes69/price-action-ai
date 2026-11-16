# Frontend Architecture

| Field | Value |
|---|---|
| Document ID | ENG-02 |
| Version | 0.2.0 |
| Status | Reflects implemented code (2026-11-16) + integration plan |
| Owner | Frontend Lead |
| Last updated | 2026-11-16 |
| Related | [PRD-07 UI/UX](../product/07_UI_UX_SPECIFICATION.md) · [ARC-04 API](../architecture/04_API_SPECIFICATION.md) · [ADR-001](../adr/ADR-001-FRONTEND-ARCHITECTURE.md) · [ADR-013](../adr/ADR-013-DESIGN-STANDARDS.md) · [design-standards](../design-standards.md) · `frontend/README.md` |

## 1. Purpose

Documents the actual Next.js frontend structure, its data boundary, and the plan for connecting it to the Laravel API without redesigning screens. Contains the authoritative **route → feature → API → entity mapping** (§8) and the **discrepancy register** (§9).

## 2. Stack (existing)

Next.js 16.4.6 (App Router, `cacheComponents`, `partialPrefetching`, standalone output), React 19.3, TypeScript strict, Tailwind CSS 4.3 via `@tailwindcss/turbopack`, Lightweight Charts 5.3, lucide-react, clsx, tailwind-merge; fonts Archivo, Inter and JetBrains Mono via `next/font`. ESLint 10 with `eslint-config-next`; Vitest 5. Design system: §11. See `frontend/AGENTS.md`: Next.js 16 conventions differ from older versions — consult `node_modules/next/dist/docs/` before framework-level changes.

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
      colors.ts         semantic tone classes and chart slots (§11.1)
      format.ts         en-IN / Asia/Kolkata formatting
      navigation.ts     nav groups, breadcrumbs, DEFAULT_ANALYSIS_SYMBOL
      chart/            chart theme from CSS tokens, timeframe aggregation (daily → weekly/monthly)
    hooks/              useSort, usePersistentState (localStorage), useMarketSession (IST clock)
    types/              domain types (market, analysis, trading, user)
    mocks/              deterministic sample universe, series generator, demo analysis heuristic, trading mocks
    styles/tokens.css   design tokens (OKLCH, light + dark; §11)
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
3. Generate API types from `contracts/api/openapi.yaml` into `src/lib/api/schema.ts`; map API schemas to existing view types in `src/lib/data/mappers/` so components stay unchanged (enum mapping per [TRD-04 §13](../trading/04_SETUP_DETECTION_RULES.md#13-frontend-vocabulary-reconciliation); price strings → numbers for display only).
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
| Errors | `not-found.tsx`, `(app)/error.tsx` | Add `error.tsx` for the other route groups; typed `ApiError` from adapter |
| Auth guard | None | Next.js request interception (middleware/`proxy` per Next 16 docs) calling `/api/v1/me`; redirect rules in PRD-05 §7 |

## 7. Charts

`components/charts/price-chart.tsx` renders Lightweight Charts with custom primitives (`primitives.ts`) for zones and BOS/CHoCH segments; theme reads CSS tokens (`lib/chart/theme.ts`, OKLCH resolved to sRGB); annotation colours come from the `bull`/`bear` and `chart-entry/event/choch/retest` tokens (§11.4); entry solid, stop dashed, target dotted; SHORT / NO TRADE levels drawn long-dashed and titled "(ref)"; weekly/monthly aggregation in `lib/chart/aggregate.ts` (display only). Required additions: unconfirmed-bar marker, wick-breach markers (dashed reference levels for SHORT setups: done 2026-11-16) ([PRD-07 §7](../product/07_UI_UX_SPECIFICATION.md#7-chart-annotation-rules)).

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
| D-01 | Setup types | `breakout-retest`, `pullback-to-support`, `range-breakout`, `breakdown-retest`, `trend-continuation`, `range-bound` | 4 canonical types (TRD-04) | Update `SetupType` + `SETUP_TYPES` labels; mapping table TRD-04 §13 | M7 |
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
| D-20 | Error handling | ~~No `error.tsx`~~ **Partly resolved 2026-11-16:** `app/(app)/error.tsx` (ErrorState + retry, digest only) | Route error boundaries | Add `(auth)` and onboarding boundaries; request id from `ApiError` once the adapter exists | M7 |
| D-21 | Tooling | ~~No tests, no `typecheck` script~~ **Resolved in M0:** Vitest 5 (`npm test`), `npm run typecheck` | Vitest, `tsc --noEmit` in CI | Done | M0 |
| D-22 | Scanner exchange filter | NSE/BSE filter | Remove (NSE only) | Remove | M7 |
| D-23 | Plan sizing input | Risk budget ₹5,000 default in dialog | Risk % from profile (₹ shown as derived) | See D-06 | M7 |
| D-24 | Prices | `number` in types | Strings in API | Adapter parses | M7 |

## 10. Testing (frontend)

Unit (Vitest): formatters, labels completeness vs enums, mappers, validators, `applyFilters`, journal stats (until server-side). Component (Testing Library): SignalBadge accessibility labels, plan dialog error rendering. E2E (Playwright, M7): login → onboarding (demo) → analysis → create plan (against a seeded backend in Docker). See [ENG-07](07_TESTING_STRATEGY.md).

## 11. Design system

**Authority:** [docs/design-standards.md](../design-standards.md) (rules) and [ADR-013](../adr/ADR-013-DESIGN-STANDARDS.md) (adoption). This section records only how the standard is implemented in this repo, the PriceAction brand values and the justified deviations. It does not restate the rules.

### 11.1 Tokens and brand configuration

| Item | Where | Notes |
|---|---|---|
| Token values (OKLCH) | `src/styles/tokens.css` | The standard's §12 template. Lines marked `BRAND` are PriceAction's: indigo `primary`/`cta`/`ring` (hue 277), chart slot 2 teal (hue 200), slot 3 ink, neutrals tinted navy (chroma 0.012–0.013, hue 265). |
| Token → utility mapping | `src/app/globals.css` (`@theme inline`) | `bg-card`, `text-muted-foreground`, `border-input`, `bg-chart-3`, `text-bull`, … plus `font-stat`, `text-2xs` (11px micro-label), radius scale from `--radius: 0.625rem`, `shadow-float`. |
| Semantic colour classes | `src/lib/colors.ts` | `TONE_CHIP/TEXT/FILL/BORDER`, `CHART_SLOTS`, `CHART_STEPS`, `CHART_REST`, `chartSlot()`, `scoreTone()`, `rrTone()`, `signTone()`. Components never compose tone classes themselves. |
| Enum → label/tone | `src/lib/labels.ts` | Lifecycle states use status tones (`success/warning/destructive/info/neutral`). Structure and bias use market tones (`bull/bear`). The brand accent is never a tone. |
| Fonts | `src/app/layout.tsx` (`next/font`) | Three roles: Archivo (display, `font-heading`; condensed 92% for `font-stat` figures), Inter (text), JetBrains Mono (identifiers). |
| Canvas charts | `src/lib/chart/theme.ts` | Resolves OKLCH tokens to sRGB through a 1×1 canvas so Lightweight Charts can parse them, and re-reads them on theme change. |

After changing any `BRAND` value, re-run the contrast check in §11.5.

### 11.2 Themes

- Preference `light | dark | system` is stored in `localStorage` key `pa-theme` (`components/layout/theme.tsx`). The default is **dark** (PRD-07 UX-01). `ThemeScript` resolves it before first paint, and `useTheme()` tracks the OS setting live while "system" is selected.
- The resolved theme goes on `<html data-theme>`. The `dark:` variant follows that attribute. Token selectors are not `:root`-only, so a nested `[data-theme]` element restates its own surfaces (used by the Settings → Appearance previews).
- Dark mode restates every token (surfaces climb about 4% L: rail 0.175 → page 0.205 → card 0.245 → popover 0.28; borders are white at 8%; cards are lit from above with `--surface-light`). It is not an inversion of light.

### 11.3 Shared components

| Standard component | Implementation |
|---|---|
| `PageFrame` / `PageHeader` | `components/layout/page-frame.tsx`. Every `(app)` page renders through it. |
| `Panel` (`boxed`, `ink`), `Card`, `RowList`, `PanelLink` | `components/ui/panel.tsx` |
| `Stat`, `Eyebrow`, `StatGrid` | `components/data/stat.tsx` |
| `FilterRow`, `ClearButton`, `SearchField` | `components/ui/filter-row.tsx` |
| `ChoiceGroup`, `PillTabs` | `components/ui/choice-group.tsx` (replaces the former `Segmented`) |
| Underlined tabs (4+ views) | `components/ui/tabs.tsx` |
| `SectionLinks` | `components/ui/section-links.tsx` (Settings rail, watchlist rail) |
| `Empty` (`scope` / `clear` / `none`) | `components/data/empty.tsx` (replaces `EmptyState`) |
| `ErrorState` | `components/data/error-state.tsx`; route boundary `app/(app)/error.tsx` |
| Skeletons | `components/data/loading-skeleton.tsx` (`Skeleton`, `StatGridSkeleton`, `TableSkeleton`, `ChartSkeleton`, `PageSkeleton`) |
| Controls | `components/ui/{button,input,select,checkbox,switch}.tsx`. Button variants are `primary | outline | ghost | danger`, all `rounded-lg`, default `h-8`. |

The removed components (`MetricCard`, `EmptyState`, `Segmented`, `PageContainer`) must not be reintroduced.

### 11.4 Justified deviations

| Deviation from the standard | Justification |
|---|---|
| No shadcn/ui, Base UI or Remix Icon. Own primitives and lucide-react are used instead. | ADR-001 / DEC-002 exclude UI libraries; the rules are met with existing primitives. |
| `bull` / `bear` market-direction tokens beside the status set | Price direction is not a status. Always paired with a sign, label or shape. |
| Price-action annotation tokens (`chart-entry/event/choch/retest`) | These are a domain legend, not categorical series. They alias chart slots (1, 1, 2, 6) and each also differs by line style or shape (PRD-07 §7). Stop and target use `bear`/`bull`. |
| Theme on `data-theme` instead of the `.dark` class | Existing pre-paint script and nested previews; `dark:` is mapped to the attribute. |
| `--input` darker than the template (light L 0.66, dark 35% white) | WCAG 1.4.11: control boundaries reach 3:1 against the card. |
| Checkbox box, kbd hint and theme-preview miniatures use `rounded-sm` | A 16px square at the control radius reads as a radio; miniatures follow the "skeleton takes the shape it stands in for" rule. |
| Tooltips `rounded-lg` (not `xl`) | Control-sized floating labels. |
| No react-hook-form + Zod | Out of scope for a design change; the existing controlled inputs and `features/auth/validation.ts` stay. Revisit with the M7 HTTP adapter (server field errors). |
| Stock Analysis verdict card scrolls inside itself on desktop (sticky) | A workspace pane, not a dashboard panel; the "no scrolling inside a card" rule (§10) applies to dashboards. |

### 11.5 Verification (2026-11-16)

- WCAG 2.1 AA contrast, computed from the OKLCH tokens in both themes: text, status, market tones and `primary` on background/card/popover ≥ 4.5:1; chip text on its own 10% tint ≥ 4.5:1; `ring` ≥ 4.5:1 on every surface including the sidebar; `*-foreground` on its fill ≥ 4.5:1; `--input` borders ≥ 3:1. No failures.
- Every route rendered in a production build and checked by headless-Chrome screenshots in light and dark, at 1440, 820 and 390 px wide. No page-level horizontal overflow. Keyboard: visible focus ring, arrow-key roving in `ChoiceGroup`/`Tabs`, dialog focus trap.
- Lint, typecheck, 25 Vitest tests (including `lib/colors.test.ts`) and `next build` all pass.
