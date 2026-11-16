import { rrTone, TONE_TEXT } from "@/lib/colors";
import { formatPct, formatPrice, formatRR } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { TradeLevels } from "@/types";
import { Eyebrow } from "@/components/data/stat";

interface RiskRewardDisplayProps {
  levels: TradeLevels;
  direction?: "long" | "short";
  variant?: "full" | "compact";
  className?: string;
}

/**
 * Visualises risk (entry → stop) against reward (entry → target) as a
 * proportional bar, with the R:R ratio and % distances. Stop is bear,
 * target is bull — the same colours the chart uses for those lines.
 */
export function RiskRewardDisplay({ levels, direction = "long", variant = "full", className }: RiskRewardDisplayProps) {
  const { entry, stopLoss, target, riskReward } = levels;
  const risk = Math.abs(entry - stopLoss);
  const reward = Math.abs(target - entry);
  const riskPct = (risk / entry) * 100;
  const rewardPct = (reward / entry) * 100;
  const total = risk + reward || 1;
  const riskShare = Math.max(8, (risk / total) * 100);
  const tone = TONE_TEXT[rrTone(riskReward)];

  if (variant === "compact") {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <div className="flex h-1.5 w-14 overflow-hidden rounded-full bg-muted" aria-hidden>
          <span className="h-full bg-bear" style={{ width: `${riskShare}%` }} />
          <span className="h-full flex-1 bg-bull" />
        </div>
        <span className={cn("text-xs font-medium tabular-nums", tone)}>{riskReward.toFixed(1)}R</span>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm text-muted-foreground">Risk / reward</span>
        <span className={cn("text-sm font-medium tabular-nums", tone)}>{formatRR(riskReward)}</span>
      </div>
      <div
        className="flex h-2 gap-0.5 overflow-hidden rounded-full"
        role="img"
        aria-label={`Risk ${formatPct(riskPct, { signed: false })}, reward ${formatPct(rewardPct, { signed: false })}`}
      >
        <span className="h-full rounded-l-full bg-bear/80" style={{ width: `${riskShare}%` }} />
        <span className="h-full flex-1 rounded-r-full bg-bull/80" />
      </div>
      <dl className="grid grid-cols-3 gap-3 tabular-nums">
        <div className="flex flex-col gap-1">
          <dt><Eyebrow>Stop{direction === "short" ? " (above)" : ""}</Eyebrow></dt>
          <dd className="text-sm font-medium text-bear">{formatPrice(stopLoss)}</dd>
          <dd className="text-xs text-muted-foreground">−{riskPct.toFixed(2)}%</dd>
        </div>
        <div className="flex flex-col items-center gap-1">
          <dt><Eyebrow>Entry</Eyebrow></dt>
          <dd className="text-sm font-medium text-foreground">{formatPrice(entry)}</dd>
        </div>
        <div className="flex flex-col items-end gap-1">
          <dt><Eyebrow>Target</Eyebrow></dt>
          <dd className="text-sm font-medium text-bull">{formatPrice(target)}</dd>
          <dd className="text-xs text-muted-foreground">+{rewardPct.toFixed(2)}%</dd>
        </div>
      </dl>
    </div>
  );
}
