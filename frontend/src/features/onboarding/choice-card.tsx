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
        "group relative flex w-full items-start gap-3 rounded-xl border bg-card px-5 py-4 text-left transition-colors",
        selected ? "border-primary ring-1 ring-primary" : "hover:border-input hover:bg-accent/50",
        disabled && "opacity-70",
      )}
    >
      {Icon && (
        <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-full", selected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground")}>
          <Icon className="size-4" aria-hidden />
        </span>
      )}
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">{choice.label}</span>
          {badge && <span className="rounded-full bg-muted px-2 text-2xs font-medium text-muted-foreground">{badge}</span>}
        </span>
        <span className="block text-sm text-muted-foreground">{choice.description}</span>
      </span>
      <span
        className={cn(
          "mt-0.5 flex size-4 shrink-0 items-center justify-center border transition-colors",
          multi ? "rounded-sm" : "rounded-full",
          selected ? "border-primary bg-primary text-primary-foreground" : "border-input",
        )}
        aria-hidden
      >
        {selected && <Check className="size-3" />}
      </span>
    </button>
  );
}
