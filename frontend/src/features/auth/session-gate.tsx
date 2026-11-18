"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { ErrorState } from "@/components/data/error-state";
import { ApiError } from "@/lib/api/client";
import { getMe } from "@/lib/api/auth";
import { USE_HTTP } from "@/lib/api/config";

/**
 * With the HTTP data source the workspace needs a session. The server cannot see the session cookie of the
 * Laravel API from here, so the check runs in the browser: no session, no workspace (redirect to sign in).
 * With the mock data source the state starts as `ok` and nothing is hidden.
 */
export function SessionGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<"checking" | "ok" | "error">(USE_HTTP ? "checking" : "ok");

  useEffect(() => {
    if (!USE_HTTP) return;
    const ctl = new AbortController();
    getMe(ctl.signal)
      .then(() => setState("ok"))
      .catch((e: unknown) => {
        if (ctl.signal.aborted) return;
        if (e instanceof ApiError && e.status === 401) router.replace("/login");
        else setState("error");
      });
    return () => ctl.abort();
  }, [router]);

  // The children are always rendered (and hidden until the session is confirmed): pages that read `params` for
  // metadata must stay in the prerendered shell, and everything outside the scanner is sample data in this mode.
  return (
    <>
      {state === "error" && (
        <div className="flex min-h-svh items-center justify-center">
          <ErrorState title="Could not verify your session" message="The server did not answer. Your data is unchanged." onRetry={() => window.location.reload()} />
        </div>
      )}
      {state === "checking" && <div className="min-h-svh bg-background" aria-busy="true" aria-label="Checking your session" role="status" />}
      <div hidden={state !== "ok"}>{children}</div>
    </>
  );
}
