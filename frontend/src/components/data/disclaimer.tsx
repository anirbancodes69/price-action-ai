import { ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";

export function Disclaimer({ className, children }: { className?: string; children?: React.ReactNode }) {
  return (
    <p className={cn("flex items-start gap-2 text-2xs leading-relaxed text-fg-subtle", className)}>
      <ShieldAlert className="mt-px size-3.5 shrink-0" aria-hidden />
      <span>
        {children ??
          "Analysis is decision support based on price action, not financial advice or a recommendation to buy or sell. Setups can fail. Always apply your own judgement and risk management."}
      </span>
    </p>
  );
}
