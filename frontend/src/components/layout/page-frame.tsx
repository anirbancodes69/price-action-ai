import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Every top-level page renders through one PageFrame (design-standards §2):
 * one gutter, one vertical rhythm (`gap-6` between sections), one title size.
 */
export function PageFrame({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("@container flex min-w-0 flex-col gap-6 px-6 py-6 sm:px-10 lg:px-12", className)}>{children}</div>;
}

interface PageHeaderProps {
  /** One to three words saying what the page is. */
  title: ReactNode;
  /** Optional: one sentence on what the reader can do here. */
  description?: ReactNode;
  /** At most one primary (filled) action; the rest are outline buttons or a menu. */
  actions?: ReactNode;
  /** Small inline items after the title (data-mode badge, signal). */
  meta?: ReactNode;
  className?: string;
}

export function PageHeader({ title, description, actions, meta, className }: PageHeaderProps) {
  return (
    <header className={cn("flex flex-wrap items-end justify-between gap-x-6 gap-y-3", className)}>
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
          <h1 className="font-heading text-2xl leading-tight tracking-tight text-foreground sm:text-3xl">{title}</h1>
          {meta}
        </div>
        {description && <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}
