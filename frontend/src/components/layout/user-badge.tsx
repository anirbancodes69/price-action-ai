import { initials, cn } from "@/lib/utils";

export function Avatar({ name, className }: { name: string; className?: string }) {
  return (
    <span
      className={cn(
        "flex size-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent to-info text-2xs font-semibold text-white",
        className,
      )}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}
