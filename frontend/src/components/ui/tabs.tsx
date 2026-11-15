"use client";

import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface TabItem<T extends string = string> {
  value: T;
  label: ReactNode;
  count?: number;
}

interface TabsProps<T extends string> {
  items: TabItem<T>[];
  value: T;
  onChange: (value: T) => void;
  variant?: "underline" | "pill";
  size?: "sm" | "md";
  className?: string;
  ariaLabel?: string;
}

/** Controlled tab list with roving keyboard focus (←/→/Home/End). */
export function Tabs<T extends string>({
  items,
  value,
  onChange,
  variant = "underline",
  size = "md",
  className,
  ariaLabel,
}: TabsProps<T>) {
  const id = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKey = (e: KeyboardEvent, i: number) => {
    let next = -1;
    if (e.key === "ArrowRight") next = (i + 1) % items.length;
    if (e.key === "ArrowLeft") next = (i - 1 + items.length) % items.length;
    if (e.key === "Home") next = 0;
    if (e.key === "End") next = items.length - 1;
    if (next < 0) return;
    e.preventDefault();
    refs.current[next]?.focus();
    onChange(items[next].value);
  };

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        "no-scrollbar flex items-center overflow-x-auto",
        variant === "underline" ? "gap-4 border-b border-border" : "gap-0.5 rounded-md border border-border bg-subtle p-0.5",
        className,
      )}
    >
      {items.map((item, i) => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            id={`${id}-${item.value}`}
            role="tab"
            type="button"
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(item.value)}
            onKeyDown={(e) => onKey(e, i)}
            className={cn(
              "inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap font-medium transition-colors",
              size === "sm" ? "text-xs" : "text-[13px]",
              variant === "underline"
                ? cn(
                    "-mb-px border-b-2 pb-2.5 pt-1",
                    active ? "border-accent text-fg" : "border-transparent text-fg-muted hover:text-fg",
                  )
                : cn(
                    "rounded px-2.5",
                    size === "sm" ? "h-6" : "h-7",
                    active ? "bg-raised text-fg shadow-sm" : "text-fg-muted hover:text-fg",
                  ),
            )}
          >
            {item.label}
            {item.count !== undefined && (
              <span
                className={cn(
                  "tnum rounded-sm px-1 text-2xs",
                  active ? "bg-accent/15 text-accent" : "bg-hover text-fg-subtle",
                )}
              >
                {item.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
