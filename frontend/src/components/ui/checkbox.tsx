import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: ReactNode;
  error?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, error, className, id, ...props },
  ref,
) {
  const autoId = useId();
  const cid = id ?? autoId;
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <label htmlFor={cid} className="inline-flex cursor-pointer items-start gap-2 text-xs text-fg-muted select-none">
        <input
          ref={ref}
          id={cid}
          type="checkbox"
          aria-invalid={error ? true : undefined}
          className={cn(
            "peer mt-px size-3.5 shrink-0 cursor-pointer appearance-none rounded-sm border border-border-strong bg-subtle transition-colors",
            "checked:border-accent checked:bg-accent",
            "checked:bg-[url(\"data:image/svg+xml,%3csvg viewBox='0 0 16 16' fill='white' xmlns='http://www.w3.org/2000/svg'%3e%3cpath d='M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z'/%3e%3c/svg%3e\")] bg-center bg-no-repeat",
            error && "border-bear/70",
          )}
          {...props}
        />
        {label && <span>{label}</span>}
      </label>
      {error && <p className="pl-5.5 text-2xs text-bear">{error}</p>}
    </div>
  );
});
