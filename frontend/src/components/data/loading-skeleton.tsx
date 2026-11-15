import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-shimmer rounded bg-hover", className)} aria-hidden />;
}

/** Generic page-level loading placeholder used by route `loading.tsx` files. */
export function LoadingSkeleton({ variant = "page" }: { variant?: "page" | "table" | "chart" }) {
  if (variant === "chart") {
    return (
      <div className="flex h-full min-h-80 flex-col gap-3 p-4" role="status" aria-label="Loading chart">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="flex-1" />
      </div>
    );
  }
  if (variant === "table") {
    return (
      <div className="flex flex-col gap-2 p-4" role="status" aria-label="Loading table">
        {Array.from({ length: 8 }, (_, i) => (
          <Skeleton key={i} className="h-8 w-full" />
        ))}
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-4 p-4 md:p-6" role="status" aria-label="Loading page">
      <Skeleton className="h-7 w-64" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-80" />
    </div>
  );
}
