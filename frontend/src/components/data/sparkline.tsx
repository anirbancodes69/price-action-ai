import { cn } from "@/lib/utils";

interface SparklineProps {
  values: number[];
  width?: number;
  height?: number;
  className?: string;
  /** Override tone; defaults to first-vs-last direction. */
  tone?: "bull" | "bear" | "neutral";
}

/** Tiny inline SVG trend line. Purely presentational. */
export function Sparkline({ values, width = 96, height = 28, className, tone }: SparklineProps) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = width / (values.length - 1);
  const pts = values.map((v, i) => [i * step, height - 2 - ((v - min) / span) * (height - 4)] as const);
  const d = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${d} L${width},${height} L0,${height} Z`;
  const t = tone ?? (values[values.length - 1] >= values[0] ? "bull" : "bear");
  const color = t === "bull" ? "text-bull" : t === "bear" ? "text-bear" : "text-fg-subtle";
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      className={cn("overflow-visible", color, className)}
      aria-hidden
      preserveAspectRatio="none"
    >
      <path d={area} fill="currentColor" opacity={0.08} />
      <path d={d} fill="none" stroke="currentColor" strokeWidth={1.25} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
