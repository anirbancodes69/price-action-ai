import { formatPct, formatPrice, formatRR } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { TradeLevels } from "@/types";

interface RiskRewardDisplayProps {
  levels: TradeLevels;
  direction?: "long" | "short";
  variant?: "full" | "compact";
  className?: string;
}

/**
 * Visualises risk (entry → stop) against reward (entry → target) as a
 * proportional bar, with the R:R ratio and % distances.
 */
export function RiskRewardDisplay({ levels, direction = "long", variant = "full", className }: RiskRewardDisplayProps) {
  const { entry, stopLoss, target, riskReward } = levels;
  const risk = Math.abs(entry - stopLoss);
  const reward = Math.abs(target - entry);
  const riskPct = (risk / entry) * 100;
  const rewardPct = (reward / entry) * 100;
  const total = risk + reward || 1;
  const riskShare = Math.max(8, (risk / total) * 100);
  const rrTone = riskReward >= 2 ? "text-bull" : riskReward >= 1.5 ? "text-warn" : "text-bear";

  if (variant === "compact") {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <div className="flex h-1.5 w-14 overflow-hidden rounded-full bg-hover" aria-hidden>
          <span className="h-full bg-bear/80" style={{ width: `${riskShare}%` }} />
          <span className="h-full flex-1 bg-bull/80" />
        </div>
        <span className={cn("tnum text-xs font-medium", rrTone)}>{riskReward.toFixed(1)}R</span>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col gap-2.5", className)}>
      <div className="flex items-baseline justify-between">
        <span className="text-xs text-fg-muted">Risk / reward</span>
        <span className={cn("tnum text-sm font-semibold", rrTone)}>{formatRR(riskReward)}</span>
      </div>
      <div className="flex h-2 overflow-hidden rounded-sm" role="img" aria-label={`Risk ${formatPct(riskPct, { signed: false })}, reward ${formatPct(rewardPct, { signed: false })}`}>
        <span className="h-full bg-bear/70" style={{ width: `${riskShare}%` }} />
        <span className="w-0.5 bg-fg" />
        <span className="h-full flex-1 bg-bull/70" />
      </div>
      <div className="tnum grid grid-cols-3 text-2xs">
        <div>
          <p className="text-fg-subtle">Stop {direction === "short" ? "(above)" : ""}</p>
          <p className="text-[13px] font-medium text-bear">{formatPrice(stopLoss)}</p>
          <p className="text-fg-subtle">−{riskPct.toFixed(2)}%</p>
        </div>
        <div className="text-center">
          <p className="text-fg-subtle">Entry</p>
          <p className="text-[13px] font-medium text-fg">{formatPrice(entry)}</p>
        </div>
        <div className="text-right">
          <p className="text-fg-subtle">Target</p>
          <p className="text-[13px] font-medium text-bull">{formatPrice(target)}</p>
          <p className="text-fg-subtle">+{rewardPct.toFixed(2)}%</p>
        </div>
      </div>
    </div>
  );
}
