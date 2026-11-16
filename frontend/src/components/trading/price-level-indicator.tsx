import { formatPrice } from "@/lib/format";
import { clamp, cn } from "@/lib/utils";
import type { TradeLevels } from "@/types";

interface PriceLevelIndicatorProps {
  price: number;
  levels: TradeLevels;
  className?: string;
}

/**
 * Horizontal ladder showing where the latest close sits between stop,
 * entry and target. Uses the chart's level colours (stop = bear, entry =
 * chart-entry, target = bull) and labels each mark.
 */
export function PriceLevelIndicator({ price, levels, className }: PriceLevelIndicatorProps) {
  const lo = Math.min(levels.stopLoss, levels.target, price);
  const hi = Math.max(levels.stopLoss, levels.target, price);
  const pad = (hi - lo) * 0.06;
  const min = lo - pad;
  const span = hi + pad - min || 1;
  const pos = (v: number) => clamp(((v - min) / span) * 100, 0, 100);

  const marks = [
    { v: levels.stopLoss, label: "SL", fill: "bg-bear", text: "text-bear" },
    { v: levels.entry, label: "Entry", fill: "bg-chart-entry", text: "text-muted-foreground" },
    { v: levels.target, label: "TGT", fill: "bg-bull", text: "text-bull" },
  ];

  return (
    <div
      className={cn("relative py-5", className)}
      role="img"
      aria-label={`Latest close ${formatPrice(price)} relative to stop ${formatPrice(levels.stopLoss)}, entry ${formatPrice(levels.entry)}, target ${formatPrice(levels.target)}`}
    >
      <div className="relative h-1 rounded-full bg-muted">
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
            <span className={cn("block h-3 w-0.5 rounded-full", m.fill)} />
            <span className={cn("absolute left-1/2 top-3.5 -translate-x-1/2 whitespace-nowrap text-2xs font-medium", m.text)}>{m.label}</span>
          </span>
        ))}
        <span className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2" style={{ left: `${pos(price)}%` }}>
          <span className="block size-2.5 rounded-full border-2 border-card bg-foreground ring-1 ring-foreground" />
          <span className="absolute bottom-3.5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-foreground px-1.5 text-2xs font-medium text-background">
            {formatPrice(price)}
          </span>
        </span>
      </div>
    </div>
  );
}
