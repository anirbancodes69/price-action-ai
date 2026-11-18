import { ShieldAlert } from "lucide-react";
import { ACCOUNT_BLOCK_REASONS, BOOKS } from "@/lib/labels";
import { formatInr, formatSignedInr } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { RiskToday } from "@/types";
import { Badge } from "@/components/data/badge";
import { Panel, PanelLink, RowList } from "@/components/ui/panel";

/**
 * Today's account state per book (TRD-05 §8, PRD-07 UX-10): what is left of the daily loss budget, the losing
 * streak and open positions against their limits. A reached limit is stated in words with an icon, never by
 * colour alone. Paper and actual books are never combined.
 */
export function RiskTodayPanel({ books }: { books: RiskToday[] }) {
  return (
    <Panel
      boxed
      title="Today's risk"
      hint="Account limits for this session. A reached limit blocks new plans until tomorrow."
      footer={<PanelLink href="/settings">Risk and limits</PanelLink>}
    >
      <div className="flex flex-col gap-3">
        {books.map((b) => (
          <section key={b.book} aria-label={`${BOOKS[b.book]} book`} className="flex flex-col gap-1">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">{BOOKS[b.book]} book</h3>
              {b.blockedReason ? (
                <Badge tone="destructive">
                  <ShieldAlert className="size-3" aria-hidden /> {ACCOUNT_BLOCK_REASONS[b.blockedReason]}
                </Badge>
              ) : (
                <Badge tone="success" variant="outline">
                  Can plan
                </Badge>
              )}
            </div>
            <RowList className="text-sm tabular-nums">
              <Row label="Realised net P&L" value={formatSignedInr(b.realisedNetPnl)} tone={b.realisedNetPnl < 0 ? "text-bear" : b.realisedNetPnl > 0 ? "text-bull" : undefined} />
              <Row label="Open risk" value={formatInr(b.openRisk)} />
              <Row label="Daily loss budget left" value={`${formatInr(b.remainingDailyLoss)} of ${formatInr(b.dailyLossLimit, { decimals: false })}`} />
              <Row label="Losing streak" value={`${b.losingStreak} of ${b.maxConsecutiveLosses}`} />
              <Row label="Open positions" value={`${b.openPositions} of ${b.maxOpenPositions}`} />
            </RowList>
          </section>
        ))}
      </div>
    </Panel>
  );
}

function Row({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <li className="flex items-center justify-between gap-2 px-3 py-2">
      <span className="truncate text-muted-foreground">{label}</span>
      <span className={cn("shrink-0", tone ?? "text-foreground")}>{value}</span>
    </li>
  );
}
