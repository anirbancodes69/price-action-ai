# Design Standards

A portable set of UI and UX rules for dense, data-heavy web apps (work tools, dashboards, admin consoles). It is distilled from PMO Assist and kept brand-neutral: the rules stay as they are, and the brand lives in one block of colour tokens that you replace.

**Stack it assumes:** React, Tailwind CSS 4, shadcn/ui (style `base-nova`, Base UI primitives), Remix Icon. The rules themselves work with any stack; only the class names are Tailwind.

**How to adopt it in a new repo**

1. Put this file at `docs/design-standards.md` (or the repo root).
2. Paste the token template from section 12 into your main stylesheet and change only the values marked `/* BRAND */`.
3. Add one line to the repo's `AGENTS.md` or `CLAUDE.md`: *"Layout, spacing, radius, colour and dashboard order follow docs/design-standards.md. Read it before building a page or a component."* That line is what makes an AI assistant apply these rules on every feature.
4. Build the six shared components in section 11 first. Every page is then made from them.

---

## 1. Principles

1. **Restraint is the design.** The brand colours are not what makes a page look good. Layout, rhythm and the absence of noise around them do that.
2. **Colour means something, or it isn't there.** Text is either foreground or muted. Anything else coloured is a status, a chart series, the primary action or the current selection.
3. **One of each.** One primary action per page, one emphasis card per page, one level of grouping per page, one radius per kind of thing.
4. **Depth from tone, not shadow.** Layers get lighter as they rise. Only things that float get a shadow.
5. **Every state is designed.** Empty, loading, error and refused states are part of the feature, not an afterthought.
6. **Same kind, same look.** A control next to a control must read as the same kind of thing.
7. **Accessible by default.** WCAG 2.1 AA on every feature. A page must read in both light and dark.

## 2. The page

- Every top-level page renders through one `PageFrame`:
  - one gutter: `px-6 sm:px-10 lg:px-12`, with `py-6`
  - one vertical rhythm: `flex flex-col gap-6`
  - one title size: `font-heading text-2xl sm:text-3xl tracking-tight`
- **Title:** says what the page is, in one to three words. **Description** (optional, `text-sm text-muted-foreground max-w-2xl`): says what the reader can do here, in one sentence.
- **Actions** sit to the right of the title. There is at most one primary (filled) action, and the rest go in a menu or as outline buttons.
- **Filters and views** sit on the page under the title, never inside a card.
- **The sidebar is the navigation.** A page does not repeat it with a row of tabs. Routed sub-pages: up to three are a pill group, and four or more become underlined tabs.

## 3. Spacing

One scale, and nothing in between:

| Between | Gap |
|---|---|
| Sections of a page | `gap-6` (24px) |
| Cards in a grid, panels side by side | `gap-4` (16px) |
| Rows inside a card or list | `gap-3` (12px) |
| A label and its value, a title and its hint | `gap-1` (4px) |

- Card padding is `px-5 py-4`. A stat card is `px-6 py-5`.
- Table cells and list rows keep the component's own padding.
- **Fix a gap on the parent, never with a margin on a child.**

## 4. Corners

Set `--radius: 0.625rem` and always use the tokens, never a pixel value:

| Shape | Radius |
|---|---|
| Cards, bordered panels, dialogs, popovers | `rounded-xl` |
| **Every control:** buttons of all variants, inputs, selects, textareas, menu triggers, bordered lists and tables | `rounded-lg` |
| Tokens and toggles: chips, badges, avatars, switches, segmented choice groups | `rounded-full` |

- The primary button gets the same radius as every other control, because Cancel next to Save must look like a pair. Pill-shaped buttons are a marketing convention, not a product one.
- A skeleton takes the radius of the thing it stands in for.
- If avatars are rounded squares, set the radius once on the `Avatar` root, never on the image or the fallback alone.

## 5. Type

| Role | Style |
|---|---|
| Page title | heading font, `text-2xl sm:text-3xl tracking-tight` |
| Panel title | `text-sm font-semibold uppercase tracking-[0.12em]` |
| Eyebrow / micro-label | `text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground`, used once at the top of a card |
| Stat figure | condensed numeric face (`font-stat`), `text-4xl leading-none` |
| Body | `text-sm` |
| Secondary facts, hints | `text-xs text-muted-foreground` |
| Numbers and dates | `tabular-nums` everywhere |
| Identifiers (keys, ids, tokens) | monospace |

- **Two weights only:** `font-medium` for a name or a row's subject, and regular for everything else.
- **Three font roles:** a display face for headings, a text face for body, and a condensed face for figures (Archivo variable at 92% width works well). Swap the families to fit your brand, but keep the three roles.

## 6. Colour

### The vocabulary

| Group | Tokens | Used for | Never used for |
|---|---|---|---|
| Neutrals | `background`, `card`, `popover`, `muted`, `accent`, `secondary`, `border`, `input`, `foreground`, `muted-foreground` | Surfaces and text | n/a |
| Brand accent | `primary`, `cta` | The primary button, the active nav item, a switch that is on | Body text, large backgrounds, chart series |
| Focus | `ring` | Focus rings and text selection | Anything else |
| Status | `success`, `warning`, `destructive`, `info` (+ neutral) | How something **is** | Chart series |
| Chart | `chart-1` to `chart-8`, `chart-step-1` to `chart-step-4`, `chart-rest` | Telling series apart | Status |

### Rules

- Text is `text-foreground` or `text-muted-foreground`. Nothing else is coloured unless it means something.
- A status tone appears in one of three forms, **always with a word or icon next to it, never alone**:
  - **chip:** `bg-{tone}/10 text-{tone}`
  - **text:** `text-{tone}`
  - **fill:** `bg-{tone}` (a dot, a bar segment)
- Status colours need at least 4.5:1 contrast as text on both page and card, in both themes. Make "destructive" a crimson (hue ~20) so it can't be mistaken for an orange brand or chart colour.
- **Charts** use slots 1 to 8 **in order, and never cycle**. The order is what keeps adjacent series colour-blind safe. After eight, group the tail into "Other" in muted.
  - Slots 1 to 3 are your brand colours, 4 and 5 are tints of 1 and 2, and 6 to 8 go beyond the brand.
  - Ordered states (to do → done) use the one-hue `chart-step` ramp instead.
  - "The remainder of a whole" (free capacity) uses `chart-rest`, which recedes.
  - Light tints fall below 3:1 on the card, so show their values in labels or tooltips.
- **Focus** is one strong colour in every palette, at least 4.5:1 on every surface. Never reuse the brand accent for focus if it is light (neon or yellow on a light surface fails).
- **Dark mode is not inverted light mode.** Restate each token for dark and re-check contrast.

### Theming

- A **palette** restates **surface tokens only**. Brand, CTA, chart and status tokens are shared by every palette.
- Nothing in a component is coloured per palette. Components read tokens and nothing else.
- Offer light, dark and system modes. More palettes are optional: a branded-neutral one and a plain-neutral ("Paper") one is a good pair.

## 7. Depth

- **Light:** cards are one step brighter than the page and have a hairline border. No shadow.
- **Dark:** each layer is about 4% lighter (OKLCH L) than the one under it: rail < page < card < popover. Nothing is pure black. Borders are white at 8%. A card is "lit from above" with a 1px top highlight that fades out (`--surface-light`).
- **Only what floats** (menus, popovers, dialogs) has a shadow.
- **One emphasis ("ink") card per page** may use the inverse surface (dark on a light page), and it is the one place the brand accent may sit inside content. In dark mode it is an ordinary card.
- **Inside a card, nested lists and tiles are a fill** (muted at ~55%), never a second outline.

## 8. Surfaces: card or panel

- A **card** is a bordered box (`rounded-xl border bg-card`). Use it for peers in a grid (projects, people, stat groups) and for anything that must read as one unit at a glance.
- A **panel** is a titled section with a rule under the title and no border. Use it for the parts of one subject on one page (Trend, Recent, People).
- Panels never nest in cards and cards never nest in panels, **except** a grid of peer cards inside a panel.
- A **stat row** is **one** card that holds 2 to 4 `Stat`s in `grid-cols-2 sm:grid-cols-4`, never four separate cards.
- **One level of grouping per page.** If a block needs a card in a panel in a card, the page has too much on it.
- A page that compares (a dashboard, an overview) uses one card style throughout.

## 9. Toolbars, tables, choices

- **Toolbar** = one `FilterRow`: filters at the start, then search and view controls (Columns) pushed to the end with `ml-auto`. All controls share one height (`h-8`).
  - A select in a toolbar sizes to its content (`w-auto`). A fixed width that pushes the row onto two lines is a bug.
  - The row wraps only when the window really is narrower than the row.
- **Clear filters / selection** is an icon button at control height, named by its tooltip, shown **only while there is something to clear**. An empty state that asks the reader to clear filters keeps a worded "Clear filters" button.
- **Counts live on the control they describe** (the tab, the badge), not in a separate line of text.
- **Tables:** full width inside a bordered `rounded-lg` container.
  - One column (the name or title) grows and truncates, so the table fits the page instead of scrolling sideways.
  - Dates and numbers are `tabular-nums`. Secondary columns hide on mobile.
- **A choice between a few views** is a pill-shaped button group: `default` variant for the current view and `outline` for the rest.
- **A reorderable list** uses a drag grip per row, with no up/down arrow buttons. The grip is also the keyboard path: focus it, press Space, move with the arrow keys, press Space to drop.
- **Forms:** one form library with schema validation (e.g. react-hook-form + Zod). Field errors from the server go onto their fields first, and a toast is the fallback.

## 10. Dashboards and overviews

A dashboard answers one role's question at a glance, in this order from the top:

1. **The figures:** one stat row with 2 to 4 numbers the role acts on. Leave out a zero that really means "not set up".
2. **What needs the reader:** decisions or items waiting on them, worst first.
3. **The things they answer for:** projects, accounts or people as peer cards, worst first.
4. **Trends and history:** charts and recent activity, only when there are enough points to mean something.

Rules:

- A block appears only when it has something to say. An empty block is left out, not shown empty.
- Every figure links to the page that holds the rest. Nothing on a dashboard is entered there.
- A panel shows **at most five rows** and ends with a link to the full list, pinned to its foot. Content that doesn't fit is cut off with a fade, never scrolled inside the card.
- On a customisable dashboard, use a 4-column grid (¼, ½, ¾ or full width) with a height ceiling of 1 to 3 rows.
- **A panel with nothing to list** shows an icon, a title and one sentence, and says which of three things is true:
  - **Out of scope:** nothing is in the current filter. Say where to widen it.
  - **All clear:** there is work and nothing is wrong. Say it as good news (green tick) and keep the link.
  - **Nothing recorded yet:** a muted icon and one sentence naming who fills it in, and where.
  - Never report "all clear" over nothing.

## 11. Empty, loading, error, refused

| State | Pattern |
|---|---|
| Empty | `Empty`: an icon, a title naming what is missing, and one sentence on how it gets filled. Who can fill it decides the sentence. |
| Loading | `Skeleton`s in the shape of what is coming, inside the same frame, so the page does not jump. |
| Error | An error state with the message and a way to retry. Never a blank page. |
| Refused | An empty state that says whose page this is and where to go instead. |
| Permission-gated control | Renders nothing while permissions load, so gated controls don't flash. |

### The shared components to build first

| Component | Owns |
|---|---|
| `PageFrame` / `PageHeader` | Gutter, rhythm, title, description, actions |
| `Panel` (with `boxed` and `ink` options) | Titled section, rule, hint, action; card or ink variant |
| `Stat`, `Eyebrow`, `StatGrid` | Headline figures and micro-labels |
| `FilterRow`, `ClearButton` | Toolbars |
| `ChoiceGroup` / `SectionLinks` / `PillTabs` | Views, sub-pages, settings rail |
| `Empty`, `ErrorState`, skeletons | The non-happy states |
| `colors.ts` | `TONE_CHIP`, `TONE_TEXT`, `TONE_FILL`, `CHART_SLOTS`, `CHART_STEPS`, `CHART_REST` |

Reference recipes:

```tsx
// PageFrame
<main className="@container flex flex-col gap-6 px-6 py-6 sm:px-10 lg:px-12">
  <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
    <div className="flex min-w-0 flex-col gap-1">
      <h1 className="font-heading text-2xl leading-tight tracking-tight sm:text-3xl">{title}</h1>
      <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">{description}</p>
    </div>
    <div className="flex flex-wrap items-center gap-2">{actions}</div>
  </header>
  {children}
</main>

// Stat
<div className="flex flex-col gap-1">
  <span className="text-[0.6875rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</span>
  <span className="font-stat text-4xl leading-none">{value}</span>
  <span className="text-xs text-muted-foreground">{hint}</span>
</div>

// Boxed panel header
<section className="@container flex min-w-0 flex-col rounded-xl border bg-card">
  <div className="flex min-h-12 flex-wrap items-center justify-between gap-x-3 border-b px-5 py-2">
    <h2 className="text-sm font-semibold uppercase tracking-[0.12em]">{title}</h2>
  </div>
  <div className="flex flex-col gap-3 px-5 py-4">{children}</div>
</section>
```

## 12. Token template

Paste this into your main stylesheet after the Tailwind and shadcn imports. **Change only the lines marked `/* BRAND */`**, then re-check the contrast rules in section 13. The neutrals below are plain zero-chroma greys; to tint them warm or cool, give every neutral the same small chroma (0.003 to 0.013) at one hue.

```css
@custom-variant dark (&:is(.dark *));

@theme inline {
  --font-heading: "Your Display Face", sans-serif;   /* BRAND */
  --font-sans: "Your Text Face", sans-serif;         /* BRAND */
  --font-mono: "JetBrains Mono Variable", ui-monospace, monospace;

  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-cta: var(--cta);
  --color-cta-foreground: var(--cta-foreground);
  --color-cta-hover: var(--cta-hover);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-success: var(--success);
  --color-success-foreground: var(--success-foreground);
  --color-warning: var(--warning);
  --color-warning-foreground: var(--warning-foreground);
  --color-info: var(--info);
  --color-info-foreground: var(--info-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);
  --color-chart-6: var(--chart-6);
  --color-chart-7: var(--chart-7);
  --color-chart-8: var(--chart-8);
  --color-chart-step-1: var(--chart-step-1);
  --color-chart-step-2: var(--chart-step-2);
  --color-chart-step-3: var(--chart-step-3);
  --color-chart-step-4: var(--chart-step-4);
  --color-chart-rest: var(--chart-rest);
  --color-sidebar: var(--sidebar);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-ring: var(--sidebar-ring);

  --radius-sm: calc(var(--radius) * 0.6);
  --radius-md: calc(var(--radius) * 0.8);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) * 1.4);
  --radius-2xl: calc(var(--radius) * 1.8);
}

/* Headline figures: condensed, tabular. */
@utility font-stat {
  font-family: "Archivo Variable", "Archivo", ui-sans-serif, sans-serif;
  font-stretch: 92%;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.015em;
}

:root {
  --radius: 0.625rem;

  /* Surfaces: page < card (a step brighter), hairline borders. */
  --background: oklch(0.975 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.145 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.145 0 0);
  --secondary: oklch(0.95 0 0);
  --secondary-foreground: oklch(0.205 0 0);
  --muted: oklch(0.955 0 0);
  --muted-foreground: oklch(0.51 0 0);          /* >= 4.5:1 on page and card */
  --accent: oklch(0.95 0 0);
  --accent-foreground: oklch(0.205 0 0);
  --border: oklch(0.9 0 0);
  --input: oklch(0.9 0 0);
  --surface-light: none;

  /* Brand accent: the primary fill and the CTA pair. */
  --primary: oklch(0.55 0.2 260);               /* BRAND */
  --primary-foreground: oklch(0.985 0 0);       /* BRAND: >= 4.5:1 on --primary */
  --cta: oklch(0.55 0.2 260);                   /* BRAND: the primary button */
  --cta-foreground: oklch(0.985 0 0);           /* BRAND */
  --cta-hover: oklch(0.48 0.2 260);             /* BRAND */

  /* Focus and selection: one strong colour, >= 4.5:1 on every surface. */
  --ring: oklch(0.49 0.29 280);                 /* BRAND */

  /* Status: reserved meanings, never chart series. */
  --destructive: oklch(0.5 0.2 20);
  --destructive-foreground: oklch(0.985 0 0);
  --success: oklch(0.545 0.155 148);
  --success-foreground: oklch(0.985 0 0);
  --warning: oklch(0.545 0.145 70);
  --warning-foreground: oklch(0.985 0 0);
  --info: oklch(0.545 0.2 253);
  --info-foreground: oklch(0.985 0 0);

  /* Chart: assign in order, never cycle. 1-3 brand, 4-5 tints of 1-2, 6-8 beyond. */
  --chart-1: oklch(0.49 0.29 280);              /* BRAND */
  --chart-2: oklch(0.64 0.21 37);               /* BRAND */
  --chart-3: oklch(0.21 0.008 129);             /* BRAND */
  --chart-4: oklch(0.70 0.18 297);              /* BRAND: tint of 1 */
  --chart-5: oklch(0.74 0.16 40);               /* BRAND: tint of 2 */
  --chart-6: oklch(0.58 0.21 350);
  --chart-7: oklch(0.72 0.148 82);
  --chart-8: oklch(0.60 0.10 200);
  /* One-hue ramp for ordered states; step 4 stands out most. */
  --chart-step-1: oklch(0.70 0.18 297);
  --chart-step-2: oklch(0.59 0.25 293);
  --chart-step-3: oklch(0.49 0.29 280);
  --chart-step-4: oklch(0.38 0.23 282);
  --chart-rest: oklch(0.87 0 0);

  /* Rail: a step off the page; the active row takes the CTA pair. */
  --sidebar: oklch(0.955 0 0);
  --sidebar-foreground: oklch(0.145 0 0);
  --sidebar-primary: var(--cta);
  --sidebar-primary-foreground: var(--cta-foreground);
  --sidebar-accent: oklch(0.93 0 0);
  --sidebar-accent-foreground: oklch(0.205 0 0);
  --sidebar-border: oklch(0.9 0 0);
  --sidebar-ring: var(--ring);
}

/* Dark: lighter upward ~4% a step (rail 0.175, page 0.205, card 0.245, popover 0.28). Never pure black. */
.dark {
  --background: oklch(0.205 0 0);
  --foreground: oklch(0.94 0 0);
  --card: oklch(0.245 0 0);
  --card-foreground: oklch(0.94 0 0);
  --popover: oklch(0.28 0 0);
  --popover-foreground: oklch(0.94 0 0);
  --secondary: oklch(0.295 0 0);
  --secondary-foreground: oklch(0.94 0 0);
  --muted: oklch(0.295 0 0);
  --muted-foreground: oklch(0.74 0 0);
  --accent: oklch(0.315 0 0);
  --accent-foreground: oklch(0.94 0 0);
  --border: oklch(1 0 0 / 8%);
  --input: oklch(1 0 0 / 14%);
  --surface-light: linear-gradient(to bottom, oklch(1 0 0 / 8%) 0 1px, oklch(1 0 0 / 2.5%) 1px, transparent 6rem);

  --primary: oklch(0.68 0.17 260);              /* BRAND: lifted for dark */
  --primary-foreground: oklch(0.16 0.02 260);   /* BRAND */
  --cta: oklch(0.68 0.17 260);                  /* BRAND */
  --cta-foreground: oklch(0.16 0.02 260);       /* BRAND */
  --cta-hover: oklch(0.74 0.15 260);            /* BRAND */
  --ring: oklch(0.70 0.18 283);                 /* BRAND */

  --destructive: oklch(0.72 0.17 12);
  --destructive-foreground: oklch(0.16 0.03 25);
  --success: oklch(0.76 0.18 150);
  --success-foreground: oklch(0.16 0.03 150);
  --warning: oklch(0.82 0.165 80);
  --warning-foreground: oklch(0.18 0.03 80);
  --info: oklch(0.72 0.15 253);
  --info-foreground: oklch(0.16 0.03 253);

  --chart-1: oklch(0.59 0.25 293);              /* BRAND */
  --chart-2: oklch(0.665 0.2 38);               /* BRAND */
  --chart-3: oklch(0.90 0.05 260);              /* BRAND: light on dark */
  --chart-4: oklch(0.76 0.147 300);
  --chart-5: oklch(0.565 0.166 41);
  --chart-6: oklch(0.635 0.2 350);
  --chart-7: oklch(0.666 0.136 82);
  --chart-8: oklch(0.645 0.109 195);
  /* Ramp reversed against the dark ground: step 4 still stands out most. */
  --chart-step-1: oklch(0.49 0.29 280);
  --chart-step-2: oklch(0.59 0.25 293);
  --chart-step-3: oklch(0.70 0.18 297);
  --chart-step-4: oklch(0.81 0.11 300);
  --chart-rest: oklch(0.37 0 0);

  --sidebar: oklch(0.175 0 0);
  --sidebar-foreground: oklch(0.94 0 0);
  --sidebar-accent: oklch(0.255 0 0);
  --sidebar-accent-foreground: oklch(0.94 0 0);
  --sidebar-border: oklch(1 0 0 / 8%);
}

/* Cards lit from above in dark; nested lists inside a card are a fill. */
@layer components {
  [data-slot="card"], [data-slot="panel-card"] { background-image: var(--surface-light); }
  [data-slot="panel-card"] [data-slot="row-list"] {
    border-color: transparent;
    background-color: color-mix(in oklab, var(--muted) 55%, transparent);
  }
}

@layer base {
  * { @apply border-border outline-ring/50; }
  ::selection { background-color: color-mix(in oklab, var(--ring) 28%, transparent); }
  body { @apply min-w-[320px] bg-background text-foreground; }
  html { @apply font-sans; }
}
```

Why OKLCH: its L channel is perceptual, so "each layer 4% lighter" and "tints at the same hue" behave predictably, and contrast is easier to reason about than in HSL.

## 13. Palette swap checklist

Run through this after changing the `/* BRAND */` values:

- [ ] `--primary-foreground` on `--primary`, and `--cta-foreground` on `--cta`: at least 4.5:1, in light and dark.
- [ ] If the accent is light (neon, yellow, lime), the light-mode CTA is **dark with accent text**, and the accent fill is kept for dark mode. Light text on a light accent never passes.
- [ ] The accent is never body text on a light surface.
- [ ] `--ring`: at least 4.5:1 against background, card, popover and sidebar in both modes. If the accent fails, pick a different focus colour.
- [ ] `--muted-foreground`: at least 4.5:1 on page and card in both modes.
- [ ] Status colours: at least 4.5:1 as text on page and card in both modes, and none of them is close in hue to a chart slot from 1 to 3.
- [ ] Chart slots 1 to 4: distinguishable for all pairs under deuteranopia and protanopia simulation, and adjacent slots 5 to 8 distinguishable.
- [ ] The active sidebar row uses the CTA pair and reads as selected on the rail colour.
- [ ] Dark surfaces climb in about 4% L steps with nothing at L = 0.

## 14. Review checklist for a new page

- [ ] Renders through `PageFrame`, has a 1 to 3 word title and an optional one-sentence description.
- [ ] At most one filled button.
- [ ] Gaps come only from the scale (6, 4, 3, 1), with no child margins used to fix spacing.
- [ ] Radii come only from `xl`, `lg` and `full`, matched to the shape.
- [ ] Filters are on the page, not in a card, and the toolbar stays on one row at desktop width.
- [ ] No card in a panel in a card. A stat row is one card.
- [ ] No coloured text that doesn't carry a meaning, and every tone has a word or icon beside it.
- [ ] Chart series use slots in order, with no status colours.
- [ ] Empty, loading, error and refused states are all designed.
- [ ] Reads correctly in light and dark, keyboard-reachable, with a visible focus ring everywhere.
- [ ] Numbers and dates use `tabular-nums`.