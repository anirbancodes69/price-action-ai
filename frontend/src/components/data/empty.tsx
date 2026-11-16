import type { ReactNode } from "react";
import { CircleCheck, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * The non-happy "nothing here" state (design-standards §10, §11): an icon,
 * a title naming what is missing, and one sentence on how it gets filled.
 *
 * Say which of three things is true:
 * - `scope`  — out of scope: nothing in the current filter; say where to widen it.
 * - `clear`  — all clear: there is work and nothing is wrong (green tick).
 * - `none`   — nothing recorded yet: name who fills it in, and where.
 * Never report "all clear" over nothing.
 */
interface EmptyProps {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  kind?: "scope" | "clear" | "none";
  /** `compact` for panel bodies; default for full table/page areas. */
  size?: "default" | "compact";
  className?: string;
}

export function Empty({ icon, title, description, action, kind = "none", size = "default", className }: EmptyProps) {
  const Icon = kind === "clear" ? CircleCheck : icon;
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 text-center",
        size === "compact" ? "px-4 py-6" : "px-6 py-12",
        className,
      )}
    >
      {Icon && (
        <span
          className={cn(
            "flex size-10 items-center justify-center rounded-full",
            kind === "clear" ? "bg-success/10 text-success" : "bg-muted text-muted-foreground",
          )}
        >
          <Icon className="size-5" aria-hidden />
        </span>
      )}
      <div className="flex max-w-sm flex-col gap-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}
