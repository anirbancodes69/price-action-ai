"use client";

import { RotateCcw, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Error state (design-standards §11): the message and a way to retry, never
 * a blank page. A request/digest id is shown so support can match logs
 * (ENG-06), never a stack trace.
 */
export function ErrorState({
  title = "Something went wrong",
  message = "This view could not be loaded. Your data is unchanged.",
  reference,
  onRetry,
  className,
}: {
  title?: string;
  message?: string;
  reference?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div role="alert" className={cn("flex flex-col items-center justify-center gap-3 px-6 py-12 text-center", className)}>
      <span className="flex size-10 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <TriangleAlert className="size-5" aria-hidden />
      </span>
      <div className="flex max-w-sm flex-col gap-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="text-sm text-muted-foreground">{message}</p>
        {reference && <p className="font-mono text-xs text-muted-foreground">Reference {reference}</p>}
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCcw /> Try again
        </Button>
      )}
    </div>
  );
}
