import Link from "next/link";
import type { ReactNode } from "react";
import { TONE_TEXT, type Tone } from "@/lib/colors";
import { cn } from "@/lib/utils";

/**
 * Headline figures (design-standards §5, §8, §10).
 *
 * - `Eyebrow`: the micro-label, used once at the top of a card.
 * - `Stat`: label, figure (condensed numeric face) and hint.
 * - `StatGrid`: the stat row — ONE card holding 2 to 4 Stats, never four
 *   separate cards.
 */

export function Eyebrow({ children, className, as: Tag = "span" }: { children: ReactNode; className?: string; as?: "span" | "p" | "h2" | "h3" }) {
  return <Tag className={cn("text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground", className)}>{children}</Tag>;
}

interface StatProps {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  /**
   * Colour the figure only when the colour carries meaning (§6): a signed
   * P&L (bull/bear) or a status. The figure's sign or the label names it.
   */
  tone?: Tone;
  /** Every figure on a dashboard links to the page that holds the rest (§10). */
  href?: string;
  className?: string;
}

export function Stat({ label, value, hint, tone, href, className }: StatProps) {
  const body = (
    <>
      <Eyebrow>{label}</Eyebrow>
      <span className={cn("font-stat text-4xl leading-none", tone ? TONE_TEXT[tone] : "text-foreground")}>{value}</span>
      {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
    </>
  );
  if (href) {
    return (
      <Link href={href} className={cn("group flex min-w-0 flex-col gap-1 rounded-lg hover:[&>span:nth-child(2)]:underline", className)}>
        {body}
      </Link>
    );
  }
  return <div className={cn("flex min-w-0 flex-col gap-1", className)}>{body}</div>;
}

const COLS: Record<2 | 3 | 4, string> = {
  2: "grid-cols-2",
  3: "grid-cols-2 sm:grid-cols-3",
  4: "grid-cols-2 sm:grid-cols-4",
};

export function StatGrid({ children, columns = 4, className, label }: { children: ReactNode; columns?: 2 | 3 | 4; className?: string; label?: string }) {
  return (
    <section aria-label={label} data-slot="card" className={cn("grid gap-x-6 gap-y-5 rounded-xl border bg-card px-6 py-5", COLS[columns], className)}>
      {children}
    </section>
  );
}
