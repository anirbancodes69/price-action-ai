import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: ReactNode;
  error?: string;
}

/**
 * Native checkbox with a drawn box. The glyph-sized box uses `rounded-sm`,
 * the one radius exception recorded in ENG-02 §11 (a 16px square at the
 * control radius would read as a radio).
 */
export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, error, className, id, ...props },
  ref,
) {
  const autoId = useId();
  const cid = id ?? autoId;
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <label htmlFor={cid} className="inline-flex cursor-pointer items-start gap-2 text-sm text-muted-foreground select-none">
        <span className="relative mt-0.5 flex size-4 shrink-0">
          <input
            ref={ref}
            id={cid}
            type="checkbox"
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? `${cid}-error` : undefined}
            className={cn(
              "peer size-4 shrink-0 cursor-pointer appearance-none rounded-sm border border-input bg-card transition-colors dark:bg-input/30",
              "checked:border-primary checked:bg-primary",
              error && "border-destructive",
            )}
            {...props}
          />
          <Check
            className="pointer-events-none absolute inset-0 m-auto hidden size-3 text-primary-foreground peer-checked:block"
            strokeWidth={3}
            aria-hidden
          />
        </span>
        {label && <span>{label}</span>}
      </label>
      {error && (
        <p id={`${cid}-error`} className="pl-6 text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  );
});
