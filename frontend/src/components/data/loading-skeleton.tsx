import { cn } from "@/lib/utils";

/**
 * Skeletons in the shape of what is coming, inside the same frame, so the
 * page does not jump (design-standards §11). A skeleton takes the radius of
 * the thing it stands in for: `rounded-lg` for a control or text line,
 * `rounded-xl` for a card, `rounded-full` for a chip.
 */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-lg bg-muted", className)} aria-hidden />;
}

/** Stat row placeholder: one card with N figures. */
export function StatGridSkeleton({ count = 4 }: { count?: 2 | 3 | 4 }) {
  return (
    <div className={cn("grid gap-x-6 gap-y-5 rounded-xl border bg-card px-6 py-5", count === 4 ? "grid-cols-2 sm:grid-cols-4" : count === 3 ? "grid-cols-2 sm:grid-cols-3" : "grid-cols-2")}>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="flex flex-col gap-1">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-3 w-28" />
        </div>
      ))}
    </div>
  );
}

/** Table placeholder inside the table's bordered container. */
export function TableSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="flex flex-col overflow-hidden rounded-lg border bg-card" role="status" aria-label="Loading table">
      <div className="h-9 border-b bg-muted/50" />
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex h-11 items-center gap-4 border-b px-4 last:border-0">
          <Skeleton className="h-3.5 w-24" />
          <Skeleton className="h-3.5 flex-1" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
      ))}
    </div>
  );
}

/** Chart placeholder sized by its container. */
export function ChartSkeleton() {
  return (
    <div className="flex h-full min-h-80 flex-col gap-3 p-4" role="status" aria-label="Loading chart">
      <Skeleton className="h-4 w-48" />
      <Skeleton className="flex-1 rounded-xl" />
    </div>
  );
}

/** Route-level placeholder in the PageFrame shape: header, stat row, content. */
export function PageSkeleton() {
  return (
    <div className="flex flex-col gap-6 px-6 py-6 sm:px-10 lg:px-12" role="status" aria-label="Loading page">
      <div className="flex flex-col gap-1">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-80 max-w-full" />
      </div>
      <StatGridSkeleton />
      <TableSkeleton />
    </div>
  );
}
