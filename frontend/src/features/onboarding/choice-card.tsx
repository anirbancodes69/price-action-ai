import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Choice } from "./options";

interface ChoiceCardProps<T extends string> {
  choice: Choice<T>;
  selected: boolean;
  onSelect: () => void;
  multi?: boolean;
  badge?: string;
  disabled?: boolean;
}

export function ChoiceCard<T extends string>({ choice, selected, onSelect, multi, badge, disabled }: ChoiceCardProps<T>) {
  const Icon = choice.icon;
  return (
    <button
      type="button"
      role={multi ? "checkbox" : "radio"}
      aria-checked={selected}
      aria-disabled={disabled}
      onClick={onSelect}
      className={cn(
        "group relative flex w-full items-start gap-3 rounded-md border p-3.5 text-left transition-colors",
        selected ? "border-accent bg-accent/8 ring-1 ring-accent/40" : "border-border bg-surface hover:border-border-strong hover:bg-hover/40",
        disabled && "opacity-70",
      )}
    >
      {Icon && (
        <span className={cn("flex size-8 shrink-0 items-center justify-center rounded border", selected ? "border-accent/40 bg-accent/15 text-accent" : "border-border bg-subtle text-fg-subtle")}>
          <Icon className="size-4" aria-hidden />
        </span>
      )}
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2">
          <span className="text-[13px] font-medium text-fg">{choice.label}</span>
          {badge && <span className="rounded-sm bg-hover px-1.5 text-[10px] font-medium text-fg-subtle">{badge}</span>}
        </span>
        <span className="mt-0.5 block text-xs text-fg-muted">{choice.description}</span>
      </span>
      <span
        className={cn(
          "mt-0.5 flex size-4 shrink-0 items-center justify-center border transition-colors",
          multi ? "rounded-sm" : "rounded-full",
          selected ? "border-accent bg-accent text-white" : "border-border-strong",
        )}
        aria-hidden
      >
        {selected && <Check className="size-3" />}
      </span>
    </button>
  );
}
