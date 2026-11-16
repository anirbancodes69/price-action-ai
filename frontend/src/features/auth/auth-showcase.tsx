import { CircleCheck, Layers, ShieldCheck } from "lucide-react";
import { Brand } from "@/components/layout/brand";

/**
 * Left-hand brand panel for auth screens: an annotated structure diagram
 * (drawn as SVG, no data) and concise product messaging. Rail surface, no
 * decorative gradients; the diagram uses the same annotation tokens as the
 * live chart (bull/bear swings, CHoCH, retest, support zone).
 */
export function AuthShowcase() {
  // Stylised swing path: LL → LH → HL (CHoCH) → HH → retest
  const path = "M20 190 L70 140 L105 170 L150 95 L185 130 L235 60 L262 92 L300 40";
  const swings: [number, number, string, "bull" | "bear" | "retest", number][] = [
    [70, 140, "LH", "bear", -10],
    [105, 170, "HL", "bull", 16],
    [150, 95, "HH", "bull", -10],
    [185, 130, "HL", "bull", 16],
    [235, 60, "HH", "bull", -10],
    [262, 92, "Retest", "retest", 18],
  ];
  const fill = { bull: "fill-bull", bear: "fill-bear", retest: "fill-chart-retest" };
  return (
    <div className="hidden h-full flex-col justify-between border-r border-sidebar-border bg-sidebar p-10 text-sidebar-foreground lg:flex xl:p-14">
      <Brand href="/login" />

      <div className="flex max-w-lg flex-col gap-6">
        <svg viewBox="0 0 320 220" className="w-full max-w-md" role="img" aria-label="Illustration of a market structure shift with a change of character, breakout and retest">
          <rect x="140" y="82" width="180" height="22" className="fill-bull/10" />
          <line x1="140" x2="320" y1="82" y2="82" className="stroke-bull/50" strokeWidth="1" />
          <line x1="140" x2="320" y1="104" y2="104" className="stroke-bull/50" strokeWidth="1" />
          <line x1="70" x2="150" y1="140" y2="140" className="stroke-chart-choch" strokeDasharray="2 3" />
          <text x="96" y="134" className="fill-chart-choch text-[9px] font-medium">CHoCH</text>
          <path d={path} fill="none" className="stroke-foreground/70" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
          {swings.map(([x, y, l, tone, dy]) => (
            <g key={`${x}-${l}`}>
              <circle cx={x} cy={y} r="3.5" className={fill[tone]} />
              <text x={x} y={y + dy} textAnchor="middle" className={`text-[10px] font-semibold ${fill[tone]}`}>
                {l}
              </text>
            </g>
          ))}
        </svg>

        <div className="flex flex-col gap-3">
          <h2 className="font-heading text-2xl leading-tight tracking-tight xl:text-3xl">Read the market the way price writes it.</h2>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Structure, levels, breakouts and retests across NSE stocks, with every setup explained step by step. Evidence first, with
            no black-box signals.
          </p>
        </div>
        <ul className="flex flex-col gap-3 text-sm text-muted-foreground">
          <li className="flex items-center gap-3">
            <Layers className="size-4 shrink-0 text-foreground" aria-hidden /> Market structure, BOS & CHoCH, support and resistance
          </li>
          <li className="flex items-center gap-3">
            <CircleCheck className="size-4 shrink-0 text-foreground" aria-hidden /> Clear states from setup → trigger → plan → position
          </li>
          <li className="flex items-center gap-3">
            <ShieldCheck className="size-4 shrink-0 text-foreground" aria-hidden /> Risk-first trade plans with defined invalidation
          </li>
        </ul>
      </div>

      <p className="text-xs text-muted-foreground">Decision support for Indian equity traders. Not investment advice.</p>
    </div>
  );
}
