import type { ReactNode } from "react";
import { TONE_CLASSES, type Tone } from "@/lib/labels";
import { cn } from "@/lib/utils";

interface BadgeProps {
  tone?: Tone;
  children: ReactNode;
  dot?: boolean;
  variant?: "soft" | "outline" | "solid";
  size?: "xs" | "sm";
  className?: string;
  title?: string;
}

/** Base pill used by every status/label badge in the system. */
export function Badge({ tone = "neutral", children, dot, variant = "soft", size = "sm", className, title }: BadgeProps) {
  const t = TONE_CLASSES[tone];
  return (
    <span
      title={title}
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-sm font-medium",
        size === "xs" ? "h-[18px] px-1.5 text-2xs" : "h-5 px-1.5 text-2xs",
        variant === "soft" && t.soft,
        variant === "outline" && cn("border bg-transparent", t.border, t.text),
        variant === "solid" && cn(t.dot, "text-white"),
        className,
      )}
    >
      {dot && <span className={cn("size-1.5 rounded-full", t.dot)} aria-hidden />}
      {children}
    </span>
  );
}
