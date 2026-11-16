"use client";

import { useMemo, useState } from "react";
import { ListPlus, MoreHorizontal, Pencil, Plus, Star, Trash2, X } from "lucide-react";
import type { ScannerRow } from "@/types";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Dropdown } from "@/components/ui/dropdown";
import { Input } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import { SectionLinks } from "@/components/ui/section-links";
import { useToast } from "@/components/ui/toast";
import { Tooltip } from "@/components/ui/tooltip";
import { Empty } from "@/components/data/empty";
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
    <PageFrame>
      <PageHeader
        title="Watchlists"
        description="Track the stocks you follow and see their structure and setup status at a glance."
        meta={<SampleDataBadge asOf={asOf} />}
        actions={
          <>
            <Button variant="outline" onClick={() => openNameDialog({ kind: "create" })}>
              <Plus /> New watchlist
            </Button>
            {active && (
              <Button
                variant="primary"
                onClick={() => {
                  setAddQuery("");
                  setDialog({ kind: "add" });
                }}
              >
                <ListPlus /> Add stocks
              </Button>
            )}
          </>
        }
      />

      <div className="grid grid-cols-1 gap-6 md:grid-cols-[14rem_minmax(0,1fr)]">
        <SectionLinks
          ariaLabel="Watchlists"
          value={active?.id ?? ""}
          onChange={setActiveId}
          items={watchlists.map((w) => ({ value: w.id, label: w.name, icon: Star, count: w.symbols.length }))}
        />

        {active ? (
          <Panel
            title={active.name}
            meta={<span className="text-xs text-muted-foreground">{active.symbols.length} stocks</span>}
            hint="Select a row to open the analysis."
            action={
              <Dropdown
                width="w-48"
                trigger={({ open, toggle, id }) => (
                  <Button size="icon" variant="ghost" onClick={toggle} aria-label="Watchlist options" aria-expanded={open} aria-haspopup="menu" aria-controls={open ? id : undefined}>
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
            }
          >
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
                    className="rounded-lg p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                    aria-label={`Remove ${r.stock.symbol} from ${active.name}`}
                  >
                    <X className="size-4" />
                  </button>
                </Tooltip>
              )}
              empty={
                <Empty
                  icon={Star}
                  title="This watchlist is empty"
                  description="Add stocks from the sample universe to start tracking their structure."
                  action={
                    <Button variant="outline" size="sm" onClick={() => setDialog({ kind: "add" })}>
                      <ListPlus /> Add stocks
                    </Button>
                  }
                />
              }
            />
          </Panel>
        ) : (
          <div data-slot="card" className="rounded-xl border bg-card">
            <Empty
              icon={Star}
              title="No watchlists yet"
              description="Create a watchlist to follow the structure of the stocks you care about."
              action={
                <Button variant="outline" size="sm" onClick={() => openNameDialog({ kind: "create" })}>
                  <Plus /> New watchlist
                </Button>
              }
            />
          </div>
        )}
      </div>

      <Dialog
        open={dialog?.kind === "create" || dialog?.kind === "rename"}
        onClose={() => setDialog(null)}
        title={dialog?.kind === "rename" ? "Rename watchlist" : "New watchlist"}
        size="sm"
        footer={
          <>
            <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
            <Button variant="primary" onClick={submitName}>{dialog?.kind === "rename" ? "Save" : "Create"}</Button>
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
        footer={<Button variant="outline" onClick={() => setDialog(null)}>Done</Button>}
      >
        <div className="flex flex-col gap-3">
        <Input aria-label="Filter stocks" placeholder="Search symbol or company…" value={addQuery} onChange={(e) => setAddQuery(e.target.value)} />
        <ul className="flex flex-col divide-y">
          {addCandidates.map((r) => (
            <li key={r.stock.symbol} className="flex items-center gap-3 py-2">
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <p className="text-sm font-medium text-foreground">{r.stock.symbol}</p>
                <p className="truncate text-xs text-muted-foreground">{r.stock.name}</p>
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
          {addCandidates.length === 0 && <li className="py-6 text-center text-sm text-muted-foreground">No more stocks to add.</li>}
        </ul>
        </div>
      </Dialog>
    </PageFrame>
  );
}
