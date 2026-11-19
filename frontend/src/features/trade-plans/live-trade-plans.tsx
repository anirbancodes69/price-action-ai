"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { ErrorState } from "@/components/data/error-state";
import { TableSkeleton } from "@/components/data/loading-skeleton";
import { ApiError } from "@/lib/api/client";
import { fetchPositions } from "@/lib/api/trades";
import { cancelTradePlan, fetchTradePlans } from "@/lib/api/trade-plans";
import type { DataMode } from "@/lib/api/scanner";
import type { TradePlan } from "@/types";
import { TradePlansView } from "./trade-plans-view";

/** Trade plans in HTTP mode (T1, T5): the plans you wrote from live setups, cancelled on the server. */
export function LiveTradePlans() {
  const router = useRouter();
  const [state, setState] = useState<{ plans: TradePlan[]; mode: DataMode } | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const [plans, live] = await Promise.all([fetchTradePlans(signal), fetchPositions(signal)]);
        setState({ plans, mode: live.dataMode });
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
        <PageHeader title="Trade Plans" description="Proposed plans you have written against detected setups. A plan is not an order." />
        {error ? <ErrorState title="Your plans are not available" message="They could not be loaded. Nothing was changed." onRetry={() => void load()} /> : <TableSkeleton />}
      </PageFrame>
    );
  }
  return (
    <TradePlansView
      initial={state.plans}
      asOf={new Date().toISOString()}
      mode={state.mode}
      onCancel={async (p) => {
        if (p.apiId) await cancelTradePlan(p.apiId);
      }}
    />
  );
}
