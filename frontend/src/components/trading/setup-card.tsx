import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { formatPrice } from "@/lib/format";
import { SETUP_TYPES } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { ScannerRow } from "@/types";
import { ChangeDisplay } from "@/components/data/price-display";
import { StatusBadge } from "@/components/data/status-badge";
import { MarketStructureBadge } from "./market-structure-badge";
import { QualityScoreBar } from "./quality-score";
import { RiskRewardDisplay } from "./risk-reward-display";
import { SignalBadge } from "./signal-badge";

/** A DETECTED setup — not a trade plan and not an order. */
export function SetupCard({ row, className }: { row: ScannerRow; className?: string }) {
  const { stock, levels } = row;
  return (
    <Link
      href={`/analysis/${encodeURIComponent(stock.symbol)}`}
      data-slot="card"
      className={cn(
        "group flex min-w-0 flex-col gap-3 rounded-xl border bg-card px-5 py-4 transition-colors hover:border-input",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground group-hover:underline underline-offset-4">{stock.symbol}</span>
            <ChangeDisplay changePct={stock.changePct} showIcon={false} />
          </div>
          <p className="truncate text-xs text-muted-foreground">{SETUP_TYPES[row.setupType].label}</p>
        </div>
        <SignalBadge signal={row.signal} />
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        <MarketStructureBadge structure={row.structure} />
        <StatusBadge kind="setup" status={row.setupStatus} />
      </div>
      <dl className="grid grid-cols-3 gap-3 border-t pt-3 tabular-nums">
        <div className="flex flex-col gap-1">
          <dt className="text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Entry</dt>
          <dd className="text-sm font-medium text-foreground">{formatPrice(levels.entry)}</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Stop</dt>
          <dd className="text-sm font-medium text-bear">{formatPrice(levels.stopLoss)}</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Target</dt>
          <dd className="text-sm font-medium text-bull">{formatPrice(levels.target)}</dd>
        </div>
      </dl>
      <div className="flex items-center justify-between">
        <RiskRewardDisplay levels={levels} variant="compact" />
        <span className="flex items-center gap-2">
          <QualityScoreBar score={row.qualityScore} />
          <ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden />
        </span>
      </div>
    </Link>
  );
}
