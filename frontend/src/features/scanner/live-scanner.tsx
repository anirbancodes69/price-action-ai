"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { ErrorState } from "@/components/data/error-state";
import { TableSkeleton } from "@/components/data/loading-skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { fetchScanner, type ScannerMeta } from "@/lib/api/scanner";
import type { ScannerRow } from "@/types";
import { ScannerView } from "./scanner-view";

/** How often the scan is refreshed while the tab is visible. A 5m bar changes the data at most every 5 minutes. */
export const POLL_MS = 30_000;

/**
 * Scanner fed by `GET /api/v1/scanner` (live engine proxy, ADR-016). Polls while the tab is visible, keeps the last
 * good result when a refresh fails, and sends an expired session back to the sign-in page.
 */
export function LiveScanner() {
  const router = useRouter();
  const toast = useToast();
  const [result, setResult] = useState<{ rows: ScannerRow[]; meta: ScannerMeta } | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const warned = useRef(false);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setRefreshing(true);
      try {
        setResult(await fetchScanner(signal));
        setError(null);
        warned.current = false;
      } catch (e) {
        if (signal?.aborted) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
          return;
        }
        setError(e instanceof Error ? e : new Error("Scan failed"));
        if (!warned.current) {
          warned.current = true;
          toast({ title: "Could not refresh the scan", description: "Showing the last result.", tone: "warn" });
        }
      } finally {
        setRefreshing(false);
      }
    },
    [router, toast],
  );

  useEffect(() => {
    const ctl = new AbortController();
    // Deferred so the effect body itself sets no state (react-hooks/set-state-in-effect).
    const first = window.setTimeout(() => void load(ctl.signal), 0);
    const tick = () => {
      if (document.visibilityState === "visible") void load();
    };
    const id = window.setInterval(tick, POLL_MS);
    document.addEventListener("visibilitychange", tick);
    return () => {
      ctl.abort();
      window.clearTimeout(first);
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [load]);

  if (!result) {
    return (
      <PageFrame>
        <PageHeader title="Market Scanner" description="Scanning the universe on the latest closed bars…" />
        {error ? (
          <ErrorState
            title="The scanner is not available"
            message={error instanceof ApiError ? errorMessage(error) : "The scan could not be loaded."}
            reference={error instanceof ApiError ? error.requestId : undefined}
            onRetry={() => void load()}
          />
        ) : (
          <TableSkeleton />
        )}
      </PageFrame>
    );
  }

  return (
    <ScannerView
      rows={result.rows}
      asOf={result.meta.asOf ?? new Date().toISOString()}
      live={{ mode: result.meta.dataMode, refreshing, onRefresh: () => void load(), nextBarClose: result.meta.nextBarClose }}
    />
  );
}

function errorMessage(e: ApiError): string {
  switch (e.code) {
    case "ENGINE_UNAVAILABLE":
      return "The analysis engine is not reachable. Your data is unchanged.";
    case "NO_DATA_SOURCE":
      return "No data source is configured yet.";
    case "RULESET_UNAVAILABLE":
      return "No active ruleset is configured.";
    case "RATE_LIMITED":
      return "Too many requests. Wait a moment and try again.";
    default:
      return "This view could not be loaded. Your data is unchanged.";
  }
}
