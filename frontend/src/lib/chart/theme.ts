/**
 * Reads design tokens at runtime so canvas-rendered charts use the same
 * palette as the rest of the UI and follow theme switches.
 *
 * Tokens are OKLCH. Lightweight Charts parses colour strings itself and
 * does not understand oklch(), so each token is resolved to sRGB by painting
 * it onto a 1×1 canvas and reading the pixel back.
 */

export type TokenName =
  | "background" | "card" | "popover" | "border" | "input" | "foreground" | "muted-foreground"
  | "bull" | "bear" | "chart-1" | "chart-rest" | "chart-entry" | "chart-event" | "chart-choch" | "chart-retest";

/** Dark-theme sRGB fallbacks for server rendering / tests (no DOM). */
const FALLBACK: Record<TokenName, [number, number, number]> = {
  background: [27, 30, 38],
  card: [34, 38, 47],
  popover: [41, 45, 55],
  border: [52, 55, 63],
  input: [62, 65, 73],
  foreground: [236, 238, 242],
  "muted-foreground": [172, 177, 188],
  bull: [76, 199, 120],
  bear: [240, 110, 100],
  "chart-1": [136, 140, 245],
  "chart-rest": [72, 76, 86],
  "chart-entry": [136, 140, 245],
  "chart-event": [136, 140, 245],
  "chart-choch": [86, 196, 210],
  "chart-retest": [232, 98, 160],
};

let probe: CanvasRenderingContext2D | null = null;

function resolve(name: TokenName): [number, number, number] {
  if (typeof window === "undefined") return FALLBACK[name];
  const raw = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();
  if (!raw) return FALLBACK[name];
  if (!probe) {
    const c = document.createElement("canvas");
    c.width = c.height = 1;
    probe = c.getContext("2d", { willReadFrequently: true });
  }
  if (!probe) return FALLBACK[name];
  probe.clearRect(0, 0, 1, 1);
  // Paint over the theme background so translucent tokens (border/input) resolve to what the eye sees.
  const bg = getComputedStyle(document.documentElement).getPropertyValue("--card").trim();
  probe.fillStyle = bg || "#000";
  probe.fillRect(0, 0, 1, 1);
  probe.fillStyle = raw;
  probe.fillRect(0, 0, 1, 1);
  const [r, g, b] = probe.getImageData(0, 0, 1, 1).data;
  return [r, g, b];
}

export function rgba(name: TokenName, alpha = 1) {
  const [r, g, b] = resolve(name);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export interface ChartPalette {
  background: string;
  text: string;
  grid: string;
  border: string;
  crosshair: string;
  crosshairLabel: string;
  bull: string;
  bear: string;
  bullVolume: string;
  bearVolume: string;
  entry: string;
  event: string;
  choch: string;
  retest: string;
  series: string;
  seriesTop: string;
  seriesBottom: string;
  supportFill: string;
  supportLine: string;
  resistanceFill: string;
  resistanceLine: string;
  labelBg: string;
}

export function chartPalette(): ChartPalette {
  return {
    background: rgba("card"),
    text: rgba("muted-foreground"),
    grid: rgba("border", 0.7),
    border: rgba("border"),
    crosshair: rgba("muted-foreground", 0.7),
    crosshairLabel: rgba("foreground"),
    bull: rgba("bull"),
    bear: rgba("bear"),
    bullVolume: rgba("bull", 0.28),
    bearVolume: rgba("bear", 0.28),
    entry: rgba("chart-entry"),
    event: rgba("chart-event"),
    choch: rgba("chart-choch"),
    retest: rgba("chart-retest"),
    series: rgba("chart-1"),
    seriesTop: rgba("chart-1", 0.22),
    seriesBottom: rgba("chart-1", 0.01),
    supportFill: rgba("bull", 0.08),
    supportLine: rgba("bull", 0.5),
    resistanceFill: rgba("bear", 0.08),
    resistanceLine: rgba("bear", 0.5),
    labelBg: rgba("popover", 0.9),
  };
}

/** Subscribe to <html data-theme> changes. */
export function onThemeChange(cb: () => void) {
  const obs = new MutationObserver(cb);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => obs.disconnect();
}
