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
      className={cn(
        "group flex flex-col gap-3 rounded-md border border-border bg-surface p-3.5 transition-colors hover:border-border-strong hover:bg-hover/40",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-semibold text-fg">{stock.symbol}</span>
            <ChangeDisplay changePct={stock.changePct} showIcon={false} />
          </div>
          <p className="truncate text-2xs text-fg-subtle">{SETUP_TYPES[row.setupType].label}</p>
        </div>
        <SignalBadge signal={row.signal} />
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        <MarketStructureBadge structure={row.structure} />
        <StatusBadge kind="setup" status={row.setupStatus} />
      </div>
      <dl className="tnum grid grid-cols-3 gap-2 border-t border-border pt-2.5 text-2xs">
        <div>
          <dt className="text-fg-subtle">Entry</dt>
          <dd className="text-xs font-medium text-fg">{formatPrice(levels.entry)}</dd>
        </div>
        <div>
          <dt className="text-fg-subtle">Stop</dt>
          <dd className="text-xs font-medium text-bear">{formatPrice(levels.stopLoss)}</dd>
        </div>
        <div>
          <dt className="text-fg-subtle">Target</dt>
          <dd className="text-xs font-medium text-bull">{formatPrice(levels.target)}</dd>
        </div>
      </dl>
      <div className="flex items-center justify-between">
        <RiskRewardDisplay levels={levels} variant="compact" />
        <span className="flex items-center gap-2">
          <QualityScoreBar score={row.qualityScore} />
          <ChevronRight className="size-4 text-fg-subtle transition-transform group-hover:translate-x-0.5" aria-hidden />
        </span>
      </div>
    </Link>
  );
}
