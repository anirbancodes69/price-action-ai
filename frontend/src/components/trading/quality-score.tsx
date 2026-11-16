import { scoreTone, TONE_FILL, TONE_TEXT } from "@/lib/colors";
import { cn } from "@/lib/utils";

const STROKE = { success: "stroke-success", warning: "stroke-warning", destructive: "stroke-destructive" } as const;

/** Circular 0–100 price-action quality dial. The number is always printed beside the colour. */
export function QualityScoreRing({ score, size = 56, className }: { score: number; size?: number; className?: string }) {
  const r = (size - 6) / 2;
  const c = 2 * Math.PI * r;
  const tone = scoreTone(score) as keyof typeof STROKE;
  return (
    <div
      className={cn("relative shrink-0", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Price-action quality score ${score} out of 100`}
    >
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} className="fill-none stroke-muted" strokeWidth={4} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          className={cn("fill-none", STROKE[tone])}
          strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - score / 100)}
        />
      </svg>
      <span className="font-stat absolute inset-0 flex items-center justify-center text-lg leading-none text-foreground">{score}</span>
    </div>
  );
}

/** Inline score meter for tables: bar + number. */
export function QualityScoreBar({ score, className }: { score: number; className?: string }) {
  const tone = scoreTone(score);
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <span className="h-1 w-10 overflow-hidden rounded-full bg-muted" aria-hidden>
        <span className={cn("block h-full rounded-full", TONE_FILL[tone])} style={{ width: `${score}%` }} />
      </span>
      <span className={cn("text-xs font-medium tabular-nums", TONE_TEXT[tone])}>{score}</span>
    </span>
  );
}
