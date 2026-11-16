import Link from "next/link";
import { forwardRef, type ComponentProps, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Button variants (design-standards §2, §4): at most one `primary` (filled
 * CTA) per page; everything else is `outline` or `ghost`. Every variant and
 * size shares one radius (`rounded-lg`) so Cancel beside Save reads as a pair.
 */
export type ButtonVariant = "primary" | "outline" | "ghost" | "danger";
export type ButtonSize = "xs" | "sm" | "md" | "lg" | "icon" | "icon-sm";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-cta text-cta-foreground hover:bg-cta-hover",
  outline: "border border-input bg-card text-foreground hover:bg-accent",
  ghost: "text-muted-foreground hover:bg-accent hover:text-foreground",
  danger: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
};

const SIZES: Record<ButtonSize, string> = {
  xs: "h-6 gap-1 px-2 text-xs [&_svg]:size-3.5",
  sm: "h-7 gap-1.5 px-2.5 text-xs [&_svg]:size-3.5",
  md: "h-8 gap-2 px-3 text-sm [&_svg]:size-4",
  lg: "h-10 gap-2 px-4 text-sm [&_svg]:size-4",
  icon: "size-8 [&_svg]:size-4",
  "icon-sm": "size-7 [&_svg]:size-4",
};

export function buttonClasses(variant: ButtonVariant = "outline", size: ButtonSize = "md", className?: string) {
  return cn(
    "inline-flex shrink-0 items-center justify-center whitespace-nowrap rounded-lg font-medium transition-colors",
    "disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50 [&_svg]:shrink-0",
    VARIANTS[variant],
    SIZES[size],
    className,
  );
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant, size, loading, className, children, disabled, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClasses(variant, size, className)}
      {...props}
    >
      {loading && <Loader2 className="animate-spin" aria-hidden />}
      {children}
    </button>
  );
});

export function ButtonLink({
  variant,
  size,
  className,
  ...props
}: ComponentProps<typeof Link> & { variant?: ButtonVariant; size?: ButtonSize }) {
  return <Link className={buttonClasses(variant, size, className)} {...props} />;
}
