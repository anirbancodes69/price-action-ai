"use client";

import Link from "next/link";
import { useRef, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * A choice between a few views (design-standards §9): a pill-shaped button
 * group, filled for the current view and outline for the rest. Counts live
 * on the control they describe.
 *
 * Exposed as a radio group with roving focus (←/→/Home/End), so it is one
 * tab stop and the arrow keys move the selection.
 */

export interface Choice<T extends string> {
  value: T;
  label: ReactNode;
  count?: number;
  disabled?: boolean;
  /** Leading glyph that carries meaning (e.g. a bias dot); text still names it. */
  icon?: ReactNode;
  /** Tooltip/explanation for a disabled choice. */
  title?: string;
}

interface ChoiceGroupProps<T extends string> {
  options: Choice<T>[];
  value: T;
  onChange: (v: T) => void;
  ariaLabel: string;
  size?: "sm" | "md";
  className?: string;
}

const pill = (active: boolean, size: "sm" | "md") =>
  cn(
    "inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border font-medium transition-colors",
    "disabled:cursor-not-allowed disabled:opacity-50",
    size === "sm" ? "h-7 px-2.5 text-xs" : "h-8 px-3 text-sm",
    active ? "border-cta bg-cta text-cta-foreground" : "border-input bg-card text-foreground hover:bg-accent",
  );

const countCls = (active: boolean) => cn("text-xs", active ? "text-cta-foreground/80" : "text-muted-foreground");

export function ChoiceGroup<T extends string>({ options, value, onChange, ariaLabel, size = "md", className }: ChoiceGroupProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const enabled = options.map((o, i) => (o.disabled ? -1 : i)).filter((i) => i >= 0);

  const onKey = (e: KeyboardEvent, i: number) => {
    const pos = enabled.indexOf(i);
    let next = -1;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = enabled[(pos + 1) % enabled.length];
    if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = enabled[(pos - 1 + enabled.length) % enabled.length];
    if (e.key === "Home") next = enabled[0];
    if (e.key === "End") next = enabled[enabled.length - 1];
    if (next === undefined || next < 0) return;
    e.preventDefault();
    refs.current[next]?.focus();
    onChange(options[next].value);
  };

  return (
    <div role="radiogroup" aria-label={ariaLabel} className={cn("flex flex-wrap items-center gap-1", className)}>
      {options.map((o, i) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            disabled={o.disabled}
            title={o.title}
            onClick={() => onChange(o.value)}
            onKeyDown={(e) => onKey(e, i)}
            className={pill(active, size)}
          >
            {o.icon}
            {o.label}
            {o.count !== undefined && <span className={countCls(active)}>{o.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Routed sub-pages, up to three (§2): the same pill group rendered as links.
 * Four or more routed sub-pages use underlined <Tabs> instead.
 */
export function PillTabs({
  items,
  current,
  ariaLabel,
  className,
}: {
  items: { href: string; label: ReactNode; count?: number }[];
  current: string;
  ariaLabel: string;
  className?: string;
}) {
  return (
    <nav aria-label={ariaLabel} className={cn("flex flex-wrap items-center gap-1", className)}>
      {items.map((it) => {
        const active = it.href === current;
        return (
          <Link key={it.href} href={it.href} aria-current={active ? "page" : undefined} className={pill(active, "md")}>
            {it.label}
            {it.count !== undefined && <span className={countCls(active)}>{it.count}</span>}
          </Link>
        );
      })}
    </nav>
  );
}
