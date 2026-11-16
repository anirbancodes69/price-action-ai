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
  /**
   * The one column that grows and truncates (the name or title) so the
   * table fits the page instead of scrolling sideways (design-standards §9).
   */
  grow?: boolean;
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
  /** Rows to show; the rest is reached through the panel's footer link (dashboards: 5). */
  limit?: number;
}

const HIDE = {
  sm: "hidden sm:table-cell",
  md: "hidden md:table-cell",
  lg: "hidden lg:table-cell",
  xl: "hidden xl:table-cell",
  "2xl": "hidden 2xl:table-cell",
};

const ALIGN = { left: "text-left", right: "text-right", center: "text-center" };

/**
 * Sortable financial data table, full width in a bordered `rounded-lg`
 * container (design-standards §9). Numbers are tabular; secondary columns
 * hide on narrow screens via `hideBelow`; horizontal scroll stays inside the
 * container as a last resort only.
 */
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
  limit,
}: DataTableProps<T>) {
  const { sorted, sort, toggle } = useSort<T, string>(
    rows,
    (row, key) => columns.find((c) => c.key === key)?.sortValue?.(row) ?? 0,
    initialSort ? { key: initialSort.key, dir: initialSort.dir } : undefined,
  );

  return (
    <div className={cn("relative w-full overflow-x-auto rounded-lg border bg-card", className)}>
      <table className="w-full border-collapse text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr>
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
                    "h-9 whitespace-nowrap border-b bg-muted px-2 text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground first:pl-3 last:pr-3 sm:px-3 sm:first:pl-4 sm:last:pr-4",
                    ALIGN[col.align ?? "left"],
                    col.hideBelow && HIDE[col.hideBelow],
                    col.sticky && "sticky left-0 z-10",
                    col.grow && "w-full",
                    col.className,
                  )}
                >
                  {sortable ? (
                    <button
                      type="button"
                      onClick={() => toggle(col.key)}
                      className={cn(
                        "inline-flex items-center gap-1 rounded-lg uppercase tracking-[0.14em] transition-colors hover:text-foreground",
                        active && "text-foreground",
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
          {(limit ? sorted.slice(0, limit) : sorted).map((row) => (
            <tr
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn(
                "group border-b transition-colors last:border-0 hover:bg-accent",
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
                    col.align === "right" && "tabular-nums",
                    col.hideBelow && HIDE[col.hideBelow],
                    col.sticky && "sticky left-0 z-10 bg-card group-hover:bg-accent",
                    col.grow && "w-full max-w-0 overflow-hidden",
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
