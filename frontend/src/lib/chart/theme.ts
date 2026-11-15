/**
 * Reads design tokens at runtime so canvas-rendered charts use the same
 * palette as the rest of the UI and follow theme switches.
 */

export type TokenName =
  | "base" | "surface" | "subtle" | "border" | "border-strong" | "fg" | "fg-muted" | "fg-subtle"
  | "bull" | "bear" | "accent" | "warn" | "info" | "neutral" | "chart-grid" | "chart-crosshair";

const FALLBACK: Record<TokenName, string> = {
  base: "11 17 32",
  surface: "21 30 47",
  subtle: "17 24 39",
  border: "35 46 66",
  "border-strong": "51 65 89",
  fg: "241 245 249",
  "fg-muted": "148 163 184",
  "fg-subtle": "100 116 139",
  bull: "34 197 94",
  bear: "239 68 68",
  accent: "99 102 241",
  warn: "245 158 11",
  info: "56 189 248",
  neutral: "100 116 139",
  "chart-grid": "30 41 59",
  "chart-crosshair": "100 116 139",
};

export function readToken(name: TokenName): [number, number, number] {
  let raw = FALLBACK[name];
  if (typeof window !== "undefined") {
    const v = getComputedStyle(document.documentElement).getPropertyValue(`--c-${name}`).trim();
    if (v) raw = v;
  }
  const [r, g, b] = raw.split(/\s+/).map(Number);
  return [r, g, b];
}

export function rgba(name: TokenName, alpha = 1) {
  const [r, g, b] = readToken(name);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export interface ChartPalette {
  background: string;
  text: string;
  textMuted: string;
  grid: string;
  border: string;
  crosshair: string;
  bull: string;
  bear: string;
  bullVolume: string;
  bearVolume: string;
  accent: string;
  warn: string;
  info: string;
  supportFill: string;
  supportLine: string;
  resistanceFill: string;
  resistanceLine: string;
  labelBg: string;
}

export function chartPalette(): ChartPalette {
  return {
    background: rgba("surface"),
    text: rgba("fg-muted"),
    textMuted: rgba("fg-subtle"),
    grid: rgba("chart-grid", 0.55),
    border: rgba("border"),
    crosshair: rgba("chart-crosshair", 0.8),
    bull: rgba("bull"),
    bear: rgba("bear"),
    bullVolume: rgba("bull", 0.28),
    bearVolume: rgba("bear", 0.28),
    accent: rgba("accent"),
    warn: rgba("warn"),
    info: rgba("info"),
    supportFill: rgba("bull", 0.08),
    supportLine: rgba("bull", 0.45),
    resistanceFill: rgba("bear", 0.08),
    resistanceLine: rgba("bear", 0.45),
    labelBg: rgba("base", 0.85),
  };
}

/** Subscribe to <html data-theme> changes. */
export function onThemeChange(cb: () => void) {
  const obs = new MutationObserver(cb);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => obs.disconnect();
}
