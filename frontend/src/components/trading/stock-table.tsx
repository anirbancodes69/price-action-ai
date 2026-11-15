"use client";

import { useMemo, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { formatPrice } from "@/lib/format";
import { SETUP_TYPES } from "@/lib/labels";
import type { ScannerRow } from "@/types";
import { DataTable, type Column } from "@/components/data/data-table";
import { ChangeDisplay } from "@/components/data/price-display";
import { StatusBadge } from "@/components/data/status-badge";
import { MarketStructureBadge } from "./market-structure-badge";
import { QualityScoreBar } from "./quality-score";
import { SignalBadge } from "./signal-badge";

export type StockColumnKey =
  | "symbol"
  | "company"
  | "price"
  | "change"
  | "structure"
  | "setup"
  | "entry"
  | "stop"
  | "target"
  | "rr"
  | "quality"
  | "status"
  | "signal";

const ALL: Record<StockColumnKey, Column<ScannerRow>> = {
  symbol: {
    key: "symbol",
    header: "Symbol",
    sticky: true,
    sortValue: (r) => r.stock.symbol,
    render: (r) => (
      <Link
        href={`/analysis/${encodeURIComponent(r.stock.symbol)}`}
        onClick={(e) => e.stopPropagation()}
        className="flex flex-col leading-tight"
      >
        <span className="text-[13px] font-semibold text-fg hover:text-accent">{r.stock.symbol}</span>
        <span className="block max-w-28 truncate text-2xs text-fg-subtle sm:max-w-40 2xl:hidden">{r.stock.name}</span>
      </Link>
    ),
  },
  company: {
    key: "company",
    header: "Company",
    hideBelow: "2xl",
    sortValue: (r) => r.stock.name,
    render: (r) => <span className="block max-w-56 truncate text-fg-muted">{r.stock.name}</span>,
  },
  price: {
    key: "price",
    header: "Price",
    align: "right",
    sortValue: (r) => r.stock.price,
    render: (r) => <span className="font-medium text-fg">{formatPrice(r.stock.price)}</span>,
  },
  change: {
    key: "change",
    header: "Chg %",
    align: "right",
    sortValue: (r) => r.stock.changePct,
    render: (r) => <ChangeDisplay changePct={r.stock.changePct} showIcon={false} />,
  },
  structure: {
    key: "structure",
    header: "Structure",
    hideBelow: "md",
    sortValue: (r) => r.structure,
    render: (r) => <MarketStructureBadge structure={r.structure} />,
  },
  setup: {
    key: "setup",
    header: "Setup",
    hideBelow: "md",
    sortValue: (r) => SETUP_TYPES[r.setupType].label,
    render: (r) => <span className="text-fg-muted">{SETUP_TYPES[r.setupType].label}</span>,
  },
  entry: {
    key: "entry",
    header: "Entry",
    align: "right",
    hideBelow: "sm",
    sortValue: (r) => r.levels.entry,
    render: (r) => <span className="text-fg">{formatPrice(r.levels.entry)}</span>,
  },
  stop: {
    key: "stop",
    header: "Stop-loss",
    align: "right",
    hideBelow: "lg",
    sortValue: (r) => r.levels.stopLoss,
    render: (r) => <span className="text-bear">{formatPrice(r.levels.stopLoss)}</span>,
  },
  target: {
    key: "target",
    header: "Target",
    align: "right",
    hideBelow: "2xl",
    sortValue: (r) => r.levels.target,
    render: (r) => <span className="text-bull">{formatPrice(r.levels.target)}</span>,
  },
  rr: {
    key: "rr",
    header: "R:R",
    align: "right",
    hideBelow: "sm",
    sortValue: (r) => r.levels.riskReward,
    render: (r) => (
      <span className={r.levels.riskReward >= 2 ? "text-bull" : r.levels.riskReward >= 1.5 ? "text-warn" : "text-fg-muted"}>
        1:{r.levels.riskReward.toFixed(1)}
      </span>
    ),
  },
  quality: {
    key: "quality",
    header: "Quality",
    hideBelow: "2xl",
    sortValue: (r) => r.qualityScore,
    render: (r) => <QualityScoreBar score={r.qualityScore} />,
  },
  status: {
    key: "status",
    header: "Setup status",
    hideBelow: "md",
    sortValue: (r) => r.setupStatus,
    render: (r) => <StatusBadge kind="setup" status={r.setupStatus} />,
  },
  signal: {
    key: "signal",
    header: "Signal",
    sortValue: (r) => r.signal,
    render: (r) => <SignalBadge signal={r.signal} />,
  },
};

export const SCANNER_COLUMNS: StockColumnKey[] = [
  "symbol", "company", "price", "change", "structure", "setup", "entry", "stop", "target", "rr", "quality", "status", "signal",
];

interface StockTableProps {
  rows: ScannerRow[];
  columns?: StockColumnKey[];
  /** Extra trailing column (e.g. remove-from-watchlist). */
  actions?: (row: ScannerRow) => ReactNode;
  empty?: ReactNode;
  initialSort?: { key: StockColumnKey; dir: "asc" | "desc" };
  caption?: string;
}

/** Pre-configured DataTable for stock rows; clicking a row opens the analysis. */
export function StockTable({ rows, columns = SCANNER_COLUMNS, actions, empty, initialSort, caption }: StockTableProps) {
  const router = useRouter();
  const cols = useMemo(() => {
    const list = columns.map((k) => ALL[k]);
    if (actions) {
      list.push({ key: "actions", header: <span className="sr-only">Actions</span>, align: "right", render: actions });
    }
    return list;
  }, [columns, actions]);

  return (
    <DataTable
      columns={cols}
      rows={rows}
      rowKey={(r) => r.stock.symbol}
      onRowClick={(r) => router.push(`/analysis/${encodeURIComponent(r.stock.symbol)}`)}
      empty={empty}
      initialSort={initialSort}
      caption={caption}
    />
  );
}
