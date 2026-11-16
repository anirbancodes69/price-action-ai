"use client";

import type { ReactNode } from "react";
import { Activity, BarChart3, Crosshair, GitCommitHorizontal, Layers, Maximize2, Target, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Timeframe } from "@/types";
import type { ChartOverlays } from "@/components/charts/price-chart";
import { ChoiceGroup } from "@/components/ui/choice-group";
import { Tooltip } from "@/components/ui/tooltip";

const TOGGLES: { key: keyof ChartOverlays; label: string; icon: LucideIcon; hint: string }[] = [
  { key: "swings", label: "Swings", icon: GitCommitHorizontal, hint: "HH / HL / LH / LL swing labels (daily only)" },
  { key: "zones", label: "Zones", icon: Layers, hint: "Support and resistance zones" },
  { key: "breaks", label: "BOS/CHoCH", icon: Activity, hint: "Break of structure and change of character (daily only)" },
  { key: "events", label: "Events", icon: Crosshair, hint: "Breakout, breakdown and retest markers" },
  { key: "levels", label: "Levels", icon: Target, hint: "Entry, stop-loss and target lines" },
  { key: "volume", label: "Volume", icon: BarChart3, hint: "Volume histogram" },
];

interface ChartToolbarProps {
  timeframe: Timeframe;
  onTimeframe: (tf: Timeframe) => void;
  overlays: ChartOverlays;
  onToggle: (key: keyof ChartOverlays) => void;
  onFit: () => void;
}

/** Chart toolbar: one row, every control the same height (design-standards §9). */
export function ChartToolbar({ timeframe, onTimeframe, overlays, onToggle, onFit }: ChartToolbarProps) {
  return (
    <div className="flex items-center gap-3 border-b px-3 py-2 sm:px-4">
      <ChoiceGroup
        ariaLabel="Chart timeframe"
        size="sm"
        value={timeframe}
        onChange={onTimeframe}
        className="flex-nowrap"
        options={[
          { value: "1D", label: "1D" },
          { value: "1W", label: "1W" },
          { value: "1M", label: "1M" },
        ]}
      />
      <span className="h-5 w-px shrink-0 bg-border" aria-hidden />
      <div className="no-scrollbar flex min-w-0 flex-1 items-center gap-1 overflow-x-auto" role="group" aria-label="Chart overlays">
        {TOGGLES.map((t) => {
          const on = overlays[t.key];
          const Icon = t.icon;
          return (
            <Tooltip key={t.key} content={t.hint} side="bottom">
              <button
                type="button"
                aria-pressed={on}
                aria-label={t.label}
                onClick={() => onToggle(t.key)}
                className={cn(
                  "inline-flex h-7 shrink-0 items-center gap-1.5 rounded-lg px-2 text-xs font-medium transition-colors",
                  on ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                )}
              >
                <Icon className="size-3.5" aria-hidden />
                <span className="hidden md:inline">{t.label}</span>
              </button>
            </Tooltip>
          );
        })}
      </div>
      <Tooltip content="Fit all data" side="bottom">
        <button
          type="button"
          onClick={onFit}
          className="inline-flex size-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground"
          aria-label="Fit chart to data"
        >
          <Maximize2 className="size-3.5" />
        </button>
      </Tooltip>
    </div>
  );
}

function Item({ swatch, label }: { swatch: ReactNode; label: string }) {
  return (
    <li className="inline-flex items-center gap-1.5 whitespace-nowrap">
      {swatch}
      {label}
    </li>
  );
}

const line = (cls: string) => <span className={cn("w-5 border-t-2", cls)} aria-hidden />;

/**
 * Key for every chart annotation. Swatches use the same tokens as the
 * canvas, and each object also differs in line style or shape, so nothing
 * relies on colour alone (PRD-07 §7, design-standards §6).
 */
export function ChartLegend({ reference = false }: { reference?: boolean }) {
  return (
    <ul aria-label="Chart legend" className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t px-4 py-2.5 text-xs text-muted-foreground">
      <Item swatch={<span className="font-semibold text-bull">HH·HL</span>} label="Bullish swings" />
      <Item swatch={<span className="font-semibold text-bear">LH·LL</span>} label="Bearish swings" />
      <Item swatch={<span className="h-2.5 w-4 rounded-sm border border-bull/60 bg-bull/10" aria-hidden />} label="Support" />
      <Item swatch={<span className="h-2.5 w-4 rounded-sm border border-bear/60 bg-bear/10" aria-hidden />} label="Resistance" />
      <Item swatch={line("border-dashed border-bull")} label="BOS" />
      <Item swatch={line("border-dotted border-chart-choch")} label="CHoCH" />
      <Item swatch={<span className="text-chart-event" aria-hidden>▲▼</span>} label="Breakout / breakdown" />
      <Item swatch={<span className="size-2 bg-chart-retest" aria-hidden />} label="Retest" />
      <Item swatch={line(reference ? "border-dashed border-chart-entry" : "border-solid border-chart-entry")} label={reference ? "Entry (reference)" : "Entry"} />
      <Item swatch={line("border-dashed border-bear")} label="Stop-loss" />
      <Item swatch={line("border-dotted border-bull")} label="Target" />
    </ul>
  );
}
