"use client";

import { useMemo, useState } from "react";
import { BookOpenText, CheckCircle2, ImagePlus, Plus, Search, TriangleAlert } from "lucide-react";
import { formatDate, formatInt, formatPct, formatPrice, formatR, formatSignedInr } from "@/lib/format";
import { OUTCOMES, SETUP_TYPES } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { JournalEntry, SetupType, TradeOutcome } from "@/types";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { Badge } from "@/components/data/badge";
import { DataTable, type Column } from "@/components/data/data-table";
import { EmptyState } from "@/components/data/empty-state";
import { MetricCard } from "@/components/data/metric-card";
import { SampleDataBadge } from "@/components/data/sample-data-badge";
import { StatusBadge } from "@/components/data/status-badge";
import { journalStats } from "./stats";

export function JournalView({ initial, asOf }: { initial: JournalEntry[]; asOf: string }) {
  const toast = useToast();
  const [entries, setEntries] = useState(initial);
  const [query, setQuery] = useState("");
  const [outcome, setOutcome] = useState<"all" | TradeOutcome>("all");
  const [setup, setSetup] = useState<"all" | SetupType>("all");
  const [adherence, setAdherence] = useState<"all" | "followed" | "broken">("all");
  const [selected, setSelected] = useState<JournalEntry | null>(null);
  const [noteDraft, setNoteDraft] = useState("");

  const filtered = useMemo(
    () =>
      entries.filter(
        (e) =>
          (!query || e.symbol.toLowerCase().includes(query.toLowerCase()) || e.notes.toLowerCase().includes(query.toLowerCase())) &&
          (outcome === "all" || e.outcome === outcome) &&
          (setup === "all" || e.setupType === setup) &&
          (adherence === "all" || (adherence === "followed" ? e.followedPlan : !e.followedPlan)),
      ),
    [entries, query, outcome, setup, adherence],
  );
  const s = journalStats(filtered);

  const columns: Column<JournalEntry>[] = [
    {
      key: "symbol",
      header: "Trade",
      sticky: true,
      sortValue: (e) => e.symbol,
      render: (e) => (
        <span className="flex flex-col leading-tight">
          <span className="text-[13px] font-semibold text-fg">{e.symbol}</span>
          <span className="text-2xs text-fg-subtle">{e.direction === "long" ? "Long" : "Short"} · {formatInt(e.quantity)} sh</span>
        </span>
      ),
    },
    { key: "setup", header: "Setup", hideBelow: "md", sortValue: (e) => e.setupType, render: (e) => <span className="text-fg-muted">{SETUP_TYPES[e.setupType].label}</span> },
    { key: "dates", header: "Held", hideBelow: "lg", sortValue: (e) => e.exitDate, render: (e) => <span className="text-fg-muted">{formatDate(e.entryDate)} → {formatDate(e.exitDate)}</span> },
    { key: "entry", header: "Entry", align: "right", hideBelow: "sm", render: (e) => formatPrice(e.entryPrice) },
    { key: "exit", header: "Exit", align: "right", hideBelow: "sm", render: (e) => formatPrice(e.exitPrice) },
    { key: "pnl", header: "P&L", align: "right", sortValue: (e) => e.pnl, render: (e) => <span className={e.pnl >= 0 ? "text-bull" : "text-bear"}>{formatSignedInr(e.pnl, { decimals: false })}</span> },
    { key: "r", header: "R", align: "right", sortValue: (e) => e.rMultiple, render: (e) => <span className={e.rMultiple >= 0 ? "text-bull" : "text-bear"}>{formatR(e.rMultiple)}</span> },
    { key: "outcome", header: "Outcome", sortValue: (e) => e.outcome, render: (e) => <StatusBadge kind="outcome" status={e.outcome} /> },
    {
      key: "plan",
      header: "Plan",
      hideBelow: "md",
      render: (e) =>
        e.followedPlan ? (
          <span className="inline-flex items-center gap-1 text-2xs text-bull"><CheckCircle2 className="size-3.5" /> Followed</span>
        ) : (
          <span className="inline-flex items-center gap-1 text-2xs text-warn"><TriangleAlert className="size-3.5" /> Deviated</span>
        ),
    },
    { key: "notes", header: "Notes", hideBelow: "xl", render: (e) => <span className="block max-w-64 truncate text-fg-muted">{e.notes}</span> },
  ];

  return (
    <PageContainer>
      <PageHeader
        title="Trading Journal"
        description="Review closed trades, classify setups and learn from your execution."
        meta={<SampleDataBadge asOf={asOf} />}
        actions={
          <Button size="sm" variant="primary" onClick={() => toast({ title: "Manual entry form coming next phase", description: "Entries will be created automatically from linked orders.", tone: "info" })}>
            <Plus /> Add entry
          </Button>
        }
      />

      <section aria-label="Performance summary" className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <MetricCard label="Trades" value={s.trades} hint="Matching current filters" />
        <MetricCard label="Win rate" value={formatPct(s.winRate, { signed: false, decimals: 0 })} tone={s.winRate >= 50 ? "bull" : "warn"} />
        <MetricCard label="Profit factor" value={Number.isFinite(s.profitFactor) ? s.profitFactor.toFixed(2) : "—"} />
        <MetricCard label="Average R" value={formatR(s.avgR)} tone={s.avgR >= 0 ? "bull" : "bear"} />
        <MetricCard label="Net P&L" value={formatSignedInr(s.net, { decimals: false })} tone={s.net >= 0 ? "bull" : "bear"} />
        <MetricCard
          label="Plan adherence"
          value={formatPct(s.planAdherence, { signed: false, decimals: 0 })}
          tone="accent"
          hint={`Deviations: ${formatSignedInr(s.brokenNet, { decimals: false })}`}
        />
      </section>

      <Panel className="overflow-hidden">
        <div className="grid grid-cols-2 gap-3 border-b border-border p-3 md:grid-cols-4">
          <Input aria-label="Search trades" placeholder="Search symbol or notes…" leading={<Search />} value={query} onChange={(e) => setQuery(e.target.value)} className="col-span-2 md:col-span-1" />
          <Select
            aria-label="Outcome"
            value={outcome}
            onChange={(e) => setOutcome(e.target.value as typeof outcome)}
            options={[{ value: "all", label: "All outcomes" }, ...(Object.keys(OUTCOMES) as TradeOutcome[]).map((k) => ({ value: k, label: OUTCOMES[k].label }))]}
          />
          <Select
            aria-label="Setup type"
            value={setup}
            onChange={(e) => setSetup(e.target.value as typeof setup)}
            options={[{ value: "all", label: "All setups" }, ...(Object.keys(SETUP_TYPES) as SetupType[]).map((k) => ({ value: k, label: SETUP_TYPES[k].label }))]}
          />
          <Select
            aria-label="Plan adherence"
            value={adherence}
            onChange={(e) => setAdherence(e.target.value as typeof adherence)}
            options={[
              { value: "all", label: "Any adherence" },
              { value: "followed", label: "Followed plan" },
              { value: "broken", label: "Deviated from plan" },
            ]}
          />
        </div>
        <DataTable
          columns={columns}
          rows={filtered}
          rowKey={(e) => e.id}
          initialSort={{ key: "dates", dir: "desc" }}
          onRowClick={(e) => {
            setSelected(e);
            setNoteDraft(e.notes);
          }}
          caption="Trade history"
          empty={<EmptyState icon={BookOpenText} title="No trades match these filters" />}
        />
      </Panel>

      <Dialog
        open={!!selected}
        onClose={() => setSelected(null)}
        size="lg"
        title={selected ? `${selected.symbol} · ${SETUP_TYPES[selected.setupType].label}` : ""}
        description={selected ? `${formatDate(selected.entryDate)} → ${formatDate(selected.exitDate)} · ${selected.id}` : undefined}
        footer={
          <>
            <Button size="sm" variant="ghost" onClick={() => setSelected(null)}>Close</Button>
            <Button
              size="sm"
              variant="primary"
              onClick={() => {
                if (!selected) return;
                setEntries((es) => es.map((e) => (e.id === selected.id ? { ...e, notes: noteDraft } : e)));
                toast({ title: "Notes saved", description: "Demo mode: kept for this session." });
                setSelected(null);
              }}
            >
              Save notes
            </Button>
          </>
        }
      >
        {selected && (
          <div className="flex flex-col gap-4">
            <dl className="tnum grid grid-cols-2 gap-3 text-2xs sm:grid-cols-4">
              {[
                ["Entry", formatPrice(selected.entryPrice)],
                ["Exit", formatPrice(selected.exitPrice)],
                ["P&L", formatSignedInr(selected.pnl, { decimals: false })],
                ["R multiple", formatR(selected.rMultiple)],
              ].map(([k, v]) => (
                <div key={k} className="rounded border border-border bg-subtle px-3 py-2">
                  <dt className="text-fg-subtle">{k}</dt>
                  <dd className={cn("text-sm font-semibold", k === "P&L" || k === "R multiple" ? (selected.pnl >= 0 ? "text-bull" : "text-bear") : "text-fg")}>{v}</dd>
                </div>
              ))}
            </dl>
            <div className="flex flex-wrap gap-1.5">
              <StatusBadge kind="outcome" status={selected.outcome} />
              <Badge tone={selected.followedPlan ? "bull" : "warn"} variant="outline">{selected.followedPlan ? "Followed plan" : "Deviated from plan"}</Badge>
              {selected.tags.map((t) => (
                <Badge key={t} tone="neutral">{t}</Badge>
              ))}
            </div>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-fg-muted">Notes</span>
              <textarea
                value={noteDraft}
                onChange={(e) => setNoteDraft(e.target.value)}
                rows={4}
                className="rounded border border-border bg-subtle px-3 py-2 text-[13px] text-fg focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
              />
            </label>
            <div>
              <p className="mb-1.5 text-xs font-medium text-fg-muted">Chart screenshots</p>
              <div className="grid grid-cols-2 gap-3">
                {["Entry chart", "Exit chart"].map((l) => (
                  <button
                    key={l}
                    type="button"
                    onClick={() => toast({ title: "Uploads not available yet", description: "Screenshot storage arrives with the backend.", tone: "info" })}
                    className="flex aspect-video flex-col items-center justify-center gap-1.5 rounded border border-dashed border-border-strong bg-subtle text-fg-subtle transition-colors hover:border-accent hover:text-fg-muted"
                  >
                    <ImagePlus className="size-5" aria-hidden />
                    <span className="text-2xs">{l} · placeholder</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
}
