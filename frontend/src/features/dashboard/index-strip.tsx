import { formatPrice } from "@/lib/format";
import type { MarketIndex } from "@/types";
import { ChangeDisplay } from "@/components/data/price-display";
import { Sparkline } from "@/components/data/sparkline";
import { MarketStatus } from "@/components/data/market-status";

/** Market overview strip: key indices + session state. */
export function IndexStrip({ indices }: { indices: MarketIndex[] }) {
  return (
    <section aria-label="Market overview" className="grid grid-cols-2 overflow-hidden rounded-md border border-border bg-surface md:grid-cols-3 xl:grid-cols-5">
      {indices.map((idx) => (
        <div key={idx.id} className="flex items-center justify-between gap-3 border-b border-r border-border px-4 py-3 last:border-r-0 xl:border-b-0">
          <div className="min-w-0">
            <p className="text-2xs font-medium uppercase tracking-wider text-fg-subtle">{idx.name}</p>
            <p className="tnum mt-1 text-[15px] font-semibold tracking-tight text-fg">{formatPrice(idx.value)}</p>
            <ChangeDisplay change={idx.change} changePct={idx.changePct} className="mt-0.5" />
          </div>
          <Sparkline values={idx.trend} width={72} height={32} className="hidden shrink-0 sm:block" tone={idx.id === "indiavix" ? "neutral" : undefined} />
        </div>
      ))}
      <div className="col-span-2 flex flex-col justify-center gap-1.5 px-4 py-3 md:col-span-1">
        <p className="text-2xs font-medium uppercase tracking-wider text-fg-subtle">Market status</p>
        <MarketStatus variant="inline" />
        <p className="text-2xs text-fg-subtle">Index values are sample data.</p>
      </div>
    </section>
  );
}
