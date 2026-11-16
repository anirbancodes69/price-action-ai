"use client";

import { useMemo, useState } from "react";
import { BookOpenText, CheckCircle2, ImagePlus, Plus, TriangleAlert } from "lucide-react";
import { signTone, TONE_TEXT, type MarketTone } from "@/lib/colors";
import { formatDate, formatInt, formatPct, formatPrice, formatR, formatSignedInr } from "@/lib/format";
import { OUTCOMES, SETUP_TYPES } from "@/lib/labels";
import type { JournalEntry, SetupType, TradeOutcome } from "@/types";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { ClearButton, FilterRow, SearchField } from "@/components/ui/filter-row";
import { Textarea } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { Badge } from "@/components/data/badge";
import { DataTable, type Column } from "@/components/data/data-table";
import { Empty } from "@/components/data/empty";
import { Stat, StatGrid } from "@/components/data/stat";
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
  const signed = (n: number): MarketTone | undefined => {
    const t = signTone(n);
    return t === "neutral" ? undefined : t;
  };
  const clearFilters = () => {
    setQuery("");
    setOutcome("all");
    setSetup("all");
    setAdherence("all");
  };

  const columns: Column<JournalEntry>[] = [
    {
      key: "symbol",
      header: "Trade",
      sticky: true,
      sortValue: (e) => e.symbol,
      render: (e) => (
        <span className="flex flex-col leading-tight">
          <span className="text-sm font-medium text-foreground">{e.symbol}</span>
          <span className="truncate text-xs text-muted-foreground">{e.direction === "long" ? "Long" : "Short"} · {formatInt(e.quantity)} sh</span>
        </span>
      ),
    },
    { key: "setup", header: "Setup", hideBelow: "xl", sortValue: (e) => e.setupType, render: (e) => <span className="text-muted-foreground">{SETUP_TYPES[e.setupType].label}</span> },
    { key: "dates", header: "Held", hideBelow: "2xl", sortValue: (e) => e.exitDate, render: (e) => <span className="text-muted-foreground">{formatDate(e.entryDate)} → {formatDate(e.exitDate)}</span> },
    { key: "entry", header: "Entry", align: "right", hideBelow: "lg", render: (e) => formatPrice(e.entryPrice) },
    { key: "exit", header: "Exit", align: "right", hideBelow: "lg", render: (e) => formatPrice(e.exitPrice) },
    { key: "pnl", header: "P&L", align: "right", sortValue: (e) => e.pnl, render: (e) => <span className={e.pnl >= 0 ? "text-bull" : "text-bear"}>{formatSignedInr(e.pnl, { decimals: false })}</span> },
    { key: "r", header: "R", align: "right", sortValue: (e) => e.rMultiple, render: (e) => <span className={e.rMultiple >= 0 ? "text-bull" : "text-bear"}>{formatR(e.rMultiple)}</span> },
    { key: "outcome", header: "Outcome", sortValue: (e) => e.outcome, render: (e) => <StatusBadge kind="outcome" status={e.outcome} /> },
    {
      key: "plan",
      header: "Plan",
      hideBelow: "md",
      render: (e) =>
        e.followedPlan ? (
          <span className="inline-flex items-center gap-1 text-xs text-success"><CheckCircle2 className="size-3.5" aria-hidden /> Followed</span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs text-warning"><TriangleAlert className="size-3.5" aria-hidden /> Deviated</span>
        ),
    },
    { key: "notes", header: "Notes", hideBelow: "xl", grow: true, render: (e) => <span className="block truncate text-muted-foreground" title={e.notes}>{e.notes}</span> },
  ];

  return (
    <PageFrame>
      <PageHeader
        title="Trading Journal"
        description="Review closed trades, classify setups and learn from your execution."
        meta={<SampleDataBadge asOf={asOf} />}
        actions={
          <Button variant="primary" onClick={() => toast({ title: "Manual entry form coming next phase", description: "Entries will be created automatically from linked orders.", tone: "info" })}>
            <Plus /> Add entry
          </Button>
        }
      />

      <StatGrid label="Performance summary">
        <Stat label="Trades" value={s.trades} hint={`${formatPct(s.planAdherence, { signed: false, decimals: 0 })} followed the plan`} />
        <Stat
          label="Win rate"
          value={formatPct(s.winRate, { signed: false, decimals: 0 })}
          hint={`Profit factor ${Number.isFinite(s.profitFactor) ? s.profitFactor.toFixed(2) : "—"}`}
        />
        <Stat label="Average R" value={formatR(s.avgR)} tone={signed(s.avgR)} hint="Per closed trade" />
        <Stat
          label="Net P&L"
          value={formatSignedInr(s.net, { decimals: false })}
          tone={signed(s.net)}
          hint={`Deviations: ${formatSignedInr(s.brokenNet, { decimals: false })}`}
        />
      </StatGrid>

      <FilterRow label="Journal filters" end={<SearchField label="Search trades" placeholder="Search symbol or notes…" value={query} onChange={setQuery} />}>
        <Select
          aria-label="Outcome"
          width="auto"
          value={outcome}
          onChange={(e) => setOutcome(e.target.value as typeof outcome)}
          options={[{ value: "all", label: "All outcomes" }, ...(Object.keys(OUTCOMES) as TradeOutcome[]).map((k) => ({ value: k, label: OUTCOMES[k].label }))]}
        />
        <Select
          aria-label="Setup type"
          width="auto"
          value={setup}
          onChange={(e) => setSetup(e.target.value as typeof setup)}
          options={[{ value: "all", label: "All setups" }, ...(Object.keys(SETUP_TYPES) as SetupType[]).map((k) => ({ value: k, label: SETUP_TYPES[k].label }))]}
        />
        <Select
          aria-label="Plan adherence"
          width="auto"
          value={adherence}
          onChange={(e) => setAdherence(e.target.value as typeof adherence)}
          options={[
            { value: "all", label: "Any adherence" },
            { value: "followed", label: "Followed plan" },
            { value: "broken", label: "Deviated from plan" },
          ]}
        />
        <ClearButton show={!!query || outcome !== "all" || setup !== "all" || adherence !== "all"} onClear={clearFilters} />
      </FilterRow>

      <DataTable
        columns={columns}
        rows={filtered}
        rowKey={(e) => e.id}
        initialSort={{ key: "dates", dir: "desc" }}
        onRowClick={(e) => {
          setSelected(e);
          setNoteDraft(e.notes);
        }}
        caption="Trade history. Select a row to review the trade and edit notes."
        empty={
          entries.length === 0 ? (
            <Empty icon={BookOpenText} title="No closed trades yet" description="Entries are created when a position linked to a plan is closed." />
          ) : (
            <Empty
              kind="scope"
              icon={BookOpenText}
              title="No trades match these filters"
              description="Widen the outcome, setup or adherence filter."
              action={
                <Button variant="outline" size="sm" onClick={clearFilters}>
                  Clear filters
                </Button>
              }
            />
          )
        }
      />

      <Dialog
        open={!!selected}
        onClose={() => setSelected(null)}
        size="lg"
        title={selected ? `${selected.symbol} · ${SETUP_TYPES[selected.setupType].label}` : ""}
        description={selected ? `${formatDate(selected.entryDate)} → ${formatDate(selected.exitDate)} · ${selected.id}` : undefined}
        footer={
          <>
            <Button variant="outline" onClick={() => setSelected(null)}>Close</Button>
            <Button
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
            <dl className="grid grid-cols-2 gap-3 tabular-nums sm:grid-cols-4">
              {[
                ["Entry", formatPrice(selected.entryPrice)],
                ["Exit", formatPrice(selected.exitPrice)],
                ["P&L", formatSignedInr(selected.pnl, { decimals: false })],
                ["R multiple", formatR(selected.rMultiple)],
              ].map(([k, v]) => (
                <div key={k} className="flex flex-col gap-1 rounded-lg bg-muted px-3 py-2">
                  <dt className="text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">{k}</dt>
                  <dd className={`text-sm font-medium ${k === "P&L" || k === "R multiple" ? TONE_TEXT[signTone(selected.pnl)] : "text-foreground"}`}>{v}</dd>
                </div>
              ))}
            </dl>
            <div className="flex flex-wrap gap-1.5">
              <StatusBadge kind="outcome" status={selected.outcome} />
              <Badge tone={selected.followedPlan ? "success" : "warning"} variant="outline">{selected.followedPlan ? "Followed plan" : "Deviated from plan"}</Badge>
              {selected.tags.map((t) => (
                <Badge key={t} tone="neutral">{t}</Badge>
              ))}
            </div>
            <Textarea label="Notes" value={noteDraft} onChange={(e) => setNoteDraft(e.target.value)} rows={4} />
            <div className="flex flex-col gap-1">
              <p className="text-xs font-medium text-muted-foreground">Chart screenshots</p>
              <div className="grid grid-cols-2 gap-3">
                {["Entry chart", "Exit chart"].map((l) => (
                  <button
                    key={l}
                    type="button"
                    onClick={() => toast({ title: "Uploads not available yet", description: "Screenshot storage arrives with the backend.", tone: "info" })}
                    className="flex aspect-video flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-input text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                  >
                    <ImagePlus className="size-5" aria-hidden />
                    <span className="text-xs">{l} · placeholder</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </Dialog>
    </PageFrame>
  );
}
