/**
 * Centralised semantic colour classes (design-standards §6, §11).
 *
 * Components never compose tone classes themselves; they look them up here
 * so Tailwind can see every class statically and the vocabulary stays in
 * one place.
 *
 * - Status tones say how something IS (success, warning, destructive, info,
 *   neutral). They always appear with a word or icon beside them.
 * - Market tones (bull, bear) are the PriceAction domain extension for
 *   price direction. They also always carry a sign, label or shape.
 * - Chart slots tell series apart and are never status colours.
 */

export type StatusTone = "success" | "warning" | "destructive" | "info" | "neutral";
export type MarketTone = "bull" | "bear";
export type Tone = StatusTone | MarketTone;

/** Chip form: `bg-{tone}/10 text-{tone}`. */
export const TONE_CHIP: Record<Tone, string> = {
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  destructive: "bg-destructive/10 text-destructive",
  info: "bg-info/10 text-info",
  neutral: "bg-muted text-muted-foreground",
  bull: "bg-bull/10 text-bull",
  bear: "bg-bear/10 text-bear",
};

/** Text form: `text-{tone}`. */
export const TONE_TEXT: Record<Tone, string> = {
  success: "text-success",
  warning: "text-warning",
  destructive: "text-destructive",
  info: "text-info",
  neutral: "text-muted-foreground",
  bull: "text-bull",
  bear: "text-bear",
};

/** Fill form: `bg-{tone}` (a dot, a bar segment). */
export const TONE_FILL: Record<Tone, string> = {
  success: "bg-success",
  warning: "bg-warning",
  destructive: "bg-destructive",
  info: "bg-info",
  neutral: "bg-muted-foreground",
  bull: "bg-bull",
  bear: "bg-bear",
};

/** Outline form for chips that must read without a fill (e.g. "Reference only"). */
export const TONE_BORDER: Record<Tone, string> = {
  success: "border-success/40",
  warning: "border-warning/40",
  destructive: "border-destructive/40",
  info: "border-info/40",
  neutral: "border-input",
  bull: "border-bull/40",
  bear: "border-bear/40",
};

/** Categorical series, assigned in order and never cycled. */
export const CHART_SLOTS = [
  "bg-chart-1",
  "bg-chart-2",
  "bg-chart-3",
  "bg-chart-4",
  "bg-chart-5",
  "bg-chart-6",
  "bg-chart-7",
  "bg-chart-8",
] as const;

/** One-hue ramp for ordered states; step 4 stands out most. */
export const CHART_STEPS = ["bg-chart-step-1", "bg-chart-step-2", "bg-chart-step-3", "bg-chart-step-4"] as const;

/** "The remainder of a whole" (free capacity, the grouped tail). */
export const CHART_REST = "bg-chart-rest";

/**
 * Colour for the i-th categorical series. Beyond eight series the tail is
 * grouped by the caller into "Other", which takes CHART_REST.
 */
export function chartSlot(index: number): string {
  return CHART_SLOTS[index] ?? CHART_REST;
}

/** Quality-style 0–100 score bands (PAQS display): how good something is, so status tones. */
export function scoreTone(score: number): StatusTone {
  if (score >= 75) return "success";
  if (score >= 55) return "warning";
  return "destructive";
}

/** Risk-to-reward display band. Below 1.5R reads as neutral, not as an error. */
export function rrTone(rr: number): StatusTone {
  if (rr >= 2) return "success";
  if (rr >= 1.5) return "warning";
  return "neutral";
}

/** Direction of a signed number (price change, P&L, R multiple). */
export function signTone(n: number): MarketTone | "neutral" {
  if (n > 0) return "bull";
  if (n < 0) return "bear";
  return "neutral";
}
