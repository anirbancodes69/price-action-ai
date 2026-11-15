# UI/UX Specification

| Field | Value |
|---|---|
| Document ID | PRD-07 |
| Version | 0.1.0 |
| Status | Reflects implemented frontend (Phase 1) + required additions |
| Owner | Product Manager / Frontend Lead |
| Last updated | 2026-11-15 |
| Related | [ENG-02 Frontend architecture](../engineering/02_FRONTEND_ARCHITECTURE.md) · [PRD-03 §6 Screens](03_PRD.md#6-screen-level-requirements) · `frontend/src/styles/tokens.css` · `frontend/src/lib/labels.ts` |

## 1. Purpose

Documents the implemented design system and interaction rules so backend integration preserves them, and lists the UI additions the specification requires. This phase does **not** redesign the frontend.

## 2. Design principles (as implemented)

| ID | Principle | Implementation |
|---|---|---|
| UX-01 | Dark-first, data-dense, calm trading UI | Dark default (`data-theme="dark"`), light theme as working preview |
| UX-02 | Never a bare BUY/SELL | `SignalBadge` uses distinct shape + icon + colour + tooltip per state |
| UX-03 | Sample data is always labelled | `SampleDataBadge`, market-status tooltip, settings "Sample data — Active" |
| UX-04 | Numbers are readable and stable | Tabular numerals (`tnum`), en-IN formatting, lakh/crore compaction |
| UX-05 | No-trade is normal | `NO TRADE` described as "Staying flat is a valid decision." |
| UX-06 | Explain before acting | Evidence panel "Why is this setup being considered?", entry conditions, invalidation |
| UX-07 | Plans are proposals | Plan dialog: "Creates a proposed plan for review. It does not place an order with any broker." |

## 3. Design tokens

Defined as RGB channel CSS variables in `src/styles/tokens.css`, mapped to Tailwind v4 utilities in `src/app/globals.css` (`@theme inline`). Components never use raw hex.

| Group | Tokens (dark values) |
|---|---|
| Surfaces | `--c-canvas #080D1A`, `--c-base #0B1120`, `--c-subtle #111827`, `--c-surface #151E2F`, `--c-raised #1E293B`, `--c-hover #243045` |
| Lines | `--c-border #232E42`, `--c-border-strong #334159` |
| Text | `--c-fg #F1F5F9`, `--c-fg-muted #94A3B8`, `--c-fg-subtle #64748B` |
| Market semantics | `--c-bull #22C55E`, `--c-bull-strong #16A34A`, `--c-bear #EF4444`, `--c-bear-strong #DC2626`, `--c-neutral #64748B` |
| Brand / status | `--c-accent #6366F1`, `--c-warn #F59E0B`, `--c-info #38BDF8` |
| Chart | `--c-chart-grid`, `--c-chart-crosshair` |
| Typography | Inter (sans), JetBrains Mono (mono); `text-2xs` 11px |
| Radius | sm 3px, default 5px, md 6px, lg 8px |

Tones (`lib/labels.ts` `TONE_CLASSES`): `bull`, `bear`, `neutral`, `accent`, `warn`, `info`.

## 4. Signal and status presentation

| State | Label | Tone | Shape/icon |
|---|---|---|---|
| `BUY_WATCH` | BUY WATCH | warn | dashed outline, Eye |
| `ENTRY_CONFIRMED` | ENTRY CONFIRMED | bull | solid fill, CircleCheck |
| `HOLD` | HOLD | info | soft fill, ShieldCheck |
| `EXIT` | EXIT | bear | soft fill, LogOut |
| `NO_TRADE` | NO TRADE | neutral | outline, Ban |

Setup status, structure, plan status and outcome labels/tones are centralised in `lib/labels.ts`; backend enum values map onto these keys in the HTTP adapter (vocabulary reconciliation in [TRD-04 §12](../trading/04_SETUP_DETECTION_RULES.md#12-frontend-vocabulary-reconciliation)). New labels required: setup status `EXPIRED`, plan statuses `SKIPPED`/`EXPIRED`/`FILLED`, structure `SIDEWAYS` (replaces "Range").

## 5. Layout and navigation

- `(auth)` group: split-screen layout with product showcase (`auth-showcase.tsx`).
- `(app)` group: `AppShell` with collapsible sidebar (persisted in localStorage `pa-sidebar`), top navigation (search, market status, notifications, user menu), breadcrumbs, mobile nav.
- Navigation groups (`lib/navigation.ts`): Overview (Dashboard) · Market (Market Scanner, Stock Analysis, Watchlists) · Trading (Trade Plans, Portfolio, Trading Journal, Backtesting) · System (Settings).
- Global search (`global-search.tsx`) opens analysis for a symbol.

## 6. Component library (existing)

| Layer | Components |
|---|---|
| `components/ui` | Button, Input, Select, Checkbox, Switch, Tabs, Dropdown, Dialog, Tooltip, Toast, Panel, Segmented |
| `components/layout` | AppShell, AppSidebar, TopNavigation, Breadcrumb, PageHeader, GlobalSearch, MobileNav, Brand, UserBadge, theme |
| `components/data` | MetricCard, PriceDisplay, MarketStatus, DataTable, StatusBadge, Badge, EmptyState, LoadingSkeleton, Sparkline, SampleDataBadge, Disclaimer |
| `components/trading` | SignalBadge, SetupCard, TradePlanCard, RiskRewardDisplay, MarketStructureBadge, PriceLevelIndicator, AnalysisPanel, StockTable, LifecycleStrip, QualityScore |
| `components/charts` | PriceChart (+ zone and BOS/CHoCH primitives), EquityChart |

## 7. Chart annotation rules

| Object | Rendering rule |
|---|---|
| Swing points | Label (HH/HL/LH/LL/EQH/EQL) above highs / below lows, only for confirmed pivots |
| Unconfirmed bars | Last `pivot.right_bars` bars visually marked "unconfirmed" (new) |
| BOS / CHoCH | Horizontal segment from level pivot to break bar, labelled; CHoCH visually distinct |
| Wick breach | Small marker, no line (new) |
| Zones | Band from `formed_at_date` to right edge; opacity by strength; flipped zones styled differently |
| Levels | Entry (accent), stop (bear), target (bull) lines with price labels; trigger shown as dashed when status is AWAITING |
| Short/informational setups | Levels drawn dashed and labelled "Reference only" |

## 8. States every data screen must handle

| State | Requirement |
|---|---|
| Loading | Skeletons (`loading.tsx` exists for `(app)`) |
| Empty | `EmptyState` with next action (e.g. "First analysis runs after data import completes") |
| Error | Route-level `error.tsx` with retry and request id (**missing today**) |
| Stale data | As-of date always visible; "Data delayed" banner when last ingested date < last trading day |
| Demo | `SampleDataBadge` whenever `meta.data_mode = DEMO` |
| Partial batch | "Analysed 487 / 500" indicator |

## 9. Required UI additions (from specification)

| ID | Addition | Screen |
|---|---|---|
| UIA-01 | `/reset-password` page | auth |
| UIA-02 | Route protection and onboarding redirect | all `(app)` |
| UIA-03 | "Explain this chart" button and AI panel with disclaimer, fallback label | `/analysis/[symbol]` |
| UIA-04 | Ruleset version, as-of, data mode footer on analysis | `/analysis/[symbol]` |
| UIA-05 | Paper / Actual book toggle | `/portfolio`, `/journal` |
| UIA-06 | Actual trade entry form (fills) replacing "Link order" toast | `/trade-plans`, `/portfolio` |
| UIA-07 | Paper trades list with stop-up and close | `/portfolio` tab or `/paper-trades` (OQ-PRD-01) |
| UIA-08 | Backtest run history, progress, results with bias flags | `/backtesting` |
| UIA-09 | Zerodha connect flow states (connecting, connected, expired, error) | `/settings`, `/onboarding` |
| UIA-10 | Ingestion status and data-source switch | `/settings#data` |
| UIA-11 | Max position %, min R:R override fields | `/settings#risk` |
| UIA-12 | Error boundaries | all `(app)` |
| UIA-13 | Universe options: add NIFTY 500 (default), remove "All NSE equities" | onboarding, settings |
| UIA-14 | Remove/hide Exchange (NSE/BSE) filter | `/market-scanner` |

## 10. Accessibility

Target WCAG 2.2 AA. Already present: focus management in Dialog, keyboard navigation in Dropdown, aria labels on signal badges, colour-independent signal shapes. To verify in M7: contrast of `fg-subtle` on surfaces in both themes, chart alternative text/table view for screen readers, focus order in plan dialog.

## 11. Copy rules

- Never "buy now", "sell", "guaranteed", "accuracy", "win probability".
- Use "setup", "plan", "proposed", "reference only", "sample data".
- Disclaimer component on analysis and backtest pages: "PriceAction AI provides rule-based analysis for education and decision support. It is not investment advice."
