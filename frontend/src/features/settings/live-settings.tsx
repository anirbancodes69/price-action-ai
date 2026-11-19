"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { ErrorState } from "@/components/data/error-state";
import { TableSkeleton } from "@/components/data/loading-skeleton";
import { ApiError } from "@/lib/api/client";
import {
  fetchRiskProfile,
  saveRiskProfile,
  type LoadedRiskProfile,
} from "@/lib/api/risk-profile";
import type { UserProfile } from "@/types";
import { SettingsView } from "./settings-view";

/** Settings with the risk section stored through `GET/PUT /api/v1/risk-profile` (HTTP mode). Other sections stay sample. */
export function LiveSettings({ user }: { user: UserProfile }) {
  const router = useRouter();
  const [loaded, setLoaded] = useState<LoadedRiskProfile | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const keep = useRef<Pick<LoadedRiskProfile, "minRr" | "maxEntryGapPct">>({
    minRr: null,
    maxEntryGapPct: null,
  });

  const load = async (signal?: AbortSignal) => {
    try {
      const p = await fetchRiskProfile(signal);
      keep.current = { minRr: p.minRr, maxEntryGapPct: p.maxEntryGapPct };
      setLoaded(p);
      setError(null);
    } catch (e) {
      if (signal?.aborted) return;
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/login");
        return;
      }
      setError(e instanceof Error ? e : new Error("Load failed"));
    }
  };

  useEffect(() => {
    const ctl = new AbortController();
    const first = window.setTimeout(() => void load(ctl.signal), 0);
    return () => {
      ctl.abort();
      window.clearTimeout(first);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- loads once; `load` only closes over stable refs and setters
  }, []);

  if (!loaded) {
    return (
      <PageFrame>
        <PageHeader
          title="Settings"
          description="Your account, preferences and risk limits."
        />
        {error ? (
          <ErrorState
            title="Settings are not available"
            message="They could not be loaded. Nothing was changed."
            onRetry={() => void load()}
          />
        ) : (
          <TableSkeleton />
        )}
      </PageFrame>
    );
  }
  return (
    <SettingsView
      user={user}
      liveRisk={{
        initial: loaded.form,
        onSave: async (form) => {
          const saved = await saveRiskProfile(form, keep.current);
          keep.current = {
            minRr: saved.minRr,
            maxEntryGapPct: saved.maxEntryGapPct,
          };
          return saved.form;
        },
      }}
    />
  );
}
