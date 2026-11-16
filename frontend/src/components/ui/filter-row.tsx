"use client";

import type { ReactNode } from "react";
import { FilterX, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { Tooltip } from "./tooltip";

/**
 * Toolbar (design-standards §9): one row on the page — never inside a card.
 * Filters at the start; search and view controls pushed to the end. Every
 * control is `h-8`; selects size to their content. The row wraps only when
 * the window is narrower than its content.
 */
export function FilterRow({ children, end, className, label = "Filters" }: { children?: ReactNode; end?: ReactNode; className?: string; label?: string }) {
  return (
    <div role="toolbar" aria-label={label} className={cn("flex flex-wrap items-center gap-2", className)}>
      {children}
      {end && <div className="ml-auto flex flex-wrap items-center gap-2 max-sm:w-full">{end}</div>}
    </div>
  );
}

/**
 * Clear filters / selection: an icon button at control height, named by its
 * tooltip, rendered only while there is something to clear.
 */
export function ClearButton({ show, onClear, label = "Clear filters" }: { show: boolean; onClear: () => void; label?: string }) {
  if (!show) return null;
  return (
    <Tooltip content={label} side="bottom">
      <button
        type="button"
        onClick={onClear}
        aria-label={label}
        className="inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        <FilterX className="size-4" aria-hidden />
      </button>
    </Tooltip>
  );
}

/** Toolbar search field at control height. */
export function SearchField({
  value,
  onChange,
  placeholder,
  label,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  label: string;
  className?: string;
}) {
  return (
    <div className={cn("relative w-full sm:w-56", className)}>
      <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
      <input
        type="search"
        aria-label={label}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 w-full rounded-lg border border-input bg-card pl-8 pr-2.5 text-sm text-foreground placeholder:text-muted-foreground hover:border-muted-foreground dark:bg-input/30"
      />
    </div>
  );
}
