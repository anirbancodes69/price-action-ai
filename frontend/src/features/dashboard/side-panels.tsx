import Link from "next/link";
import { BellRing, BookOpenText, ClipboardList, ListChecks, Radar, XCircle, type LucideIcon } from "lucide-react";
import { TONE_CHIP, type Tone } from "@/lib/colors";
import { formatDateTime, formatPct, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ActivityItem, StockAnalysis, TriggerAlert } from "@/types";
import { Panel, PanelLink, RowList } from "@/components/ui/panel";
import { MarketStructureBadge } from "@/components/trading/market-structure-badge";
import { SignalBadge } from "@/components/trading/signal-badge";

const ROWS = 5;

/** What needs the reader: trigger levels, nearest (or already crossed) first. */
export function UpcomingTriggers({ triggers }: { triggers: TriggerAlert[] }) {
  const ordered = [...triggers].sort((a, b) => a.distancePct - b.distancePct).slice(0, ROWS);
  return (
    <Panel
      boxed
      title="Upcoming triggers"
      meta={<span className="text-xs text-muted-foreground">{triggers.length}</span>}
      hint="Levels that would confirm a detected setup, nearest first."
      footer={<PanelLink href="/market-scanner">All setups</PanelLink>}
    >
      <RowList>
        {ordered.map((t) => (
          <li key={t.id}>
            <Link href={`/analysis/${t.symbol}`} className="flex items-center gap-3 px-3 py-2.5 transition-colors hover:bg-accent">
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <p className="text-sm font-medium text-foreground">{t.symbol}</p>
                <p className="truncate text-xs text-muted-foreground">{t.condition}</p>
              </div>
              <div className="flex flex-col items-end gap-1 tabular-nums">
                <p className="text-sm text-foreground">{formatPrice(t.level)}</p>
                <p className={cn("text-xs", t.distancePct <= 0 ? "text-success" : "text-muted-foreground")}>
                  {t.distancePct <= 0 ? "Above trigger" : `${formatPct(t.distancePct, { signed: false })} away`}
                </p>
              </div>
            </Link>
          </li>
        ))}
      </RowList>
    </Panel>
  );
}

export function RecentAnalyses({ analyses }: { analyses: StockAnalysis[] }) {
  return (
    <Panel boxed title="Recent analyses" footer={<PanelLink href="/market-scanner">Open the scanner</PanelLink>}>
      <RowList>
        {analyses.slice(0, ROWS).map((a) => (
          <li key={a.stock.symbol}>
            <Link href={`/analysis/${a.stock.symbol}`} className="flex items-center gap-3 px-3 py-2.5 transition-colors hover:bg-accent">
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <p className="text-sm font-medium text-foreground">{a.stock.symbol}</p>
                <MarketStructureBadge structure={a.structure} variant="text" />
              </div>
              <SignalBadge signal={a.setup.signal} explain={false} />
            </Link>
          </li>
        ))}
      </RowList>
    </Panel>
  );
}

const ACTIVITY: Record<ActivityItem["kind"], { icon: LucideIcon; tone: Tone }> = {
  setup: { icon: Radar, tone: "info" },
  plan: { icon: ClipboardList, tone: "neutral" },
  trigger: { icon: BellRing, tone: "success" },
  invalidated: { icon: XCircle, tone: "destructive" },
  journal: { icon: BookOpenText, tone: "neutral" },
  watchlist: { icon: ListChecks, tone: "neutral" },
};

export function RecentActivity({ items }: { items: ActivityItem[] }) {
  return (
    <Panel boxed title="Recent activity" footer={<PanelLink href="/journal">Trading journal</PanelLink>}>
      <ol className="flex flex-col gap-3">
        {items.slice(0, ROWS).map((a) => {
          const { icon: Icon, tone } = ACTIVITY[a.kind];
          return (
            <li key={a.id} className="flex gap-3">
              <span className={cn("flex size-6 shrink-0 items-center justify-center rounded-full", TONE_CHIP[tone])}>
                <Icon className="size-3.5" aria-hidden />
              </span>
              <div className="flex min-w-0 flex-col gap-1">
                <p className="text-sm text-foreground">{a.title}</p>
                <p className="text-xs text-muted-foreground">{a.detail}</p>
                <p className="text-xs text-muted-foreground">{formatDateTime(a.at)}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </Panel>
  );
}
