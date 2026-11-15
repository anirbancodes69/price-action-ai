"use client";

import { cn } from "@/lib/utils";

interface SegmentedProps<T extends string> {
  options: { value: T; label: string; disabled?: boolean }[];
  value: T;
  onChange: (v: T) => void;
  size?: "xs" | "sm";
  ariaLabel: string;
  className?: string;
}

/** Compact radio group, e.g. timeframe or filter selectors. */
export function Segmented<T extends string>({ options, value, onChange, size = "sm", ariaLabel, className }: SegmentedProps<T>) {
  return (
    <div role="radiogroup" aria-label={ariaLabel} className={cn("inline-flex rounded border border-border bg-subtle p-0.5", className)}>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={o.disabled}
            onClick={() => onChange(o.value)}
            className={cn(
              "tnum rounded-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40",
              size === "xs" ? "h-5 px-1.5 text-2xs" : "h-6 px-2 text-xs",
              active ? "bg-raised text-fg shadow-sm" : "text-fg-muted hover:text-fg",
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
