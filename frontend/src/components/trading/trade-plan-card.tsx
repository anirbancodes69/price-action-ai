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
    <article className={cn("flex flex-col rounded-md border border-border bg-surface", className)}>
      <header className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Link href={`/analysis/${encodeURIComponent(plan.symbol)}`} className="text-[13px] font-semibold text-fg hover:text-accent">
              {plan.symbol}
            </Link>
            <span className="tnum text-2xs text-fg-subtle">{plan.id}</span>
          </div>
          <p className="truncate text-2xs text-fg-subtle">
            {SETUP_TYPES[plan.setupType].label} · {plan.companyName}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusBadge kind="plan" status={plan.status} />
          <SignalBadge signal={plan.signal} />
        </div>
      </header>

      <div className="flex flex-col gap-4 px-4 py-3.5">
        <RiskRewardDisplay levels={plan} />
        <dl className="tnum grid grid-cols-3 gap-2 text-2xs">
          <div>
            <dt className="text-fg-subtle">Quantity</dt>
            <dd className="text-xs font-medium text-fg">{formatInt(plan.quantity)}</dd>
          </div>
          <div>
            <dt className="text-fg-subtle">Capital at risk</dt>
            <dd className="text-xs font-medium text-bear">{formatInr(plan.riskAmount, { decimals: false })}</dd>
          </div>
          <div className="text-right">
            <dt className="text-fg-subtle">Position value</dt>
            <dd className="text-xs font-medium text-fg">{formatInr(plan.entry * plan.quantity, { decimals: false })}</dd>
          </div>
        </dl>
        {plan.note && <p className="text-xs leading-relaxed text-fg-muted">{plan.note}</p>}
      </div>

      <footer className="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-border px-4 py-2.5">
        {executed ? (
          <span className="inline-flex items-center gap-1.5 text-2xs font-medium text-bull">
            <Receipt className="size-3.5" aria-hidden />
            Executed order · {plan.linkedOrderId}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 text-2xs font-medium text-fg-muted">
            <FileText className="size-3.5" aria-hidden />
            Proposed plan — not an order
          </span>
        )}
        <div className="flex items-center gap-1.5">
          <span className="text-2xs text-fg-subtle">Updated {formatDate(plan.updatedAt)}</span>
          {actions}
        </div>
      </footer>
    </article>
  );
}

export function PlanLevelsInline({ entry, stopLoss, target }: Pick<TradePlan, "entry" | "stopLoss" | "target">) {
  return (
    <span className="tnum text-xs">
      <span className="text-fg">{formatPrice(entry)}</span>
      <span className="text-fg-subtle"> / </span>
      <span className="text-bear">{formatPrice(stopLoss)}</span>
      <span className="text-fg-subtle"> / </span>
      <span className="text-bull">{formatPrice(target)}</span>
    </span>
  );
}
