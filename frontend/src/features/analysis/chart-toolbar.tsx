"use client";

import { Activity, BarChart3, Crosshair, GitCommitHorizontal, Layers, Maximize2, Target, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Timeframe } from "@/types";
import type { ChartOverlays } from "@/components/charts/price-chart";
import { Segmented } from "@/components/ui/segmented";
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

export function ChartToolbar({ timeframe, onTimeframe, overlays, onToggle, onFit }: ChartToolbarProps) {
  return (
    <div className="flex items-center gap-2 border-b border-border px-2 py-1.5 sm:px-3">
      <Segmented
        ariaLabel="Chart timeframe"
        size="xs"
        value={timeframe}
        onChange={onTimeframe}
        options={[
          { value: "1D", label: "1D" },
          { value: "1W", label: "1W" },
          { value: "1M", label: "1M" },
        ]}
      />
      <span className="h-4 w-px bg-border" aria-hidden />
      <div className="no-scrollbar flex min-w-0 flex-1 items-center gap-0.5 overflow-x-auto" role="group" aria-label="Chart overlays">
        {TOGGLES.map((t) => {
          const on = overlays[t.key];
          const Icon = t.icon;
          return (
            <Tooltip key={t.key} content={t.hint} side="bottom">
              <button
                type="button"
                aria-pressed={on}
                onClick={() => onToggle(t.key)}
                className={cn(
                  "inline-flex h-6 shrink-0 items-center gap-1 rounded-sm px-1.5 text-2xs font-medium transition-colors",
                  on ? "bg-accent/12 text-fg" : "text-fg-subtle hover:bg-hover hover:text-fg-muted",
                )}
              >
                <Icon className={cn("size-3.5", on ? "text-accent" : undefined)} aria-hidden />
                <span className="hidden md:inline">{t.label}</span>
              </button>
            </Tooltip>
          );
        })}
      </div>
      <Tooltip content="Fit all data" side="bottom">
        <button type="button" onClick={onFit} className="rounded-sm p-1 text-fg-subtle hover:bg-hover hover:text-fg" aria-label="Fit chart to data">
          <Maximize2 className="size-3.5" />
        </button>
      </Tooltip>
    </div>
  );
}

/** Compact key explaining chart annotations. */
export function ChartLegend() {
  const item = (swatch: React.ReactNode, label: string) => (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      {swatch}
      {label}
    </span>
  );
  return (
    <div className="no-scrollbar flex items-center gap-4 overflow-x-auto border-t border-border px-3 py-2 text-2xs text-fg-subtle">
      {item(<span className="font-semibold text-bull">HH·HL</span>, "Bullish swings")}
      {item(<span className="font-semibold text-bear">LH·LL</span>, "Bearish swings")}
      {item(<span className="h-2.5 w-4 rounded-[2px] border border-bull/50 bg-bull/10" />, "Support zone")}
      {item(<span className="h-2.5 w-4 rounded-[2px] border border-bear/50 bg-bear/10" />, "Resistance zone")}
      {item(<span className="w-4 border-t border-dashed border-bull" />, "BOS")}
      {item(<span className="w-4 border-t border-dashed border-warn" />, "CHoCH")}
      {item(<span className="w-4 border-t border-accent" />, "Entry")}
    </div>
  );
}
