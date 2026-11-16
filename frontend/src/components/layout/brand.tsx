import Link from "next/link";
import { cn } from "@/lib/utils";

/** Brand mark: a stylised swing structure (HL → HH) inside a rounded square. */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 28 28" className={cn("size-7 shrink-0", className)} aria-hidden>
      <rect width="28" height="28" rx="7" className="fill-primary" />
      <path
        d="M6 19.5 L11 13 L14.5 16.5 L21.5 8"
        fill="none"
        className="stroke-primary-foreground"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="21.5" cy="8" r="2" className="fill-primary-foreground" />
      <path d="M6 22.5 H22" className="stroke-primary-foreground" strokeOpacity="0.4" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

export function Brand({ collapsed = false, href = "/dashboard", className }: { collapsed?: boolean; href?: string; className?: string }) {
  return (
    <Link href={href} className={cn("flex items-center gap-2.5", className)} aria-label="PriceAction AI home">
      <BrandMark />
      {!collapsed && (
        <span className="whitespace-nowrap font-heading text-base font-semibold tracking-tight text-foreground">
          PriceAction<span className="ml-1 text-primary">AI</span>
        </span>
      )}
    </Link>
  );
}
