import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * The single surface primitive. Pages compose Panels side by side rather
 * than nesting cards inside cards.
 */
export function Panel({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={cn("rounded-md border border-border bg-surface", className)} {...props} />;
}

interface PanelHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  icon?: ReactNode;
  className?: string;
}

export function PanelHeader({ title, description, actions, icon, className }: PanelHeaderProps) {
  return (
    <header className={cn("flex min-h-11 items-center justify-between gap-3 border-b border-border px-4 py-2.5", className)}>
      <div className="flex min-w-0 items-center gap-2">
        {icon && <span className="text-fg-subtle [&_svg]:size-4">{icon}</span>}
        <div className="min-w-0">
          <h2 className="truncate text-[13px] font-semibold text-fg">{title}</h2>
          {description && <p className="truncate text-2xs text-fg-subtle">{description}</p>}
        </div>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-1.5">{actions}</div>}
    </header>
  );
}

export function PanelBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-4", className)} {...props} />;
}
