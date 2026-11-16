import { ArrowLeftRight, Shuffle, TrendingDown, TrendingUp, type LucideIcon } from "lucide-react";
import { TONE_CHIP, TONE_TEXT } from "@/lib/colors";
import { STRUCTURES } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { MarketStructure } from "@/types";

const ICONS: Record<MarketStructure, LucideIcon> = {
  uptrend: TrendingUp,
  downtrend: TrendingDown,
  range: ArrowLeftRight,
  transition: Shuffle,
};

/** Structure chip: icon + word + tone (never colour alone). */
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
  return (
    <span
      title={meta.description}
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap font-medium",
        variant === "soft" ? cn("h-5 rounded-full px-2 text-2xs", TONE_CHIP[meta.tone]) : cn("text-xs", TONE_TEXT[meta.tone]),
        className,
      )}
    >
      <Icon className="size-3.5" aria-hidden />
      {meta.label}
    </span>
  );
}
