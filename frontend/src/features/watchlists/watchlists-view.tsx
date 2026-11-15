"use client";

import { useMemo, useState } from "react";
import { ListPlus, MoreHorizontal, Pencil, Plus, Star, Trash2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ScannerRow } from "@/types";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Dropdown } from "@/components/ui/dropdown";
import { Input } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import { useToast } from "@/components/ui/toast";
import { Tooltip } from "@/components/ui/tooltip";
import { EmptyState } from "@/components/data/empty-state";
import { SampleDataBadge } from "@/components/data/sample-data-badge";
import { StockTable } from "@/components/trading/stock-table";
import { useWatchlists } from "./watchlist-store";

type DialogState = { kind: "create" } | { kind: "rename"; id: string } | { kind: "add" } | null;

export function WatchlistsView({ rows, asOf }: { rows: ScannerRow[]; asOf: string }) {
  const { watchlists, add, remove, create, rename, removeList } = useWatchlists();
  const toast = useToast();
  const [activeId, setActiveId] = useState(watchlists[0]?.id ?? "");
  const [dialog, setDialog] = useState<DialogState>(null);
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string>();
  const [addQuery, setAddQuery] = useState("");

  const active = watchlists.find((w) => w.id === activeId) ?? watchlists[0];
  const bySymbol = useMemo(() => new Map(rows.map((r) => [r.stock.symbol, r])), [rows]);
  const activeRows = active ? active.symbols.map((s) => bySymbol.get(s)).filter((r): r is ScannerRow => !!r) : [];

  const addCandidates = useMemo(() => {
    const q = addQuery.trim().toLowerCase();
    return rows
      .filter((r) => !active?.symbols.includes(r.stock.symbol))
      .filter((r) => !q || r.stock.symbol.toLowerCase().includes(q) || r.stock.name.toLowerCase().includes(q))
      .slice(0, 12);
  }, [rows, active, addQuery]);

  const openNameDialog = (d: DialogState, initial = "") => {
    setName(initial);
    setNameError(undefined);
    setDialog(d);
  };

  const submitName = () => {
    const n = name.trim();
    if (n.length < 2) return setNameError("Name must be at least 2 characters");
    if (watchlists.some((w) => w.name.toLowerCase() === n.toLowerCase() && (dialog?.kind !== "rename" || w.id !== dialog.id))) {
      return setNameError("A watchlist with this name already exists");
    }
    if (dialog?.kind === "create") {
      const wl = create(n);
      setActiveId(wl.id);
      toast({ title: `Created “${n}”` });
    } else if (dialog?.kind === "rename") {
      rename(dialog.id, n);
      toast({ title: `Renamed to “${n}”` });
    }
    setDialog(null);
  };

  return (
    <PageContainer>
      <PageHeader
        title="Watchlists"
        description="Track the stocks you follow and see their structure and setup status at a glance."
        meta={<SampleDataBadge asOf={asOf} />}
        actions={
          <Button size="sm" variant="secondary" onClick={() => openNameDialog({ kind: "create" })}>
            <Plus /> New watchlist
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[240px_minmax(0,1fr)] lg:gap-5">
        {/* List selector */}
        <Panel className="h-fit">
          <ul className="no-scrollbar flex gap-1 overflow-x-auto p-1.5 lg:flex-col lg:overflow-visible" aria-label="Watchlists">
            {watchlists.map((w) => (
              <li key={w.id} className="shrink-0">
                <button
                  type="button"
                  onClick={() => setActiveId(w.id)}
                  aria-current={w.id === active?.id}
                  className={cn(
                    "flex h-8 w-full items-center gap-2 rounded px-2.5 text-left text-[13px] transition-colors",
                    w.id === active?.id ? "bg-accent/12 text-fg" : "text-fg-muted hover:bg-hover hover:text-fg",
                  )}
                >
                  <Star className={cn("size-3.5 shrink-0", w.id === active?.id ? "fill-warn text-warn" : "text-fg-subtle")} aria-hidden />
                  <span className="flex-1 truncate">{w.name}</span>
                  <span className="tnum text-2xs text-fg-subtle">{w.symbols.length}</span>
                </button>
              </li>
            ))}
          </ul>
        </Panel>

        {/* Active list */}
        {active ? (
          <Panel className="min-w-0 overflow-hidden">
            <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-2.5">
              <div className="min-w-0">
                <h2 className="truncate text-[13px] font-semibold text-fg">{active.name}</h2>
                <p className="text-2xs text-fg-subtle">{active.symbols.length} stocks · click a row to open the analysis</p>
              </div>
              <div className="flex items-center gap-1.5">
                <Button size="sm" variant="primary" onClick={() => { setAddQuery(""); setDialog({ kind: "add" }); }}>
                  <ListPlus /> Add stocks
                </Button>
                <Dropdown
                  width="w-44"
                  trigger={({ open, toggle, id }) => (
                    <Button size="icon-sm" variant="ghost" onClick={toggle} aria-label="Watchlist options" aria-expanded={open} aria-haspopup="menu" aria-controls={open ? id : undefined}>
                      <MoreHorizontal />
                    </Button>
                  )}
                  items={[
                    { label: "Rename", icon: Pencil, onSelect: () => openNameDialog({ kind: "rename", id: active.id }, active.name) },
                    {
                      label: "Delete watchlist",
                      icon: Trash2,
                      tone: "danger",
                      disabled: watchlists.length <= 1,
                      onSelect: () => {
                        removeList(active.id);
                        setActiveId(watchlists.find((w) => w.id !== active.id)?.id ?? "");
                        toast({ title: `Deleted “${active.name}”`, tone: "info" });
                      },
                    },
                  ]}
                />
              </div>
            </header>
            <StockTable
              rows={activeRows}
              columns={["symbol", "company", "price", "change", "structure", "setup", "status", "signal"]}
              caption={`Watchlist ${active.name}`}
              actions={(r) => (
                <Tooltip content="Remove from watchlist" side="left">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      remove(active.id, r.stock.symbol);
                      toast({ title: `Removed ${r.stock.symbol}`, description: `From ${active.name}`, tone: "info" });
                    }}
                    className="rounded p-1 text-fg-subtle opacity-60 transition hover:bg-bear/10 hover:text-bear group-hover:opacity-100"
                    aria-label={`Remove ${r.stock.symbol} from ${active.name}`}
                  >
                    <X className="size-4" />
                  </button>
                </Tooltip>
              )}
              empty={
                <EmptyState
                  icon={Star}
                  title="This watchlist is empty"
                  description="Add stocks from the sample universe to start tracking their structure."
                  action={
                    <Button size="sm" variant="secondary" onClick={() => setDialog({ kind: "add" })}>
                      <ListPlus /> Add stocks
                    </Button>
                  }
                />
              }
            />
          </Panel>
        ) : (
          <Panel>
            <EmptyState icon={Star} title="No watchlists" action={<Button size="sm" onClick={() => openNameDialog({ kind: "create" })}>Create one</Button>} />
          </Panel>
        )}
      </div>

      <Dialog
        open={dialog?.kind === "create" || dialog?.kind === "rename"}
        onClose={() => setDialog(null)}
        title={dialog?.kind === "rename" ? "Rename watchlist" : "New watchlist"}
        size="sm"
        footer={
          <>
            <Button size="sm" variant="ghost" onClick={() => setDialog(null)}>Cancel</Button>
            <Button size="sm" variant="primary" onClick={submitName}>{dialog?.kind === "rename" ? "Save" : "Create"}</Button>
          </>
        }
      >
        <form onSubmit={(e) => { e.preventDefault(); submitName(); }}>
          <Input label="Name" autoFocus value={name} onChange={(e) => setName(e.target.value)} error={nameError} placeholder="e.g. Breakout candidates" />
        </form>
      </Dialog>

      <Dialog
        open={dialog?.kind === "add"}
        onClose={() => setDialog(null)}
        title={`Add stocks to ${active?.name ?? "watchlist"}`}
        description="Sample NSE universe"
        footer={<Button size="sm" variant="secondary" onClick={() => setDialog(null)}>Done</Button>}
      >
        <Input aria-label="Filter stocks" placeholder="Search symbol or company…" value={addQuery} onChange={(e) => setAddQuery(e.target.value)} />
        <ul className="mt-3 flex flex-col divide-y divide-border/60">
          {addCandidates.map((r) => (
            <li key={r.stock.symbol} className="flex items-center gap-3 py-2">
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-semibold text-fg">{r.stock.symbol}</p>
                <p className="truncate text-2xs text-fg-subtle">{r.stock.name}</p>
              </div>
              <Button
                size="xs"
                variant="outline"
                onClick={() => {
                  if (!active) return;
                  add(active.id, r.stock.symbol);
                  toast({ title: `Added ${r.stock.symbol}`, description: `To ${active.name}` });
                }}
              >
                <Plus /> Add
              </Button>
            </li>
          ))}
          {addCandidates.length === 0 && <li className="py-6 text-center text-xs text-fg-subtle">No more stocks to add.</li>}
        </ul>
      </Dialog>
    </PageContainer>
  );
}
