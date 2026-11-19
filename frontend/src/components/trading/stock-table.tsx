"use client";

import { useMemo, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { rrTone, TONE_TEXT } from "@/lib/colors";
import { formatPrice, formatTime } from "@/lib/format";
import { SETUP_TYPES } from "@/lib/labels";
import type { ScannerRow } from "@/types";
import { DataTable, type Column } from "@/components/data/data-table";
import { ChangeDisplay } from "@/components/data/price-display";
import { StatusBadge } from "@/components/data/status-badge";
import { MarketStructureBadge } from "./market-structure-badge";
import { QualityScoreBar } from "./quality-score";
import { SignalBadge } from "./signal-badge";

/** A row without a setup has no levels: no-trade is a valid result, not a missing value. */
const NO_SETUP = <span className="text-xs text-muted-foreground">No setup</span>;
const NO_LEVEL = <span className="text-muted-foreground" aria-label="No levels">–</span>;

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
  | "signal"
  | "validity";

const ALL: Record<StockColumnKey, Column<ScannerRow>> = {
  symbol: {
    key: "symbol",
    header: "Symbol",
    sticky: true,
    grow: true,
    sortValue: (r) => r.stock.symbol,
    render: (r) => (
      <Link
        href={`/analysis/${encodeURIComponent(r.stock.symbol)}`}
        onClick={(e) => e.stopPropagation()}
        className="flex min-w-24 flex-col rounded-lg leading-tight"
      >
        <span className="text-sm font-medium text-foreground underline-offset-4 hover:underline">{r.stock.symbol}</span>
        <span className="block truncate text-xs text-muted-foreground 2xl:hidden">{r.stock.name}</span>
      </Link>
    ),
  },
  company: {
    key: "company",
    header: "Company",
    hideBelow: "2xl",
    sortValue: (r) => r.stock.name,
    render: (r) => <span className="block max-w-64 truncate text-muted-foreground">{r.stock.name}</span>,
  },
  price: {
    key: "price",
    header: "Price",
    align: "right",
    sortValue: (r) => r.stock.price,
    render: (r) => <span className="font-medium text-foreground">{formatPrice(r.stock.price)}</span>,
  },
  change: {
    key: "change",
    header: "Chg %",
    align: "right",
    hideBelow: "sm",
    sortValue: (r) => r.stock.changePct,
    render: (r) => <ChangeDisplay changePct={r.stock.changePct} showIcon={false} />,
  },
  structure: {
    key: "structure",
    header: "Structure",
    hideBelow: "lg",
    sortValue: (r) => r.structure,
    render: (r) => <MarketStructureBadge structure={r.structure} />,
  },
  setup: {
    key: "setup",
    header: "Setup",
    hideBelow: "2xl",
    sortValue: (r) => SETUP_TYPES[r.setupType].label,
    render: (r) => <span className="text-muted-foreground">{SETUP_TYPES[r.setupType].label}</span>,
  },
  entry: {
    key: "entry",
    header: "Entry",
    align: "right",
    hideBelow: "sm",
    sortValue: (r) => r.levels?.entry ?? -1,
    render: (r) => (r.levels ? <span className="text-foreground">{formatPrice(r.levels.entry)}</span> : NO_LEVEL),
  },
  stop: {
    key: "stop",
    header: "Stop-loss",
    align: "right",
    hideBelow: "xl",
    sortValue: (r) => r.levels?.stopLoss ?? -1,
    render: (r) => (r.levels ? <span className="text-bear">{formatPrice(r.levels.stopLoss)}</span> : NO_LEVEL),
  },
  target: {
    key: "target",
    header: "Target",
    align: "right",
    hideBelow: "2xl",
    sortValue: (r) => r.levels?.target ?? -1,
    render: (r) => (r.levels ? <span className="text-bull">{formatPrice(r.levels.target)}</span> : NO_LEVEL),
  },
  rr: {
    key: "rr",
    header: "R:R",
    align: "right",
    hideBelow: "sm",
    sortValue: (r) => r.levels?.riskReward ?? -1,
    render: (r) =>
      r.levels ? (
        <span className={TONE_TEXT[rrTone(r.levels.riskReward)]}>
          1:{r.levels.riskReward.toFixed(1)}
        </span>
      ) : (
        NO_LEVEL
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
    sortValue: (r) => r.setupStatus ?? "",
    render: (r) => (r.setupStatus ? <StatusBadge kind="setup" status={r.setupStatus} /> : NO_SETUP),
  },
  signal: {
    key: "signal",
    header: "Signal",
    sortValue: (r) => r.signal,
    render: (r) => <SignalBadge signal={r.signal} />,
  },
  validity: {
    key: "validity",
    header: "Valid until",
    hideBelow: "lg",
    sortValue: (r) => r.validUntil ?? "",
    // Signal time and expiry (TRD-04 §12). Dash when there is no live signal.
    render: (r) =>
      r.validUntil ? (
        <span className="tabular-nums text-muted-foreground" title={r.signalAt ? `Signal at the ${formatTime(r.signalAt)} close` : undefined}>
          {formatTime(r.validUntil)}
        </span>
      ) : (
        <span className="text-muted-foreground" aria-label="No live signal">—</span>
      ),
  },
};

export const SCANNER_COLUMNS: StockColumnKey[] = [
  "symbol", "company", "price", "change", "structure", "setup", "entry", "stop", "target", "rr", "quality", "status", "signal", "validity",
];

interface StockTableProps {
  rows: ScannerRow[];
  columns?: StockColumnKey[];
  /** Extra trailing column (e.g. remove-from-watchlist). */
  actions?: (row: ScannerRow) => ReactNode;
  empty?: ReactNode;
  initialSort?: { key: StockColumnKey; dir: "asc" | "desc" };
  caption?: string;
  /** Show only the first N rows (dashboard panels: 5). */
  limit?: number;
}

/** Pre-configured DataTable for stock rows; clicking a row opens the analysis. */
export function StockTable({ rows, columns = SCANNER_COLUMNS, actions, empty, initialSort, caption, limit }: StockTableProps) {
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
      limit={limit}
    />
  );
}
