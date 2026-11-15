import { CircleCheck, Layers, ShieldCheck } from "lucide-react";
import { Brand } from "@/components/layout/brand";

/**
 * Left-hand brand panel for auth screens: an annotated structure diagram
 * (drawn as SVG, no data) and concise product messaging.
 */
export function AuthShowcase() {
  // Stylised swing path: LL → LH → HL (CHoCH) → HH → retest
  const path = "M20 190 L70 140 L105 170 L150 95 L185 130 L235 60 L262 92 L300 40";
  return (
    <div className="relative hidden h-full flex-col justify-between overflow-hidden border-r border-border bg-subtle p-10 lg:flex xl:p-14">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgb(var(--c-accent)/0.16),transparent_55%)]" aria-hidden />
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:linear-gradient(rgb(var(--c-border))_1px,transparent_1px),linear-gradient(90deg,rgb(var(--c-border))_1px,transparent_1px)] [background-size:44px_44px] [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]"
        aria-hidden
      />

      <Brand href="/login" className="relative" />

      <div className="relative max-w-lg">
        <svg viewBox="0 0 320 220" className="mb-10 w-full max-w-md" role="img" aria-label="Illustration of a market structure shift with a breakout and retest">
          <rect x="140" y="82" width="180" height="22" className="fill-bull/10" />
          <line x1="140" x2="320" y1="82" y2="82" className="stroke-bull/50" strokeWidth="1" />
          <line x1="140" x2="320" y1="104" y2="104" className="stroke-bull/50" strokeWidth="1" />
          <line x1="70" x2="150" y1="140" y2="140" className="stroke-warn" strokeDasharray="4 3" />
          <text x="96" y="134" className="fill-warn text-[9px] font-medium">CHoCH</text>
          <path d={path} fill="none" className="stroke-accent" strokeWidth="2.25" strokeLinejoin="round" strokeLinecap="round" />
          {[
            [70, 140, "LH", "bear", -10],
            [105, 170, "HL", "bull", 16],
            [150, 95, "HH", "bull", -10],
            [185, 130, "HL", "bull", 16],
            [235, 60, "HH", "bull", -10],
            [262, 92, "Retest", "warn", 18],
          ].map(([x, y, l, tone, dy]) => (
            <g key={`${x}-${l}`}>
              <circle cx={x as number} cy={y as number} r="3.5" className={tone === "bull" ? "fill-bull" : tone === "bear" ? "fill-bear" : "fill-warn"} />
              <text x={x as number} y={(y as number) + (dy as number)} textAnchor="middle" className={`text-[10px] font-semibold ${tone === "bull" ? "fill-bull" : tone === "bear" ? "fill-bear" : "fill-warn"}`}>
                {l}
              </text>
            </g>
          ))}
        </svg>

        <h2 className="text-2xl font-semibold leading-tight tracking-tight text-fg xl:text-[28px]">
          Read the market the way price writes it.
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-fg-muted">
          Structure, levels, breakouts and retests across NSE stocks, with every setup explained step by step.
          Evidence first, with no black-box signals.
        </p>
        <ul className="mt-8 flex flex-col gap-3 text-[13px] text-fg-muted">
          <li className="flex items-center gap-2.5"><Layers className="size-4 text-accent" aria-hidden /> Market structure, BOS & CHoCH, support and resistance</li>
          <li className="flex items-center gap-2.5"><CircleCheck className="size-4 text-accent" aria-hidden /> Clear states from setup → trigger → plan → position</li>
          <li className="flex items-center gap-2.5"><ShieldCheck className="size-4 text-accent" aria-hidden /> Risk-first trade plans with defined invalidation</li>
        </ul>
      </div>

      <p className="relative text-2xs text-fg-subtle">Decision support for Indian equity traders. Not investment advice.</p>
    </div>
  );
}
