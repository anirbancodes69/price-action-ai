# ADR-013: Adopt the Project Design Standards

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-16 |
| Deciders | Product owner / Frontend lead |
| Version | 1.0 |
| Related | [design-standards](../design-standards.md) · [ADR-001](ADR-001-FRONTEND-ARCHITECTURE.md) · [ENG-02 §11](../engineering/02_FRONTEND_ARCHITECTURE.md#11-design-system) · [PRD-07](../product/07_UI_UX_SPECIFICATION.md) |

## Context

The Phase 1 frontend had its own token vocabulary (`surface`, `raised`, `fg-subtle`, `accent` as the brand), three text colours, one font role, 3–8px radii and per-page layout conventions. The brand accent was also used for status, chart lines and links. A portable, brand-neutral rule set ([docs/design-standards.md](../design-standards.md)) now exists. It covers layout, spacing, radius, type, colour, depth, dashboards, states and accessibility. The owner asked for it to become the authority for every page.

The standard assumes shadcn/ui (Base UI primitives) and Remix Icon. ADR-001 and DEC-002 exclude UI component libraries, and the frontend uses lucide-react.

## Decision

1. `docs/design-standards.md` is the authoritative UI/UX rule set for `frontend/`. CLAUDE.md §5 makes reading it mandatory before any visual change.
2. Adopt the standard's **token vocabulary and template** (OKLCH, `background/card/popover/muted/accent/border/input/ring/primary/cta`, status `success/warning/destructive/info`, `chart-1..8`, `chart-step-*`, `chart-rest`, `sidebar-*`). Only the `BRAND` values are PriceAction-specific (indigo primary/CTA/ring, teal and ink chart slots, navy-tinted neutrals).
3. Implement the standard's shared components (`PageFrame`/`PageHeader`, `Panel`, `Card`, `Stat`/`Eyebrow`/`StatGrid`, `FilterRow`/`ClearButton`, `ChoiceGroup`/`PillTabs`/`SectionLinks`, `Empty`/`ErrorState`/skeletons, `lib/colors.ts`) on the existing primitives. **No new dependencies:** ADR-001 stands, no shadcn/Base UI and no Remix Icon (lucide stays).
4. Domain extensions, recorded as justified deviations in [ENG-02 §11.4](../engineering/02_FRONTEND_ARCHITECTURE.md#114-justified-deviations): `bull`/`bear` market-direction tokens and the `chart-entry/event/choch/retest` annotation tokens.
5. Themes: light, dark and system. **Dark stays the default** (PRD-07 UX-01 unchanged). The theme is applied through `<html data-theme>`, and the standard's `.dark` class is replaced by a `dark` custom variant on that attribute.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Keep the old token names and only adjust values | Leaves the standard's recipes inapplicable as written, and keeps the brand accent as a status colour. |
| Install shadcn/ui (`base-nova`) and Remix Icon as the standard assumes | Contradicts ADR-001 / DEC-002 and adds dependency and upgrade risk for no rule the existing primitives cannot meet. |
| Make "system" the default theme | Would silently change the dark-first product decision (UX-01). It is offered as an option instead. |

## Consequences

+ One design language on every page; the standard's checklists apply directly to new work.
+ Status, market direction, chart series and brand are separate colour groups, and every tone sits beside a word or icon.
+ WCAG 2.1 AA contrast is verified for every token pairing in both themes (ENG-02 §11.5).
− Every frontend file changed once (class vocabulary); open branches touching `frontend/` need a rebase.
− Control borders are heavier than the template's (3:1 for WCAG 1.4.11).
− Forms keep the existing controlled-input validators instead of react-hook-form + Zod (deviation recorded in ENG-02 §11.4).

## Status

Accepted on 2026-11-16. Does not supersede ADR-001; refines DEC-002's "custom token-based design system".
