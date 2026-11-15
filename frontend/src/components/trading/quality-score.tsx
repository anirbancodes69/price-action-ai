import { cn } from "@/lib/utils";

function toneFor(score: number) {
  if (score >= 75) return { text: "text-bull", stroke: "stroke-bull", bar: "bg-bull" };
  if (score >= 55) return { text: "text-warn", stroke: "stroke-warn", bar: "bg-warn" };
  return { text: "text-bear", stroke: "stroke-bear", bar: "bg-bear" };
}

/** Circular 0–100 score dial. */
export function QualityScoreRing({ score, size = 56, className }: { score: number; size?: number; className?: string }) {
  const r = (size - 6) / 2;
  const c = 2 * Math.PI * r;
  const t = toneFor(score);
  return (
    <div
      className={cn("relative shrink-0", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Price-action quality score ${score} out of 100`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} className="fill-none stroke-hover" strokeWidth={4} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          className={cn("fill-none transition-[stroke-dashoffset] duration-700", t.stroke)}
          strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - score / 100)}
        />
      </svg>
      <span className={cn("tnum absolute inset-0 flex items-center justify-center text-sm font-semibold", t.text)}>{score}</span>
    </div>
  );
}

/** Inline score pill for tables. */
export function QualityScoreBar({ score, className }: { score: number; className?: string }) {
  const t = toneFor(score);
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <span className="h-1 w-10 overflow-hidden rounded-full bg-hover" aria-hidden>
        <span className={cn("block h-full rounded-full", t.bar)} style={{ width: `${score}%` }} />
      </span>
      <span className={cn("tnum text-xs font-medium", t.text)}>{score}</span>
    </span>
  );
}
