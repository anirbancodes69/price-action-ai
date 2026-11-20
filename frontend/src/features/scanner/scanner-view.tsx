"use client";

import { useMemo, useState } from "react";
import { Download, Radar, RotateCcw } from "lucide-react";
import { SETUP_STATUS, SETUP_TYPES, STRUCTURES } from "@/lib/labels";
import { TONE_FILL } from "@/lib/colors";
import { cn } from "@/lib/utils";
import type { Bias, ScannerRow } from "@/types";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { Button } from "@/components/ui/button";
import { ChoiceGroup } from "@/components/ui/choice-group";
import { ClearButton, FilterRow, SearchField } from "@/components/ui/filter-row";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { Disclaimer } from "@/components/data/disclaimer";
import { Empty } from "@/components/data/empty";
import { LiveDataBadge } from "@/components/data/live-data-badge";
import { SampleDataBadge } from "@/components/data/sample-data-badge";
import { StockTable } from "@/components/trading/stock-table";
import { DEFAULT_FILTERS, activeFilterCount, applyFilters, type ScannerFilters } from "./filters";

const opts = <T extends string>(rec: Record<T, { label: string }>, allLabel: string) => [
  { value: "all", label: allLabel },
  ...(Object.keys(rec) as T[]).map((k) => ({ value: k, label: rec[k].label })),
];

const dot = (cls: string) => <span className={cn("size-1.5 rounded-full", cls)} aria-hidden />;

export interface ScannerLive {
  /** Data mode of the source (ADR-011). DEMO is shown as sample data, never as live. */
  mode: "DEMO" | "PERSONAL" | "LICENSED";
  refreshing: boolean;
  onRefresh: () => void;
  /** When the data can next change (end of the next 5m bar). */
  nextBarClose: string | null;
}

export function ScannerView({ rows, asOf, live }: { rows: ScannerRow[]; asOf: string; live?: ScannerLive }) {
  const toast = useToast();
  const [f, setF] = useState<ScannerFilters>(DEFAULT_FILTERS);
  const filtered = useMemo(() => applyFilters(rows, f), [rows, f]);
  const set = <K extends keyof ScannerFilters>(k: K, v: ScannerFilters[K]) => setF((s) => ({ ...s, [k]: v }));
  const canClear = activeFilterCount(f) > 0 || f.query !== "";

  const biasCounts = useMemo(() => {
    const base = applyFilters(rows, { ...f, bias: "all" });
    return {
      all: base.length,
      bullish: base.filter((r) => r.bias === "bullish").length,
      bearish: base.filter((r) => r.bias === "bearish").length,
      neutral: base.filter((r) => r.bias === "neutral").length,
    };
  }, [rows, f]);

  return (
    <PageFrame>
      <PageHeader
        title="Market Scanner"
        description="Scan the universe for price-action structure and setups (15m structure, 5m setups). Select a row to open its analysis."
        meta={live && live.mode !== "DEMO" ? <LiveDataBadge mode={live.mode} asOf={asOf} /> : <SampleDataBadge asOf={asOf} />}
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => toast({ title: "Export is not available yet", description: "CSV export will be enabled with the data API.", tone: "info" })}
            >
              <Download /> Export
            </Button>
            <Button
              variant="primary"
              disabled={live?.refreshing}
              onClick={() => (live ? live.onRefresh() : toast({ title: "Scan refreshed", description: `Sample data · ${rows.length} stocks evaluated.` }))}
            >
              <RotateCcw className={live?.refreshing ? "animate-spin" : undefined} /> {live?.refreshing ? "Scanning…" : "Re-run scan"}
            </Button>
          </>
        }
      />

      <FilterRow
        label="Scanner filters"
        end={<SearchField label="Search symbol or company" placeholder="Search symbol or company…" value={f.query} onChange={(v) => set("query", v)} />}
      >
        <ChoiceGroup<"all" | Bias>
          ariaLabel="Directional bias"
          value={f.bias}
          onChange={(v) => set("bias", v)}
          options={[
            { value: "all", label: "All", count: biasCounts.all },
            { value: "bullish", label: "Bullish", count: biasCounts.bullish, icon: dot(TONE_FILL.bull) },
            { value: "bearish", label: "Bearish", count: biasCounts.bearish, icon: dot(TONE_FILL.bear) },
            { value: "neutral", label: "Neutral", count: biasCounts.neutral, icon: dot(TONE_FILL.neutral) },
          ]}
        />
        <Select
          aria-label="Setup type"
          width="auto"
          value={f.setup}
          onChange={(e) => set("setup", e.target.value as ScannerFilters["setup"])}
          options={opts(SETUP_TYPES, "All setups")}
        />
        <Select
          aria-label="Market structure"
          width="auto"
          value={f.structure}
          onChange={(e) => set("structure", e.target.value as ScannerFilters["structure"])}
          options={opts(STRUCTURES, "All structures")}
        />
        <Select
          aria-label="Setup status"
          width="auto"
          value={f.status}
          onChange={(e) => set("status", e.target.value as ScannerFilters["status"])}
          options={opts(SETUP_STATUS, "All statuses")}
        />
        <Select
          aria-label="Minimum risk to reward"
          width="auto"
          value={String(f.minRR)}
          onChange={(e) => set("minRR", Number(e.target.value))}
          options={[
            { value: "0", label: "Any R:R" },
            { value: "1.5", label: "R:R ≥ 1.5" },
            { value: "2", label: "R:R ≥ 2" },
            { value: "3", label: "R:R ≥ 3" },
          ]}
        />
        <Select
          aria-label="Index"
          width="auto"
          value={f.index}
          onChange={(e) => set("index", e.target.value as ScannerFilters["index"])}
          options={[
            { value: "all", label: "All indices" },
            { value: "NIFTY 50", label: "NIFTY 50" },
            { value: "NIFTY NEXT 50", label: "NIFTY NEXT 50" },
            { value: "NIFTY MIDCAP 100", label: "NIFTY MIDCAP 100" },
          ]}
        />
        <ClearButton show={canClear} onClear={() => setF(DEFAULT_FILTERS)} />
      </FilterRow>

      <StockTable
        rows={filtered}
        initialSort={{ key: "quality", dir: "desc" }}
        caption={`Market scanner results: ${filtered.length} of ${rows.length} stocks`}
        empty={
          <Empty
            kind="scope"
            icon={Radar}
            title="No stocks match these filters"
            description="Loosen a filter or clear them to see the full sample universe."
            action={
              <Button variant="outline" size="sm" onClick={() => setF(DEFAULT_FILTERS)}>
                Clear filters
              </Button>
            }
          />
        }
      />
      <Disclaimer />
    </PageFrame>
  );
}
