"use client";

import { useId } from "react";
import { cn } from "@/lib/utils";

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  id?: string;
}

/** Toggle (design-standards §4 `rounded-full`; §6: an "on" switch takes the brand accent). */
export function Switch({ checked, onChange, label, description, disabled, id }: SwitchProps) {
  const autoId = useId();
  const sid = id ?? autoId;
  const control = (
    <button
      id={sid}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label ? undefined : "Toggle"}
      aria-labelledby={label ? `${sid}-label` : undefined}
      aria-describedby={description ? `${sid}-desc` : undefined}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        checked ? "border-primary bg-primary" : "border-input bg-muted",
      )}
    >
      <span
        className={cn(
          "inline-block size-3.5 rounded-full shadow-sm transition-transform",
          checked ? "translate-x-[18px] bg-primary-foreground" : "translate-x-[2px] bg-muted-foreground",
        )}
      />
    </button>
  );
  if (!label) return control;
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex min-w-0 flex-col gap-1">
        <p id={`${sid}-label`} className="text-sm text-foreground">
          {label}
        </p>
        {description && (
          <p id={`${sid}-desc`} className="text-xs text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {control}
    </div>
  );
}
