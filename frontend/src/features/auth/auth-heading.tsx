import type { ReactNode } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

/** Auth and onboarding title block: same type roles as PageHeader (design-standards §5). */
export function AuthHeading({ title, description }: { title: ReactNode; description?: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <h1 className="font-heading text-2xl leading-tight tracking-tight text-foreground sm:text-3xl">{title}</h1>
      {description && <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>}
    </div>
  );
}

/** Inline text link: foreground + underline, never the brand accent as body text (§6). */
export function TextLink({ href, children, className }: { href: string; children: ReactNode; className?: string }) {
  return (
    <Link href={href} className={cn("rounded-lg font-medium text-foreground underline underline-offset-4 hover:no-underline", className)}>
      {children}
    </Link>
  );
}

/** Quiet demo-mode notice: a muted fill with the sample-data wording. */
export function DemoNotice({ children }: { children: ReactNode }) {
  return <p className="rounded-lg bg-muted px-3 py-2.5 text-xs leading-relaxed text-muted-foreground">{children}</p>;
}
