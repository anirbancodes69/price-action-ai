"use client";

import type { ReactNode } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useSort } from "@/hooks/use-sort";
import { cn } from "@/lib/utils";

export interface Column<T> {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  /** Return a value to make the column sortable. */
  sortValue?: (row: T) => string | number;
  align?: "left" | "right" | "center";
  /** Hide on narrow screens to keep tables readable on mobile. */
  hideBelow?: "sm" | "md" | "lg" | "xl" | "2xl";
  className?: string;
  /** Pin this column to the left while scrolling horizontally. */
  sticky?: boolean;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  empty?: ReactNode;
  initialSort?: { key: string; dir: "asc" | "desc" };
  dense?: boolean;
  className?: string;
  caption?: string;
}

const HIDE = {
  sm: "hidden sm:table-cell",
  md: "hidden md:table-cell",
  lg: "hidden lg:table-cell",
  xl: "hidden xl:table-cell",
  "2xl": "hidden 2xl:table-cell",
};

const ALIGN = { left: "text-left", right: "text-right", center: "text-center" };

/** Dense, sortable financial data table. Scrolls horizontally inside its container only. */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  empty,
  initialSort,
  dense = true,
  className,
  caption,
}: DataTableProps<T>) {
  const { sorted, sort, toggle } = useSort<T, string>(
    rows,
    (row, key) => columns.find((c) => c.key === key)?.sortValue?.(row) ?? 0,
    initialSort ? { key: initialSort.key, dir: initialSort.dir } : undefined,
  );

  return (
    <div className={cn("relative w-full overflow-x-auto", className)}>
      <table className="w-full border-collapse text-[13px]">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr className="border-b border-border">
            {columns.map((col) => {
              const sortable = !!col.sortValue;
              const active = sort.key === col.key;
              const SortIcon = !active ? ArrowUpDown : sort.dir === "asc" ? ArrowUp : ArrowDown;
              return (
                <th
                  key={col.key}
                  scope="col"
                  aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : undefined}
                  className={cn(
                    "h-8 whitespace-nowrap bg-surface px-2 text-2xs font-medium uppercase tracking-wider text-fg-subtle first:pl-3 last:pr-3 sm:px-3 sm:first:pl-4 sm:last:pr-4",
                    ALIGN[col.align ?? "left"],
                    col.hideBelow && HIDE[col.hideBelow],
                    col.sticky && "sticky left-0 z-10",
                    col.className,
                  )}
                >
                  {sortable ? (
                    <button
                      type="button"
                      onClick={() => toggle(col.key)}
                      className={cn(
                        "inline-flex items-center gap-1 uppercase tracking-wider transition-colors hover:text-fg",
                        active && "text-fg-muted",
                        col.align === "right" && "flex-row-reverse",
                      )}
                    >
                      {col.header}
                      <SortIcon className={cn("size-3", !active && "opacity-40")} aria-hidden />
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn(
                "group border-b border-border/60 transition-colors last:border-0 hover:bg-hover/50",
                onRowClick && "cursor-pointer",
              )}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn(
                    "whitespace-nowrap px-2 first:pl-3 last:pr-3 sm:px-3 sm:first:pl-4 sm:last:pr-4",
                    dense ? "h-10" : "h-12",
                    ALIGN[col.align ?? "left"],
                    col.align === "right" && "tnum",
                    col.hideBelow && HIDE[col.hideBelow],
                    col.sticky && "sticky left-0 z-10 bg-surface group-hover:bg-[color-mix(in_srgb,var(--color-surface)_50%,var(--color-hover))]",
                    col.className,
                  )}
                >
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {sorted.length === 0 && empty}
    </div>
  );
}
