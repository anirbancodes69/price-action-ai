import Link from "next/link";
import type { HTMLAttributes, ReactNode } from "react";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Surfaces (design-standards §8):
 *
 * - `Panel` is a titled section with a rule under the title. Unboxed by
 *   default (parts of one subject on one page); `boxed` puts it in a card,
 *   which is what side-by-side panels on a comparing page use; `ink` is the
 *   one emphasis card per page (inverse in light, ordinary card in dark).
 * - `Card` is a bordered box for peers in a grid.
 * - `RowList` is a list nested inside a card or boxed panel; it renders as a
 *   muted fill, never a second outline (§7).
 *
 * Panels never nest in cards and cards never nest in panels, except a grid
 * of peer cards inside an unboxed panel.
 */

interface PanelProps {
  title: ReactNode;
  /** One line under the title in muted text. */
  hint?: ReactNode;
  /** Controls at the right of the title row (outline/ghost buttons, a menu). */
  action?: ReactNode;
  /** Small inline items after the title (counts, badges). */
  meta?: ReactNode;
  boxed?: boolean;
  ink?: boolean;
  /** Pinned to the foot, e.g. <PanelLink> to the full list (§10). */
  footer?: ReactNode;
  /** Remove body padding (tables and edge-to-edge content in a boxed panel). */
  flush?: boolean;
  className?: string;
  bodyClassName?: string;
  children?: ReactNode;
  id?: string;
  "aria-label"?: string;
}

export function Panel({
  title,
  hint,
  action,
  meta,
  boxed = false,
  ink = false,
  footer,
  flush = false,
  className,
  bodyClassName,
  children,
  id,
  ...rest
}: PanelProps) {
  const card = boxed || ink;
  return (
    <section
      id={id}
      aria-label={rest["aria-label"]}
      data-slot={card ? "panel-card" : "panel"}
      className={cn(
        "@container flex min-w-0 flex-col",
        card ? "rounded-xl border bg-card text-card-foreground" : "gap-3",
        ink && "border-transparent bg-foreground text-background dark:border-border dark:bg-card dark:text-card-foreground",
        className,
      )}
    >
      <header
        className={cn(
          "flex min-h-12 flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b",
          card ? "px-5 py-2" : "pb-2",
          ink && "border-background/15 dark:border-border",
        )}
      >
        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold uppercase tracking-[0.12em]">{title}</h2>
            {meta}
          </div>
          {hint && <p className={cn("text-xs", ink ? "text-background/70 dark:text-muted-foreground" : "text-muted-foreground")}>{hint}</p>}
        </div>
        {action && <div className="flex shrink-0 flex-wrap items-center gap-2">{action}</div>}
      </header>
      {children !== undefined && (
        <div className={cn("flex min-w-0 flex-1 flex-col gap-3", card && !flush && "px-5 py-4", bodyClassName)}>{children}</div>
      )}
      {footer && <div className={cn("mt-auto flex items-center", card ? "border-t px-5 py-2.5" : "pt-1")}>{footer}</div>}
    </section>
  );
}

/** "View all" style link pinned to a panel foot. */
export function PanelLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="inline-flex items-center gap-1 rounded-lg text-sm font-medium text-foreground hover:underline underline-offset-4">
      {children}
      <ArrowRight className="size-3.5" aria-hidden />
    </Link>
  );
}

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Default card padding `px-5 py-4` (§3). Turn off for edge-to-edge content. */
  padded?: boolean;
  as?: "div" | "article" | "section";
}

export function Card({ padded = true, as: Tag = "div", className, ...props }: CardProps) {
  return (
    <Tag
      data-slot="card"
      className={cn("min-w-0 rounded-xl border bg-card text-card-foreground", padded && "px-5 py-4", className)}
      {...props}
    />
  );
}

/** A list nested in a card: a muted fill with rule-separated rows. */
export function RowList({ className, children, ...props }: HTMLAttributes<HTMLUListElement>) {
  return (
    <ul data-slot="row-list" className={cn("flex flex-col divide-y overflow-hidden rounded-lg border", className)} {...props}>
      {children}
    </ul>
  );
}
