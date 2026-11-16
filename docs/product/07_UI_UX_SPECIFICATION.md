# UI/UX Specification

| Field | Value |
|---|---|
| Document ID | PRD-07 |
| Version | 0.2.0 |
| Status | Reflects implemented frontend (Phase 1) + required additions |
| Owner | Product Manager / Frontend Lead |
| Last updated | 2026-11-16 |
| Related | [design-standards](../design-standards.md) · [ADR-013](../adr/ADR-013-DESIGN-STANDARDS.md) · [ENG-02 Frontend architecture](../engineering/02_FRONTEND_ARCHITECTURE.md) · [PRD-03 §6 Screens](03_PRD.md#6-screen-level-requirements) · `frontend/src/styles/tokens.css` · `frontend/src/lib/labels.ts` |

## 1. Purpose

Documents the product-level interaction rules so backend integration preserves them, and lists the UI additions the specification requires. Visual rules (layout, spacing, radius, type, colour, depth, states, accessibility) are governed by [docs/design-standards.md](../design-standards.md) ([ADR-013](../adr/ADR-013-DESIGN-STANDARDS.md)); their implementation is in [ENG-02 §11](../engineering/02_FRONTEND_ARCHITECTURE.md#11-design-system).

## 2. Design principles (as implemented)

| ID | Principle | Implementation |
|---|---|---|
| UX-01 | Dark-first, data-dense, calm trading UI | Dark default; light and system modes fully supported (`data-theme`, ENG-02 §11.2) |
| UX-02 | Never a bare BUY/SELL | `SignalBadge` uses distinct shape + icon + colour + tooltip per state |
| UX-03 | Sample data is always labelled | `SampleDataBadge`, market-status tooltip, settings "Sample data — Active" |
| UX-04 | Numbers are readable and stable | Tabular numerals everywhere, condensed figure face (`font-stat`), en-IN formatting, lakh/crore compaction |
| UX-05 | No-trade is normal | `NO TRADE` described as "Staying flat is a valid decision." |
| UX-06 | Explain before acting | Evidence panel "Why is this setup being considered?", entry conditions, invalidation |
| UX-07 | Plans are proposals | Plan dialog: "Creates a proposed plan for review. It does not place an order with any broker." |

## 3. Design tokens

Token vocabulary and values follow [design-standards §6 and §12](../design-standards.md#12-token-template). PriceAction brand values, domain extensions (`bull`/`bear`, price-action annotation tokens) and theme conventions are in [ENG-02 §11](../engineering/02_FRONTEND_ARCHITECTURE.md#11-design-system). Components never use raw colour values.

Tones (`lib/colors.ts`): status `success`, `warning`, `destructive`, `info`, `neutral`; market `bull`, `bear`. The brand accent is reserved for the primary action, the active navigation row, a switch that is on and the current selection.

## 4. Signal and status presentation

| State | Label | Tone | Shape/icon |
|---|---|---|---|
| `BUY_WATCH` | BUY WATCH | warning | dashed outline, Eye |
| `ENTRY_CONFIRMED` | ENTRY CONFIRMED | success | solid fill, CircleCheck |
| `HOLD` | HOLD | info | soft fill, ShieldCheck |
| `EXIT` | EXIT | destructive | soft fill + border, LogOut |
| `NO_TRADE` | NO TRADE | neutral | outline, Ban |

Setup status, structure, plan status and outcome labels/tones are centralised in `lib/labels.ts`; backend enum values map onto these keys in the HTTP adapter (vocabulary reconciliation in [TRD-04 §12](../trading/04_SETUP_DETECTION_RULES.md#12-frontend-vocabulary-reconciliation)). New labels required: setup status `EXPIRED`, plan statuses `SKIPPED`/`EXPIRED`/`FILLED`, structure `SIDEWAYS` (replaces "Range").

## 5. Layout and navigation

- `(auth)` group: split-screen layout with product showcase (`auth-showcase.tsx`).
- `(app)` group: `AppShell` with collapsible sidebar (persisted in localStorage `pa-sidebar`), top navigation (search, market status, notifications, user menu), breadcrumbs, mobile nav.
- Navigation groups (`lib/navigation.ts`): Overview (Dashboard) · Market (Market Scanner, Stock Analysis, Watchlists) · Trading (Trade Plans, Portfolio, Trading Journal, Backtesting) · System (Settings).
- Global search (`global-search.tsx`) opens analysis for a symbol.

## 6. Component library (existing)

Shared design-system components (PageFrame, Panel, Card, Stat/StatGrid, FilterRow, ChoiceGroup, SectionLinks, Empty, ErrorState, skeletons) are listed in [ENG-02 §11.3](../engineering/02_FRONTEND_ARCHITECTURE.md#113-shared-components). Domain components:

| Layer | Components |
|---|---|
| `components/ui` | Button, Input/Textarea, Select, Checkbox, Switch, Tabs, ChoiceGroup, SectionLinks, FilterRow, Dropdown, Dialog, Tooltip, Toast, Panel |
| `components/layout` | AppShell, AppSidebar, TopNavigation, Breadcrumb, PageFrame/PageHeader, GlobalSearch, MobileNav, Brand, UserBadge, theme |
| `components/data` | Stat/StatGrid, PriceDisplay, MarketStatus, DataTable, StatusBadge, Badge, Empty, ErrorState, LoadingSkeleton, Sparkline, SampleDataBadge, Disclaimer |
| `components/trading` | SignalBadge, SetupCard, TradePlanCard, RiskRewardDisplay, MarketStructureBadge, PriceLevelIndicator, AnalysisPanel, StockTable, LifecycleStrip, QualityScore |
| `components/charts` | PriceChart (+ zone and BOS/CHoCH primitives), EquityChart |

## 7. Chart annotation rules

| Object | Rendering rule |
|---|---|
| Swing points | Label (HH/HL/LH/LL/EQH/EQL) above highs / below lows, only for confirmed pivots |
| Unconfirmed bars | Last `pivot.right_bars` bars visually marked "unconfirmed" (new) |
| BOS / CHoCH | Horizontal segment from level pivot to break bar, labelled; BOS dashed in the break direction (bull/bear), CHoCH dotted in `chart-choch` |
| Wick breach | Small marker, no line (new) |
| Zones | Band from `formed_at_date` to right edge; opacity by strength; flipped zones styled differently |
| Levels | Entry (`chart-entry`, solid), stop (bear, dashed), target (bull, dotted) lines with price labels; trigger shown as dashed when status is AWAITING (new) |
| Short/informational setups | Levels drawn long-dashed, titled "(ref)" on the axis and "Reference only" in the panel (implemented) |

## 8. States every data screen must handle

| State | Requirement |
|---|---|
| Loading | Skeletons (`loading.tsx` exists for `(app)`) |
| Empty | `EmptyState` with next action (e.g. "First analysis runs after data import completes") |
| Error | Route-level `error.tsx` with retry and request id (`(app)` implemented with digest; request id in M7) |
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

Target WCAG 2.2 AA (design-standards requires 2.1 AA as the floor). Contrast for every token pairing in both themes was verified on 2026-11-16 ([ENG-02 §11.5](../engineering/02_FRONTEND_ARCHITECTURE.md#115-verification-2026-11-16)). Already present: visible focus ring (`ring`) on every control, arrow-key roving in choice groups and tabs, focus management in Dialog, keyboard navigation in Dropdown, aria labels on signal badges, colour-independent signal shapes. To verify in M7: chart alternative text/table view for screen readers, focus order in plan dialog, screen-reader pass on the analysis workspace.

## 11. Copy rules

- Never "buy now", "sell", "guaranteed", "accuracy", "win probability".
- Use "setup", "plan", "proposed", "reference only", "sample data".
- Disclaimer component on analysis and backtest pages: "PriceAction AI provides rule-based analysis for education and decision support. It is not investment advice."
