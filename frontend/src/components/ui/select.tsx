import { forwardRef, useId, type SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { inputBase } from "./input";

export interface SelectOption<T extends string = string> {
  value: T;
  label: string;
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "children"> {
  label?: string;
  options: SelectOption[];
  selectSize?: "sm" | "md" | "lg";
}

/** Native select (accessible, mobile-friendly) with design-system styling. */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, options, selectSize = "md", className, id, ...props },
  ref,
) {
  const autoId = useId();
  const selectId = id ?? autoId;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {label && (
        <label htmlFor={selectId} className="text-xs font-medium text-fg-muted">
          {label}
        </label>
      )}
      <div className="relative">
        <select
          ref={ref}
          id={selectId}
          className={cn(
            inputBase,
            "cursor-pointer appearance-none pr-8",
            selectSize === "sm" ? "h-7 pl-2 text-xs" : selectSize === "lg" ? "h-10 pl-3 text-sm" : "h-8 pl-2.5",
          )}
          {...props}
        >
          {options.map((o) => (
            <option key={o.value} value={o.value} className="bg-raised">
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2 top-1/2 size-3.5 -translate-y-1/2 text-fg-subtle" />
      </div>
    </div>
  );
});
