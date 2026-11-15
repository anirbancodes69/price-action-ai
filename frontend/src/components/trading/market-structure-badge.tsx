import { ArrowLeftRight, Shuffle, TrendingDown, TrendingUp, type LucideIcon } from "lucide-react";
import { STRUCTURES, TONE_CLASSES } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { MarketStructure } from "@/types";

const ICONS: Record<MarketStructure, LucideIcon> = {
  uptrend: TrendingUp,
  downtrend: TrendingDown,
  range: ArrowLeftRight,
  transition: Shuffle,
};

export function MarketStructureBadge({
  structure,
  className,
  variant = "soft",
}: {
  structure: MarketStructure;
  className?: string;
  variant?: "soft" | "text";
}) {
  const meta = STRUCTURES[structure];
  const Icon = ICONS[structure];
  const tone = TONE_CLASSES[meta.tone];
  return (
    <span
      title={meta.description}
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap text-xs font-medium",
        variant === "soft" ? cn("h-5 rounded-sm px-1.5 text-2xs", tone.soft) : tone.text,
        className,
      )}
    >
      <Icon className="size-3.5" aria-hidden />
      {meta.label}
    </span>
  );
}
