import { formatPrice } from "@/lib/format";
import type { MarketIndex } from "@/types";
import { Panel, RowList } from "@/components/ui/panel";
import { ChangeDisplay } from "@/components/data/price-display";
import { MarketStatus } from "@/components/data/market-status";
import { Sparkline } from "@/components/data/sparkline";

/** Market context: key indices (at most five rows) and the NSE session state. */
export function MarketPanel({ indices }: { indices: MarketIndex[] }) {
  return (
    <Panel boxed title="Market" hint="Index values are sample data." action={<MarketStatus variant="inline" />}>
      <RowList aria-label="Key indices">
        {indices.slice(0, 5).map((idx) => (
          <li key={idx.id} className="flex items-center justify-between gap-3 px-3 py-2.5">
            <div className="flex min-w-0 flex-col gap-1">
              <p className="truncate text-xs text-muted-foreground">{idx.name}</p>
              <p className="text-sm font-medium tabular-nums text-foreground">{formatPrice(idx.value)}</p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <Sparkline values={idx.trend} width={56} height={24} className="hidden sm:block" tone={idx.id === "indiavix" ? "neutral" : undefined} />
              <ChangeDisplay changePct={idx.changePct} className="w-16 justify-end" />
            </div>
          </li>
        ))}
      </RowList>
    </Panel>
  );
}
