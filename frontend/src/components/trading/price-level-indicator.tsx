import { formatPrice } from "@/lib/format";
import { clamp, cn } from "@/lib/utils";
import type { TradeLevels } from "@/types";

interface PriceLevelIndicatorProps {
  price: number;
  levels: TradeLevels;
  className?: string;
}

/**
 * Horizontal ladder showing where the current price sits between stop,
 * entry and target. Values outside the band are clamped to the edges.
 */
export function PriceLevelIndicator({ price, levels, className }: PriceLevelIndicatorProps) {
  const lo = Math.min(levels.stopLoss, levels.target, price);
  const hi = Math.max(levels.stopLoss, levels.target, price);
  const pad = (hi - lo) * 0.06;
  const min = lo - pad;
  const span = hi + pad - min || 1;
  const pos = (v: number) => clamp(((v - min) / span) * 100, 0, 100);

  const marks = [
    { v: levels.stopLoss, label: "SL", cls: "bg-bear", text: "text-bear" },
    { v: levels.entry, label: "Entry", cls: "bg-fg", text: "text-fg-muted" },
    { v: levels.target, label: "TGT", cls: "bg-bull", text: "text-bull" },
  ];

  return (
    <div
      className={cn("relative pt-5 pb-5", className)}
      role="img"
      aria-label={`Price ${formatPrice(price)} relative to stop ${formatPrice(levels.stopLoss)}, entry ${formatPrice(levels.entry)}, target ${formatPrice(levels.target)}`}
    >
      <div className="relative h-1 rounded-full bg-hover">
        <span
          className="absolute inset-y-0 rounded-full bg-bear/40"
          style={{ left: `${Math.min(pos(levels.stopLoss), pos(levels.entry))}%`, width: `${Math.abs(pos(levels.entry) - pos(levels.stopLoss))}%` }}
        />
        <span
          className="absolute inset-y-0 rounded-full bg-bull/40"
          style={{ left: `${Math.min(pos(levels.entry), pos(levels.target))}%`, width: `${Math.abs(pos(levels.target) - pos(levels.entry))}%` }}
        />
        {marks.map((m) => (
          <span key={m.label} className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2" style={{ left: `${pos(m.v)}%` }}>
            <span className={cn("block h-3 w-0.5 rounded-full", m.cls)} />
            <span className={cn("tnum absolute top-3 left-1/2 -translate-x-1/2 text-[10px] font-medium whitespace-nowrap", m.text)}>
              {m.label}
            </span>
          </span>
        ))}
        <span className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2" style={{ left: `${pos(price)}%` }}>
          <span className="block size-2.5 rounded-full border-2 border-surface bg-accent ring-1 ring-accent" />
          <span className="tnum absolute bottom-3.5 left-1/2 -translate-x-1/2 rounded-sm bg-accent px-1 text-[10px] font-semibold whitespace-nowrap text-accent-fg">
            {formatPrice(price)}
          </span>
        </span>
      </div>
    </div>
  );
}
