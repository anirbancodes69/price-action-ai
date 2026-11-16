import type { ReactNode } from "react";
import { TONE_BORDER, TONE_CHIP, TONE_FILL, TONE_TEXT, type Tone } from "@/lib/colors";
import { cn } from "@/lib/utils";

interface BadgeProps {
  tone?: Tone;
  children: ReactNode;
  /** Leading fill dot. The text still names the state (§6: never colour alone). */
  dot?: boolean;
  /** `soft` = the chip form; `outline` = a quiet bordered chip for meta and "reference only". */
  variant?: "soft" | "outline";
  className?: string;
  title?: string;
}

/** Base chip used by every status/label badge (design-standards §4 `rounded-full`, §6 chip form). */
export function Badge({ tone = "neutral", children, dot, variant = "soft", className, title }: BadgeProps) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex h-5 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2 text-2xs font-medium",
        variant === "soft" ? TONE_CHIP[tone] : cn("border bg-transparent", TONE_BORDER[tone], TONE_TEXT[tone]),
        className,
      )}
    >
      {dot && <span className={cn("size-1.5 rounded-full", TONE_FILL[tone])} aria-hidden />}
      {children}
    </span>
  );
}
