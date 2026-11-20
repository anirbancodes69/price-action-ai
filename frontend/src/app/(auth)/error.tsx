"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/data/error-state";
import { errorReference } from "@/lib/api/error-reference";

/** Route error boundary for sign-in, registration and password reset (UIA-12, ENG-06): retry, reference only. */
export default function AuthError({ error, retry }: { error: unknown; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <div data-slot="card" className="rounded-xl border bg-card">
      <ErrorState
        title="This page could not be loaded"
        message="Something went wrong. Nothing was changed and you were not signed in or out. Try again."
        reference={errorReference(error)}
        onRetry={retry}
      />
    </div>
  );
}
