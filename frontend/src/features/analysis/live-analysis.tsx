"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { ErrorState } from "@/components/data/error-state";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { analysisProblem, fetchAnalysis, mapAnalysis, type AnalysisMeta, type ApiAnalysisRun } from "@/lib/api/analysis";
import { createTradePlan } from "@/lib/api/trade-plans";
import { AnalysisView } from "./analysis-view";

/** Same cadence as the scanner: a 5m bar changes the analysis at most every 5 minutes. */
const POLL_MS = 30_000;

/**
 * Analysis of one symbol fed by `GET /api/v1/analysis/{symbol}` (live engine proxy, ADR-016). Polls while the tab is
 * visible, keeps the last good result when a refresh fails, and sends an expired session back to the sign-in page.
 */
export function LiveAnalysis({ symbol }: { symbol: string }) {
  const router = useRouter();
  const toast = useToast();
  const [result, setResult] = useState<{ run: ApiAnalysisRun; meta: AnalysisMeta } | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const warned = useRef(false);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        setResult(await fetchAnalysis(symbol, signal));
        setError(null);
        warned.current = false;
      } catch (e) {
        if (signal?.aborted) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
          return;
        }
        setError(e instanceof Error ? e : new Error("Analysis failed"));
        if (!warned.current) {
          warned.current = true;
          toast({ title: "Could not refresh the analysis", description: "Showing the last result.", tone: "warn" });
        }
      }
    },
    [symbol, router, toast],
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

  const title = symbol.toUpperCase();
  const problem = result ? analysisProblem(result.run) : null;

  if (!result || problem) {
    return (
      <PageFrame>
        <PageHeader title={title} description="Analysis on the latest closed bars" />
        {error || problem ? (
          <ErrorState
            title="The analysis is not available"
            message={problem ?? message(error)}
            reference={error instanceof ApiError ? error.requestId : undefined}
            onRetry={() => void load()}
          />
        ) : null}
      </PageFrame>
    );
  }

  const analysis = mapAnalysis(result.run);
  return (
    <AnalysisView
      key={result.run.instrument.symbol}
      a={analysis}
      mode={result.meta.dataMode}
      onCreatePlan={async (levels) => {
        const plan = await createTradePlan(analysis.stock.symbol, analysis.setup.type, levels);
        return { quantity: plan.quantity };
      }}
    />
  );
}

function message(e: ApiError | Error | null): string {
  if (!(e instanceof ApiError)) return "The analysis could not be loaded.";
  switch (e.code) {
    case "NOT_FOUND":
      return "This symbol is not in the instrument list.";
    case "NO_BARS_FOR_SYMBOL":
      return "No stored bars for this symbol yet.";
    case "ENGINE_UNAVAILABLE":
      return "The analysis engine is not reachable. Your data is unchanged.";
    case "RATE_LIMITED":
      return "Too many requests. Wait a moment and try again.";
    default:
      return "This view could not be loaded. Your data is unchanged.";
  }
}
