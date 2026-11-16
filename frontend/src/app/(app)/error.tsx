"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/data/error-state";
import { PageFrame } from "@/components/layout/page-frame";

/**
 * Route error boundary for the authenticated app (PRD-07 §8, UIA-12).
 * Shows the message and a retry, never a blank page. Only the digest is
 * shown, never the error text, so server details are not leaked (ENG-06).
 */
export default function AppError({ error, retry }: { error: unknown; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  const digest = error instanceof Error && "digest" in error ? String((error as Error & { digest?: string }).digest ?? "") : "";
  return (
    <PageFrame>
      <div data-slot="card" className="rounded-xl border bg-card">
        <ErrorState
          title="This page could not be loaded"
          message="Something went wrong while preparing this view. Nothing was changed. Try again, or open another page from the sidebar."
          reference={digest || undefined}
          onRetry={retry}
        />
      </div>
    </PageFrame>
  );
}
