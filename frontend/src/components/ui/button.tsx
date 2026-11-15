import Link from "next/link";
import { forwardRef, type ComponentProps, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "outline" | "danger" | "bull";
type Size = "xs" | "sm" | "md" | "lg" | "icon" | "icon-sm";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-accent-fg hover:bg-accent-strong shadow-[inset_0_1px_0_rgb(255_255_255/0.12)]",
  secondary: "bg-raised text-fg border border-border hover:bg-hover hover:border-border-strong",
  outline: "border border-border text-fg hover:bg-hover hover:border-border-strong",
  ghost: "text-fg-muted hover:text-fg hover:bg-hover",
  danger: "bg-bear/12 text-bear border border-bear/25 hover:bg-bear/20",
  bull: "bg-bull-strong text-white hover:bg-bull-strong/90",
};

const SIZES: Record<Size, string> = {
  xs: "h-6 px-2 text-2xs gap-1",
  sm: "h-7 px-2.5 text-xs gap-1.5",
  md: "h-8 px-3 text-[13px] gap-2",
  lg: "h-10 px-4 text-sm gap-2",
  icon: "h-8 w-8",
  "icon-sm": "h-7 w-7",
};

export function buttonClasses(variant: Variant = "secondary", size: Size = "md", className?: string) {
  return cn(
    "inline-flex shrink-0 items-center justify-center whitespace-nowrap rounded font-medium transition-colors duration-150",
    "disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
    VARIANTS[variant],
    SIZES[size],
    className,
  );
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
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
}: ComponentProps<typeof Link> & { variant?: Variant; size?: Size }) {
  return <Link className={buttonClasses(variant, size, className)} {...props} />;
}
