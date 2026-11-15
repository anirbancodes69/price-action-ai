# PriceAction AI — Frontend (Phase 1)

Premium, dark-first UI foundation for PriceAction AI: AI-assisted pure price-action analysis for Indian equity swing and positional traders.

> **All market values in this build are sample data.** Nothing is live. Every screen showing prices carries a "Sample data" badge.

## Run

### Docker (recommended)

From the repository root:

```bash
docker compose up --build frontend          # production build → http://localhost:3000
docker compose --profile dev up frontend-dev # hot-reload dev server → http://localhost:3001
```

### Local

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
npm run build && npm start
npm run lint
```

`/` redirects to `/login`. Any syntactically valid email and password signs in to the demo workspace.

## Stack

Next.js 16 (App Router, Cache Components) · React 19 · TypeScript (strict) · Tailwind CSS v4 · lucide-react · TradingView Lightweight Charts v5. No other UI framework.

## Architecture

```
src/
  app/                  Routes only — thin server components that fetch via `data` and render a feature view
    (auth)/             /login /register /forgot-password (split-screen layout)
    (app)/              Authenticated shell (sidebar + top nav) for all product pages
    onboarding/         Multi-step onboarding
  features/<area>/      Page compositions and feature-local state (dashboard, scanner, analysis, …)
  components/
    ui/                 Primitives: Button, Input, Select, Checkbox, Switch, Tabs, Dropdown, Dialog, Tooltip, Toast, Panel, Segmented
    layout/             AppShell, AppSidebar, TopNavigation, Breadcrumb, PageHeader, GlobalSearch, MobileNav, theme
    data/               MetricCard, PriceDisplay, MarketStatus, DataTable, StatusBadge, EmptyState, LoadingSkeleton, Sparkline, SampleDataBadge
    trading/            SignalBadge, SetupCard, TradePlanCard, RiskRewardDisplay, MarketStructureBadge, PriceLevelIndicator, AnalysisPanel, StockTable, LifecycleStrip
    charts/             PriceChart (+ zone / BOS-CHoCH primitives), EquityChart
  lib/
    data/               DataSource interface + mock adapter  ← swap for an HTTP adapter later
    labels.ts           Single source of truth for enum labels, tones, explanations
    format.ts           en-IN / Asia/Kolkata formatting (hydration-safe)
    navigation.ts       Nav config + breadcrumbs
    chart/              Chart theme (reads CSS tokens) and timeframe aggregation
  hooks/                useSort, usePersistentState, useMarketSession
  types/                Domain types — the contract the backend must satisfy
  mocks/                Sample data + deterministic sample-series generator
  styles/tokens.css     Design tokens (dark + light)
```

### Connecting the backend

Pages depend only on `DataSource` (`src/lib/data/source.ts`). Implement it with HTTP calls to the Laravel API and export it from `src/lib/data/index.ts`. No page or component needs to change. `StockAnalysis` (`src/types/analysis.ts`) is the expected payload from the Python analysis engine: candles, swings, structure breaks, zones, events, setup, levels, quality factors, entry/invalidation conditions and evidence.

### Sample analysis data

`src/mocks/demo-series.ts` generates deterministic OHLCV series from scripted price-action templates (breakout/retest, pullback, range, breakdown). `src/mocks/demo-analysis.ts` derives swings, BOS/CHoCH, zones and levels from those candles so chart annotations match the bars. This is a **demo heuristic, not the product's trading logic**, which has not been specified yet.

### Design system

- Tokens are CSS variables (`--c-*`, RGB channels) in `src/styles/tokens.css`, mapped to Tailwind utilities in `globals.css` (`bg-surface`, `text-fg-muted`, `text-bull`, `border-border`, …).
- Theme is switched with `<html data-theme>`. Light is a working preview, applied pre-paint and persisted.
- Prices use the `tnum` utility (tabular numerals).
- Signal states (BUY WATCH, ENTRY CONFIRMED, HOLD, EXIT, NO TRADE) each have a distinct shape, colour and icon, plus a tooltip explanation. A bare BUY/SELL label is never shown.
