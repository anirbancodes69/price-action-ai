import Link from "next/link";
import {
  Activity,
  BellRing,
  BookOpenText,
  ClipboardList,
  History,
  ListChecks,
  Radar,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { formatDateTime, formatPct, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ActivityItem, StockAnalysis, TriggerAlert } from "@/types";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { MarketStructureBadge } from "@/components/trading/market-structure-badge";
import { SignalBadge } from "@/components/trading/signal-badge";

export function UpcomingTriggers({ triggers }: { triggers: TriggerAlert[] }) {
  return (
    <Panel>
      <PanelHeader title="Upcoming trade triggers" description="Levels that would confirm a detected setup" icon={<BellRing />} />
      <ul className="divide-y divide-border/60">
        {triggers.map((t) => (
          <li key={t.id}>
            <Link href={`/analysis/${t.symbol}`} className="flex items-center gap-3 px-4 py-2.5 transition-colors hover:bg-hover/50">
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-semibold text-fg">{t.symbol}</p>
                <p className="truncate text-2xs text-fg-subtle">{t.condition}</p>
              </div>
              <div className="tnum text-right">
                <p className="text-[13px] font-medium text-fg">{formatPrice(t.level)}</p>
                <p className={cn("text-2xs", t.distancePct <= 0 ? "text-bull" : "text-fg-subtle")}>
                  {t.distancePct <= 0 ? "Above trigger" : `${formatPct(t.distancePct, { signed: false })} away`}
                </p>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export function RecentAnalyses({ analyses }: { analyses: StockAnalysis[] }) {
  return (
    <Panel>
      <PanelHeader title="Recent analyses" icon={<History />} />
      <ul className="divide-y divide-border/60">
        {analyses.map((a) => (
          <li key={a.stock.symbol}>
            <Link href={`/analysis/${a.stock.symbol}`} className="flex items-center gap-3 px-4 py-2.5 transition-colors hover:bg-hover/50">
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-semibold text-fg">{a.stock.symbol}</p>
                <MarketStructureBadge structure={a.structure} variant="text" className="text-2xs" />
              </div>
              <SignalBadge signal={a.setup.signal} />
            </Link>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

const ACTIVITY_ICONS: Record<ActivityItem["kind"], { icon: LucideIcon; cls: string }> = {
  setup: { icon: Radar, cls: "text-accent bg-accent/10" },
  plan: { icon: ClipboardList, cls: "text-info bg-info/10" },
  trigger: { icon: BellRing, cls: "text-bull bg-bull/10" },
  invalidated: { icon: XCircle, cls: "text-bear bg-bear/10" },
  journal: { icon: BookOpenText, cls: "text-warn bg-warn/10" },
  watchlist: { icon: ListChecks, cls: "text-fg-muted bg-hover" },
};

export function RecentActivity({ items }: { items: ActivityItem[] }) {
  return (
    <Panel>
      <PanelHeader title="Recent activity" icon={<Activity />} />
      <ol className="flex flex-col px-4 py-3">
        {items.map((a, i) => {
          const { icon: Icon, cls } = ACTIVITY_ICONS[a.kind];
          return (
            <li key={a.id} className="relative flex gap-3 pb-4 last:pb-0">
              {i < items.length - 1 && <span className="absolute left-3 top-7 bottom-0 w-px bg-border" aria-hidden />}
              <span className={cn("flex size-6 shrink-0 items-center justify-center rounded-full", cls)}>
                <Icon className="size-3.5" aria-hidden />
              </span>
              <div className="min-w-0 pt-0.5">
                <p className="text-[13px] text-fg">{a.title}</p>
                <p className="text-xs text-fg-muted">{a.detail}</p>
                <p className="mt-0.5 text-2xs text-fg-subtle">{formatDateTime(a.at)}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </Panel>
  );
}
