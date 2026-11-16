"use client";

import { useEffect, useRef } from "react";
import { AreaSeries, ColorType, createChart, LineStyle, type Time } from "lightweight-charts";
import { chartPalette, onThemeChange } from "@/lib/chart/theme";
import { cn } from "@/lib/utils";

interface EquityChartProps {
  points: { time: string; value: number }[];
  className?: string;
}

/** Area chart for equity curves (sample placeholder in Phase 1). */
export function EquityChart({ points, className }: EquityChartProps) {
  const el = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!el.current) return;
    const p = chartPalette();
    const chart = createChart(el.current, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: p.background }, textColor: p.text, fontSize: 11, attributionLogo: false },
      grid: { vertLines: { visible: false }, horzLines: { color: p.grid } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
      crosshair: { vertLine: { style: LineStyle.Dashed, labelBackgroundColor: p.crosshairLabel }, horzLine: { labelBackgroundColor: p.crosshairLabel } },
      handleScroll: false,
      handleScale: false,
    });
    const series = chart.addSeries(AreaSeries, {
      lineColor: p.series,
      topColor: p.seriesTop,
      bottomColor: p.seriesBottom,
      lineWidth: 2,
      priceLineVisible: false,
    });
    series.setData(points.map((x) => ({ time: x.time as Time, value: x.value })));
    chart.timeScale().fitContent();
    const off = onThemeChange(() => {
      const np = chartPalette();
      chart.applyOptions({ layout: { background: { type: ColorType.Solid, color: np.background }, textColor: np.text }, grid: { horzLines: { color: np.grid } } });
      series.applyOptions({ lineColor: np.series, topColor: np.seriesTop, bottomColor: np.seriesBottom });
    });
    return () => {
      off();
      chart.remove();
    };
  }, [points]);

  return <div ref={el} className={cn("h-full w-full", className)} />;
}
