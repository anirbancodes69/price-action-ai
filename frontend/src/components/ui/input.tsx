import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Shared control surface for inputs, selects and textareas (design-standards §4: every control is `rounded-lg`). */
export const controlBase =
  "rounded-lg border border-input bg-card text-sm text-foreground placeholder:text-muted-foreground transition-colors " +
  "hover:border-muted-foreground dark:bg-input/30 " +
  "disabled:cursor-not-allowed disabled:opacity-60 " +
  "aria-invalid:border-destructive";

export const CONTROL_HEIGHT = { sm: "h-7", md: "h-8", lg: "h-10" } as const;

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  leading?: ReactNode;
  trailing?: ReactNode;
  inputSize?: keyof typeof CONTROL_HEIGHT;
}

/** Field labels and their hints sit `gap-1` apart (§3). */
export function FieldLabel({ htmlFor, children }: { htmlFor: string; children: ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="text-xs font-medium text-muted-foreground">
      {children}
    </label>
  );
}

export function FieldMessage({ id, error, hint }: { id: string; error?: string; hint?: string }) {
  if (error) {
    return (
      <p id={`${id}-error`} className="text-xs text-destructive">
        {error}
      </p>
    );
  }
  if (hint) {
    return (
      <p id={`${id}-hint`} className="text-xs text-muted-foreground">
        {hint}
      </p>
    );
  }
  return null;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, hint, error, leading, trailing, inputSize = "md", className, id, ...props },
  ref,
) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      {label && <FieldLabel htmlFor={inputId}>{label}</FieldLabel>}
      <div className="relative">
        {leading && (
          <span className="pointer-events-none absolute inset-y-0 left-2.5 flex items-center text-muted-foreground [&_svg]:size-4">
            {leading}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(
            controlBase,
            "w-full",
            CONTROL_HEIGHT[inputSize],
            inputSize === "lg" ? "px-3" : "px-2.5",
            leading ? "pl-8" : undefined,
            trailing ? "pr-9" : undefined,
          )}
          {...props}
        />
        {trailing && <span className="absolute inset-y-0 right-1 flex items-center">{trailing}</span>}
      </div>
      <FieldMessage id={inputId} error={error} hint={hint} />
    </div>
  );
});

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, hint, className, id, ...props },
  ref,
) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      {label && <FieldLabel htmlFor={fieldId}>{label}</FieldLabel>}
      <textarea
        ref={ref}
        id={fieldId}
        aria-describedby={hint ? `${fieldId}-hint` : undefined}
        className={cn(controlBase, "w-full px-3 py-2")}
        {...props}
      />
      <FieldMessage id={fieldId} hint={hint} />
    </div>
  );
});
