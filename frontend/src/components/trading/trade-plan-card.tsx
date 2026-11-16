import type { ReactNode } from "react";
import Link from "next/link";
import { FileText, Receipt } from "lucide-react";
import { formatDate, formatInr, formatInt, formatPrice } from "@/lib/format";
import { SETUP_TYPES } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { TradePlan } from "@/types";
import { StatusBadge } from "@/components/data/status-badge";
import { RiskRewardDisplay } from "./risk-reward-display";
import { SignalBadge } from "./signal-badge";

/**
 * A trader-authored PROPOSAL. The card makes the distinction explicit:
 * plans without a linked order are labelled "Proposed — not an order";
 * plans with an executed order show the order reference.
 */
export function TradePlanCard({ plan, actions, className }: { plan: TradePlan; actions?: ReactNode; className?: string }) {
  const executed = !!plan.linkedOrderId;
  return (
    <article data-slot="card" className={cn("flex min-w-0 flex-col rounded-xl border bg-card", className)}>
      <header className="flex items-start justify-between gap-3 border-b px-5 py-4">
        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex items-center gap-2">
            <Link href={`/analysis/${encodeURIComponent(plan.symbol)}`} className="rounded-lg text-sm font-medium text-foreground underline-offset-4 hover:underline">
              {plan.symbol}
            </Link>
            <span className="font-mono text-xs text-muted-foreground">{plan.id}</span>
          </div>
          <p className="truncate text-xs text-muted-foreground">
            {SETUP_TYPES[plan.setupType].label} · {plan.companyName}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusBadge kind="plan" status={plan.status} />
          <SignalBadge signal={plan.signal} />
        </div>
      </header>

      <div className="flex flex-col gap-4 px-5 py-4">
        <RiskRewardDisplay levels={plan} />
        <dl className="grid grid-cols-3 gap-3 tabular-nums">
          <div className="flex flex-col gap-1">
            <dt className="text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Quantity</dt>
            <dd className="text-sm font-medium text-foreground">{formatInt(plan.quantity)}</dd>
          </div>
          <div className="flex flex-col gap-1">
            <dt className="text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Capital at risk</dt>
            <dd className="text-sm font-medium text-bear">{formatInr(plan.riskAmount, { decimals: false })}</dd>
          </div>
          <div className="flex flex-col gap-1 items-end">
            <dt className="text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Position value</dt>
            <dd className="text-sm font-medium text-foreground">{formatInr(plan.entry * plan.quantity, { decimals: false })}</dd>
          </div>
        </dl>
        {plan.note && <p className="text-sm leading-relaxed text-muted-foreground">{plan.note}</p>}
      </div>

      <footer className="mt-auto flex flex-wrap items-center justify-between gap-2 border-t px-5 py-2.5">
        {executed ? (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-success">
            <Receipt className="size-3.5" aria-hidden />
            Executed order · {plan.linkedOrderId}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            <FileText className="size-3.5" aria-hidden />
            Proposed plan — not an order
          </span>
        )}
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">Updated {formatDate(plan.updatedAt)}</span>
          {actions}
        </div>
      </footer>
    </article>
  );
}

export function PlanLevelsInline({ entry, stopLoss, target }: Pick<TradePlan, "entry" | "stopLoss" | "target">) {
  return (
    <span className="text-sm tabular-nums">
      <span className="text-foreground">{formatPrice(entry)}</span>
      <span className="text-muted-foreground"> / </span>
      <span className="text-bear">{formatPrice(stopLoss)}</span>
      <span className="text-muted-foreground"> / </span>
      <span className="text-bull">{formatPrice(target)}</span>
    </span>
  );
}
