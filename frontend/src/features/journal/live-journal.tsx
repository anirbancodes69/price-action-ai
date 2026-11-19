"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { ErrorState } from "@/components/data/error-state";
import { TableSkeleton } from "@/components/data/loading-skeleton";
import { ApiError } from "@/lib/api/client";
import { fetchJournal, saveJournalNotes } from "@/lib/api/journal";
import { fetchPositions } from "@/lib/api/trades";
import type { DataMode } from "@/lib/api/scanner";
import type { JournalEntry } from "@/types";
import { JournalView } from "./journal-view";

/** Journal fed by `GET /api/v1/journal` (HTTP mode): the closed trades you logged, with notes saved on the server. */
export function LiveJournal() {
  const router = useRouter();
  const [state, setState] = useState<{ entries: JournalEntry[]; mode: DataMode } | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const [entries, live] = await Promise.all([fetchJournal(signal), fetchPositions(signal)]);
        setState({ entries, mode: live.dataMode });
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
    return () => {
      ctl.abort();
      window.clearTimeout(first);
    };
  }, [load]);

  if (!state) {
    return (
      <PageFrame>
        <PageHeader title="Trading Journal" description="Review closed trades and learn from your execution." />
        {error ? <ErrorState title="Your journal is not available" message="It could not be loaded. Nothing was changed." onRetry={() => void load()} /> : <TableSkeleton />}
      </PageFrame>
    );
  }
  return <JournalView initial={state.entries} asOf={new Date().toISOString()} mode={state.mode} onSaveNotes={saveJournalNotes} />;
}
