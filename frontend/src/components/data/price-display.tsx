import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { formatPct, formatPrice, formatSignedNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

interface PriceDisplayProps {
  price: number;
  change?: number;
  changePct?: number;
  size?: "sm" | "md" | "lg" | "xl";
  /** Show ₹ prefix. */
  currency?: boolean;
  layout?: "inline" | "stacked";
  className?: string;
}

const PRICE_SIZE = {
  sm: "text-[13px]",
  md: "text-sm",
  lg: "text-lg",
  xl: "text-2xl",
};

export function PriceDisplay({
  price,
  change,
  changePct,
  size = "md",
  currency = true,
  layout = "inline",
  className,
}: PriceDisplayProps) {
  return (
    <div
      className={cn(
        "tnum flex",
        layout === "inline" ? "items-baseline gap-2" : "flex-col gap-0.5",
        className,
      )}
    >
      <span className={cn("font-semibold tracking-tight text-fg", PRICE_SIZE[size])}>
        {currency && <span className="mr-px text-fg-muted">₹</span>}
        {formatPrice(price)}
      </span>
      {changePct !== undefined && <ChangeDisplay change={change} changePct={changePct} size={size === "xl" || size === "lg" ? "md" : "sm"} />}
    </div>
  );
}

interface ChangeDisplayProps {
  change?: number;
  changePct: number;
  size?: "sm" | "md";
  showIcon?: boolean;
  className?: string;
}

export function ChangeDisplay({ change, changePct, size = "sm", showIcon = true, className }: ChangeDisplayProps) {
  const up = changePct > 0;
  const down = changePct < 0;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <span
      className={cn(
        "tnum inline-flex items-center gap-0.5 font-medium",
        size === "sm" ? "text-xs" : "text-sm",
        up ? "text-bull" : down ? "text-bear" : "text-fg-muted",
        className,
      )}
    >
      {showIcon && (up || down) && <Icon className={size === "sm" ? "size-3.5" : "size-4"} aria-hidden />}
      {change !== undefined && <span>{formatSignedNumber(change)}</span>}
      <span>{change !== undefined ? `(${formatPct(changePct)})` : formatPct(changePct)}</span>
    </span>
  );
}
