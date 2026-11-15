import { Briefcase, CalendarRange, Database, GraduationCap, LineChart, Plug, Rocket, Sprout, Target, type LucideIcon } from "lucide-react";

export type StepId = "welcome" | "experience" | "style" | "universe" | "data" | "risk" | "done";

export interface StepDef {
  id: StepId;
  label: string;
  optional?: boolean;
}

export const STEPS: StepDef[] = [
  { id: "welcome", label: "Welcome" },
  { id: "experience", label: "Experience" },
  { id: "style", label: "Trading style" },
  { id: "universe", label: "Market universe", optional: true },
  { id: "data", label: "Data source" },
  { id: "risk", label: "Risk preferences", optional: true },
  { id: "done", label: "Complete" },
];

export interface Choice<T extends string> {
  value: T;
  label: string;
  description: string;
  icon?: LucideIcon;
}

export const EXPERIENCE: Choice<"new" | "intermediate" | "advanced">[] = [
  { value: "new", label: "Getting started", description: "Under 1 year. Learning structure, support and resistance.", icon: Sprout },
  { value: "intermediate", label: "Intermediate", description: "1–3 years. Trade setups with defined stops.", icon: GraduationCap },
  { value: "advanced", label: "Experienced", description: "3+ years. Systematic process and journal.", icon: Briefcase },
];

export const STYLES: Choice<"swing" | "positional" | "breakout" | "pullback">[] = [
  { value: "swing", label: "Swing trading", description: "Hold for days to a few weeks.", icon: LineChart },
  { value: "positional", label: "Positional", description: "Hold for weeks to months.", icon: CalendarRange },
  { value: "breakout", label: "Breakouts & retests", description: "Trade range and level breaks.", icon: Rocket },
  { value: "pullback", label: "Trend pullbacks", description: "Buy dips into support in uptrends.", icon: Target },
];

export const UNIVERSES: Choice<"nifty50" | "nifty100" | "nifty200" | "midcap">[] = [
  { value: "nifty50", label: "NIFTY 50", description: "Large-cap leaders. Highest liquidity." },
  { value: "nifty100", label: "NIFTY 100", description: "Large caps plus NIFTY NEXT 50." },
  { value: "nifty200", label: "NIFTY 200", description: "Adds liquid mid caps." },
  { value: "midcap", label: "NIFTY MIDCAP 150", description: "Mid caps only. Wider swings." },
];

export const DATA_SOURCES: Choice<"demo" | "zerodha">[] = [
  { value: "demo", label: "Demo mode", description: "Explore with built-in sample data. Nothing is live.", icon: Database },
  { value: "zerodha", label: "Zerodha Kite", description: "Connect your broker account for market data. Coming soon.", icon: Plug },
];

