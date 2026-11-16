"use client";

import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SectionLink<T extends string> {
  value: T;
  label: ReactNode;
  icon?: LucideIcon;
  count?: number;
}

interface SectionLinksProps<T extends string> {
  items: SectionLink<T>[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
  className?: string;
}

/**
 * A rail of sections on one page (Settings, a list of watchlists): vertical
 * from `md`, a horizontally scrolling row below it. The current row takes
 * the selection fill, like the sidebar's active row but one level quieter.
 */
export function SectionLinks<T extends string>({ items, value, onChange, ariaLabel, className }: SectionLinksProps<T>) {
  return (
    <nav aria-label={ariaLabel} className={cn("min-w-0", className)}>
      <ul className="no-scrollbar flex gap-1 overflow-x-auto md:flex-col md:overflow-visible">
        {items.map((s) => {
          const Icon = s.icon;
          const on = value === s.value;
          return (
            <li key={s.value} className="shrink-0">
              <button
                type="button"
                onClick={() => onChange(s.value)}
                aria-current={on ? "true" : undefined}
                className={cn(
                  "flex h-8 w-full items-center gap-2 rounded-lg px-2.5 text-left text-sm transition-colors",
                  on ? "bg-accent font-medium text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                )}
              >
                {Icon && <Icon className="size-4 shrink-0" aria-hidden />}
                <span className="min-w-0 flex-1 truncate">{s.label}</span>
                {s.count !== undefined && <span className="text-xs text-muted-foreground">{s.count}</span>}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
