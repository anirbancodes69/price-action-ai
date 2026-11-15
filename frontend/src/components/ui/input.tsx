import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export const inputBase =
  "w-full rounded border border-border bg-subtle text-[13px] text-fg placeholder:text-fg-subtle transition-colors " +
  "hover:border-border-strong focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 " +
  "disabled:cursor-not-allowed disabled:opacity-60";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  leading?: ReactNode;
  trailing?: ReactNode;
  inputSize?: "sm" | "md" | "lg";
}

const SIZE: Record<NonNullable<InputProps["inputSize"]>, string> = {
  sm: "h-7 px-2",
  md: "h-8 px-2.5",
  lg: "h-10 px-3 text-sm",
};

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, hint, error, leading, trailing, inputSize = "md", className, id, ...props },
  ref,
) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {label && (
        <label htmlFor={inputId} className="text-xs font-medium text-fg-muted">
          {label}
        </label>
      )}
      <div className="relative">
        {leading && (
          <span className="pointer-events-none absolute inset-y-0 left-2.5 flex items-center text-fg-subtle [&_svg]:size-4">
            {leading}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(
            inputBase,
            SIZE[inputSize],
            leading ? "pl-8" : undefined,
            trailing ? "pr-9" : undefined,
            error && "border-bear/60 focus:border-bear focus:ring-bear/20",
          )}
          {...props}
        />
        {trailing && <span className="absolute inset-y-0 right-1 flex items-center">{trailing}</span>}
      </div>
      {error ? (
        <p id={`${inputId}-error`} className="text-2xs text-bear">
          {error}
        </p>
      ) : hint ? (
        <p id={`${inputId}-hint`} className="text-2xs text-fg-subtle">
          {hint}
        </p>
      ) : null}
    </div>
  );
});
