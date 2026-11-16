import { forwardRef, useId, type SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { CONTROL_HEIGHT, FieldLabel, controlBase } from "./input";

export interface SelectOption<T extends string = string> {
  value: T;
  label: string;
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "children"> {
  label?: string;
  options: SelectOption[];
  selectSize?: keyof typeof CONTROL_HEIGHT;
  /**
   * `full` fills its form column; `auto` sizes to its content, which is what
   * a select in a toolbar must do (design-standards §9).
   */
  width?: "full" | "auto";
}

/** Native select (accessible, mobile-friendly) with design-system styling. */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, options, selectSize = "md", width = "full", className, id, ...props },
  ref,
) {
  const autoId = useId();
  const selectId = id ?? autoId;
  return (
    <div className={cn("flex flex-col gap-1", width === "auto" && "w-auto", className)}>
      {label && <FieldLabel htmlFor={selectId}>{label}</FieldLabel>}
      <div className="relative">
        <select
          ref={ref}
          id={selectId}
          className={cn(
            controlBase,
            "cursor-pointer appearance-none pr-8",
            width === "full" ? "w-full" : "w-auto",
            CONTROL_HEIGHT[selectSize],
            selectSize === "lg" ? "pl-3" : "pl-2.5",
            selectSize === "sm" && "text-xs",
          )}
          {...props}
        >
          {options.map((o) => (
            <option key={o.value} value={o.value} className="bg-popover text-popover-foreground">
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden />
      </div>
    </div>
  );
});
