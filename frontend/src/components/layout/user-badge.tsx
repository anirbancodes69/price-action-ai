import { initials, cn } from "@/lib/utils";

/** Initials avatar. Neutral fill, `rounded-full` (design-standards §4) — no gradient. */
export function Avatar({ name, className }: { name: string; className?: string }) {
  return (
    <span
      className={cn(
        "flex size-7 shrink-0 items-center justify-center rounded-full bg-secondary text-2xs font-semibold text-secondary-foreground ring-1 ring-border",
        className,
      )}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}
