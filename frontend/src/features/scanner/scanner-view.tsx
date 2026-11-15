"use client";

import { useMemo, useState } from "react";
import { Download, FilterX, Radar, RotateCcw, Search, SlidersHorizontal } from "lucide-react";
import { BIAS, SETUP_STATUS, SETUP_TYPES, STRUCTURES } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { Bias, ScannerRow } from "@/types";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { Disclaimer } from "@/components/data/disclaimer";
import { EmptyState } from "@/components/data/empty-state";
import { SampleDataBadge } from "@/components/data/sample-data-badge";
import { StockTable } from "@/components/trading/stock-table";
import { DEFAULT_FILTERS, activeFilterCount, applyFilters, type ScannerFilters } from "./filters";

const opts = <T extends string>(rec: Record<T, { label: string }>, allLabel: string) => [
  { value: "all", label: allLabel },
  ...(Object.keys(rec) as T[]).map((k) => ({ value: k, label: rec[k].label })),
];

const BIAS_CHIPS: { value: "all" | Bias; label: string; dot?: string }[] = [
  { value: "all", label: "All" },
  { value: "bullish", label: "Bullish", dot: "bg-bull" },
  { value: "bearish", label: "Bearish", dot: "bg-bear" },
  { value: "neutral", label: "Neutral", dot: "bg-neutral" },
];

export function ScannerView({ rows, asOf }: { rows: ScannerRow[]; asOf: string }) {
  const toast = useToast();
  const [f, setF] = useState<ScannerFilters>(DEFAULT_FILTERS);
  const [showFilters, setShowFilters] = useState(true);
  const filtered = useMemo(() => applyFilters(rows, f), [rows, f]);
  const set = <K extends keyof ScannerFilters>(k: K, v: ScannerFilters[K]) => setF((s) => ({ ...s, [k]: v }));
  const nActive = activeFilterCount(f);

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
    <PageContainer>
      <PageHeader
        title="Market Scanner"
        description="Scan the universe for price-action structure and setups on the daily timeframe."
        meta={<SampleDataBadge asOf={asOf} />}
        actions={
          <>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => toast({ title: "Export is not available yet", description: "CSV export will be enabled with the data API.", tone: "info" })}
            >
              <Download /> Export
            </Button>
            <Button
              size="sm"
              variant="primary"
              onClick={() => toast({ title: "Scan refreshed", description: `Sample data · ${rows.length} stocks evaluated.` })}
            >
              <RotateCcw /> Re-run scan
            </Button>
          </>
        }
      />

      <Panel className="overflow-hidden">
        {/* Toolbar */}
        <div className="flex flex-col gap-3 border-b border-border p-3 md:flex-row md:items-center">
          <Input
            aria-label="Search symbol or company"
            placeholder="Search symbol or company…"
            leading={<Search />}
            value={f.query}
            onChange={(e) => set("query", e.target.value)}
            className="md:w-72"
          />
          <div role="radiogroup" aria-label="Directional bias" className="no-scrollbar flex items-center gap-1 overflow-x-auto">
            {BIAS_CHIPS.map((c) => (
              <button
                key={c.value}
                type="button"
                role="radio"
                aria-checked={f.bias === c.value}
                onClick={() => set("bias", c.value)}
                className={cn(
                  "inline-flex h-7 shrink-0 items-center gap-1.5 rounded border px-2.5 text-xs font-medium transition-colors",
                  f.bias === c.value ? "border-accent/50 bg-accent/12 text-fg" : "border-border text-fg-muted hover:border-border-strong hover:text-fg",
                )}
              >
                {c.dot && <span className={cn("size-1.5 rounded-full", c.dot)} aria-hidden />}
                {c.label}
                <span className="tnum text-fg-subtle">{biasCounts[c.value]}</span>
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 md:ml-auto">
            <Button size="sm" variant={showFilters ? "secondary" : "ghost"} onClick={() => setShowFilters((s) => !s)} aria-expanded={showFilters}>
              <SlidersHorizontal /> Filters
              {nActive > 0 && <span className="tnum rounded-sm bg-accent px-1 text-2xs text-accent-fg">{nActive}</span>}
            </Button>
            {nActive > 0 && (
              <Button size="sm" variant="ghost" onClick={() => setF({ ...DEFAULT_FILTERS, query: f.query })}>
                <FilterX /> Clear
              </Button>
            )}
          </div>
        </div>

        {showFilters && (
          <div className="grid grid-cols-2 gap-3 border-b border-border bg-subtle/40 p-3 sm:grid-cols-3 lg:grid-cols-6">
            <Select
              label="Exchange"
              selectSize="sm"
              value={f.exchange}
              onChange={(e) => set("exchange", e.target.value as ScannerFilters["exchange"])}
              options={[{ value: "all", label: "All exchanges" }, { value: "NSE", label: "NSE" }, { value: "BSE", label: "BSE" }]}
            />
            <Select
              label="Index"
              selectSize="sm"
              value={f.index}
              onChange={(e) => set("index", e.target.value as ScannerFilters["index"])}
              options={[
                { value: "all", label: "All indices" },
                { value: "NIFTY 50", label: "NIFTY 50" },
                { value: "NIFTY NEXT 50", label: "NIFTY NEXT 50" },
                { value: "NIFTY MIDCAP 100", label: "NIFTY MIDCAP 100" },
              ]}
            />
            <Select label="Setup type" selectSize="sm" value={f.setup} onChange={(e) => set("setup", e.target.value as ScannerFilters["setup"])} options={opts(SETUP_TYPES, "All setups")} />
            <Select
              label="Market structure"
              selectSize="sm"
              value={f.structure}
              onChange={(e) => set("structure", e.target.value as ScannerFilters["structure"])}
              options={opts(STRUCTURES, "All structures")}
            />
            <Select label="Setup status" selectSize="sm" value={f.status} onChange={(e) => set("status", e.target.value as ScannerFilters["status"])} options={opts(SETUP_STATUS, "All statuses")} />
            <Select
              label="Min. risk/reward"
              selectSize="sm"
              value={String(f.minRR)}
              onChange={(e) => set("minRR", Number(e.target.value))}
              options={[
                { value: "0", label: "Any" },
                { value: "1.5", label: "≥ 1 : 1.5" },
                { value: "2", label: "≥ 1 : 2" },
                { value: "3", label: "≥ 1 : 3" },
              ]}
            />
          </div>
        )}

        <div className="flex items-center justify-between px-4 py-2 text-2xs text-fg-subtle">
          <span className="tnum">
            Showing <span className="text-fg-muted">{filtered.length}</span> of {rows.length} stocks · {f.bias !== "all" ? BIAS[f.bias].label : "All biases"}
          </span>
          <span className="hidden sm:inline">Click a row to open the analysis</span>
        </div>

        <StockTable
          rows={filtered}
          initialSort={{ key: "quality", dir: "desc" }}
          caption="Market scanner results"
          empty={
            <EmptyState
              icon={Radar}
              title="No stocks match these filters"
              description="Loosen a filter or clear them to see the full sample universe."
              action={
                <Button size="sm" variant="secondary" onClick={() => setF(DEFAULT_FILTERS)}>
                  Clear filters
                </Button>
              }
            />
          }
        />
      </Panel>
      <Disclaimer />
    </PageContainer>
  );
}
