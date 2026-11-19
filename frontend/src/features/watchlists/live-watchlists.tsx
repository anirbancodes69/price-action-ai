"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { ErrorState } from "@/components/data/error-state";
import { TableSkeleton } from "@/components/data/loading-skeleton";
import { ApiError } from "@/lib/api/client";
import { fetchScanner } from "@/lib/api/scanner";
import type { ScannerRow } from "@/types";
import { WatchlistsView } from "./watchlists-view";

const POLL_MS = 30_000;

/** Watchlists in HTTP mode: the lists come from the store (server-backed); their structure and setups from the live scan. */
export function LiveWatchlists() {
  const router = useRouter();
  const [state, setState] = useState<{ rows: ScannerRow[]; asOf: string } | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const { rows, meta } = await fetchScanner(signal);
        setState({ rows, asOf: meta.asOf ?? new Date().toISOString() });
        setError(null);
      } catch (e) {
        if (signal?.aborted) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
          return;
        }
        setError(e instanceof Error ? e : new Error("Load failed"));
      }
    },
    [router],
  );

  useEffect(() => {
    const ctl = new AbortController();
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

  if (!state) {
    return (
      <PageFrame>
        <PageHeader title="Watchlists" description="Track the stocks you follow and see their structure and setup status at a glance." />
        {error ? <ErrorState title="Watchlists are not available" message="The live scan could not be loaded. Your lists are unchanged." onRetry={() => void load()} /> : <TableSkeleton />}
      </PageFrame>
    );
  }
  return <WatchlistsView rows={state.rows} asOf={state.asOf} />;
}
