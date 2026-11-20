"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/data/error-state";
import { errorReference } from "@/lib/api/error-reference";

/** Route error boundary for onboarding (UIA-12, ENG-06): retry, reference only. */
export default function OnboardingError({ error, retry }: { error: unknown; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <main className="flex min-h-dvh items-center justify-center bg-background px-6">
      <div data-slot="card" className="w-full max-w-md rounded-xl border bg-card">
        <ErrorState
          title="Setup could not be loaded"
          message="Something went wrong while preparing this step. Nothing was saved. Try again."
          reference={errorReference(error)}
          onRetry={retry}
        />
      </div>
    </main>
  );
}
