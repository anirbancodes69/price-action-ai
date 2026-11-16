---
name: frontend-ui
description: Frontend workflow for the PriceAction AI Next.js 16 app in frontend/ - App Router pages, feature views, the token-based Tailwind v4 design system, reusable components (ui, data, trading, charts, layout), Lightweight Charts overlays, the DataSource adapter boundary, labels and formatters, sample-data badging, responsive layout, accessibility (WCAG 2.2 AA) and premium dark-first fintech UI. Use when creating or changing any page, component, style, chart, hook or frontend test, or when wiring frontend data. Never introduces Bootstrap or a UI component library.
---

# Frontend UI

Changes to `frontend/` must look and behave like the existing product: dark-first, data-dense, token-driven, and honest about sample data. Authority: [docs/design-standards.md](../../../docs/design-standards.md) (mandatory for every visual change, [ADR-013](../../../docs/adr/ADR-013-DESIGN-STANDARDS.md)), [ADR-001](../../../docs/adr/ADR-001-FRONTEND-ARCHITECTURE.md), [ENG-02](../../../docs/engineering/02_FRONTEND_ARCHITECTURE.md) (§11 design-system implementation and deviations), [PRD-07](../../../docs/product/07_UI_UX_SPECIFICATION.md).

> Current state: Phase 1 UI is complete on **mock data only** (`src/lib/data/mock-source.ts`). Analysis overlays come from a demo heuristic (`src/mocks/demo-analysis.ts`), not the engine. There is no HTTP adapter, mutation client or auth guard yet (M7). 24 known spec discrepancies are in ENG-02 §9.

## Required context

1. [frontend/AGENTS.md](../../../frontend/AGENTS.md): Next.js 16 differs from your training data. Read the relevant guide in `frontend/node_modules/next/dist/docs/` before using framework APIs (routing, caching, middleware/`proxy`, metadata).
2. ENG-02 §3 directory structure, §5 data boundary, §6 state and forms, §7 charts, **§9 discrepancy register**.
3. PRD-07 for the screen you touch: layout, states, §7 chart annotation rules, §10 accessibility.
4. [docs/design-standards.md](../../../docs/design-standards.md) in full, then [ENG-02 §11](../../../docs/engineering/02_FRONTEND_ARCHITECTURE.md#11-design-system): `src/styles/tokens.css`, `src/app/globals.css`, `src/lib/colors.ts` and the shared components.

## Workflow

1. **Find before you build.** Pages render through `PageFrame`/`PageHeader`; build from `Panel`, `Card`, `StatGrid`, `FilterRow`, `ChoiceGroup`, `Empty`, `ErrorState` and skeletons. Search `src/components/**` (`ui/`, `data/`, `trading/`, `charts/`, `layout/`), `src/lib/labels.ts`, `src/lib/colors.ts`, `src/lib/format.ts` and `src/hooks/` for an existing piece. Extend it rather than creating a parallel one.
2. **Data only through `DataSource`.** Pages and features import from `@/lib/data`, never from `src/mocks` directly. A data need the interface lacks is added to `source.ts` + `mock-source.ts`, and noted against ARC-04 / ENG-02 §8 so the M7 HTTP adapter can serve it.
3. **Style only with tokens.** Use semantic utilities (`bg-card`, `text-muted-foreground`, `text-bull`, `border-input` and similar) and tone classes from `lib/colors.ts`. No raw hex or arbitrary colour values. Radii only `xl`/`lg`/`full`; gaps only 6/4/3/1. Light, dark and system themes must all work (`data-theme`).
4. **Build every state:** loading (`loading-skeleton`), empty (`Empty`), error (`ErrorState`), and populated. Responsive from phone width up: the sidebar collapses to `mobile-nav`, and tables need an overflow strategy.
5. **Accessibility:** semantic elements, keyboard reachability, visible focus, labelled controls, signal meaning not conveyed by colour alone (keep shape and text), sufficient contrast, chart alternatives where data is essential.
6. **Validate** (and walk the design-standards §14 review checklist): `make lint-frontend` (ESLint + `next typegen && tsc --noEmit`), `make test-frontend` (Vitest), and a production build (`npm run build`, as in CI). Add Vitest tests for new pure logic (formatters, mappers, filters, validators). For visible changes, run the app and check the screen.

## Hard rules

| Rule | Source |
|---|---|
| No Bootstrap, MUI, Chakra, shadcn-installed libraries or any other UI kit. Icons: `lucide-react`. Charts: Lightweight Charts v5 | ADR-001, CLAUDE.md §2 |
| TypeScript strict. Domain types live in `src/types` and are the frontend contract | CLAUDE.md §5 |
| Frontend calls only Laravel `/api/v1` (from M7). Never the engine, Kite or the DB. No broker credentials in the browser or `localStorage` | ARC-04 §2.2, ARC-06 §5, C-06 |
| No trading logic in TypeScript. Display what the engine returns. Chart aggregation is display only | CLAUDE.md §3 |
| Every market-data surface shows its data mode. DEMO shows `SampleDataBadge` and is never styled or worded as live | C-03, ARC-08 §2 |
| No order-placement UI. Plans are for manual execution | ADR-010, BAC-06 |
| SHORT setups are informational (dashed or reference styling, no buy action). NO_TRADE is presented as a valid result, not an error | C-12, PRD-07 §7 |
| Legacy setup vocabulary is mapped at the adapter boundary (TRD-04 §12), not in components | ENG-02 §5 |
| No redesigns or renames during integration work. Keep the existing structure | ROADMAP M7, CLAUDE.md §5 |

## Deliverables

- The change, with lint, typecheck, tests and build results, plus a note on screens checked.
- Updates to ENG-02 (including §9 discrepancies resolved or added), PRD-06 feature status, PRD-07 if UX changed, and ARC-04 if data needs changed. Then the `docs-sync` skill.
