"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type AutoscaleInfo,
  type CandlestickData,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type SeriesMarker,
  type Time,
} from "lightweight-charts";
import { aggregate, bucketFor } from "@/lib/chart/aggregate";
import { chartPalette, onThemeChange, type ChartPalette } from "@/lib/chart/theme";
import { formatCompact, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Candle, ChartEvent, PriceZone, StructureBreak, SwingPoint, Timeframe, TradeLevels } from "@/types";
import { BreaksPrimitive, ZonesPrimitive, setPrimitiveFont } from "./primitives";

export interface ChartOverlays {
  swings: boolean;
  zones: boolean;
  breaks: boolean;
  events: boolean;
  levels: boolean;
  volume: boolean;
}

export const DEFAULT_OVERLAYS: ChartOverlays = {
  swings: true,
  zones: true,
  breaks: true,
  events: true,
  levels: true,
  volume: true,
};

interface PriceChartProps {
  candles: Candle[];
  timeframe?: Timeframe;
  swings?: SwingPoint[];
  breaks?: StructureBreak[];
  zones?: PriceZone[];
  events?: ChartEvent[];
  levels?: TradeLevels;
  overlays?: ChartOverlays;
  /**
   * Levels are informational (SHORT setup or NO TRADE): drawn long-dashed and
   * titled "(ref)" so they never read as an actionable plan (PRD-07 §7).
   */
  referenceLevels?: boolean;
  /** Increment to trigger fit-to-content from the toolbar. */
  fitSignal?: number;
  className?: string;
}

const toTime = (day: string) => day as Time;

interface Legend {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/**
 * Candlestick chart with price-action overlays. All overlay data comes from
 * props (the analysis contract); this component only renders.
 */
export function PriceChart({
  candles,
  timeframe = "1D",
  swings = [],
  breaks = [],
  zones = [],
  events = [],
  levels,
  overlays = DEFAULT_OVERLAYS,
  referenceLevels = false,
  fitSignal = 0,
  className,
}: PriceChartProps) {
  const container = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const zonesRef = useRef<ZonesPrimitive | null>(null);
  const breaksRef = useRef<BreaksPrimitive | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);
  const [palette, setPalette] = useState<ChartPalette | null>(null);

  const bars = useMemo(() => aggregate(candles, timeframe), [candles, timeframe]);
  const lastBar = bars[bars.length - 1];
  const [legend, setLegend] = useState<Legend | null>(null);
  const shown = legend ?? lastBar;

  // Create chart once.
  useEffect(() => {
    const el = container.current;
    if (!el) return;
    const p = chartPalette();
    const fontFamily = getComputedStyle(document.body).fontFamily;
    setPrimitiveFont(fontFamily);
    const chart = createChart(el, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: p.background },
        textColor: p.text,
        fontFamily,
        fontSize: 11,
        attributionLogo: false,
      },
      grid: { vertLines: { color: p.grid }, horzLines: { color: p.grid } },
      rightPriceScale: { borderColor: p.border, scaleMargins: { top: 0.08, bottom: 0.22 } },
      timeScale: { borderColor: p.border, rightOffset: 8, barSpacing: 7, minBarSpacing: 2 },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: p.crosshair, labelBackgroundColor: p.crosshairLabel, style: LineStyle.Dashed },
        horzLine: { color: p.crosshair, labelBackgroundColor: p.crosshairLabel, style: LineStyle.Dashed },
      },
      localization: { priceFormatter: (v: number) => formatPrice(v) },
    });
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: p.bull,
      downColor: p.bear,
      borderUpColor: p.bull,
      borderDownColor: p.bear,
      wickUpColor: p.bull,
      wickDownColor: p.bear,
      priceLineVisible: true,
      priceLineStyle: LineStyle.Dotted,
    });
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceScaleId: "volume",
      priceFormat: { type: "volume" },
      lastValueVisible: false,
      priceLineVisible: false,
    });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.84, bottom: 0 } });

    const zp = new ZonesPrimitive();
    const bp = new BreaksPrimitive();
    candleSeries.attachPrimitive(zp);
    candleSeries.attachPrimitive(bp);

    chartRef.current = chart;
    candleRef.current = candleSeries;
    volumeRef.current = volumeSeries;
    zonesRef.current = zp;
    breaksRef.current = bp;
    markersRef.current = createSeriesMarkers(candleSeries, []);
    setPalette(p);

    chart.subscribeCrosshairMove((param) => {
      const d = param.seriesData.get(candleSeries) as CandlestickData<Time> | undefined;
      const v = param.seriesData.get(volumeSeries) as { value: number } | undefined;
      if (!param.time || !d) {
        setLegend(null);
        return;
      }
      setLegend({ time: String(param.time), open: d.open, high: d.high, low: d.low, close: d.close, volume: v?.value ?? 0 });
    });

    const offTheme = onThemeChange(() => {
      const np = chartPalette();
      chart.applyOptions({
        layout: { background: { type: ColorType.Solid, color: np.background }, textColor: np.text },
        grid: { vertLines: { color: np.grid }, horzLines: { color: np.grid } },
        rightPriceScale: { borderColor: np.border },
        timeScale: { borderColor: np.border },
        crosshair: {
          vertLine: { color: np.crosshair, labelBackgroundColor: np.crosshairLabel },
          horzLine: { color: np.crosshair, labelBackgroundColor: np.crosshairLabel },
        },
      });
      candleSeries.applyOptions({
        upColor: np.bull, downColor: np.bear, borderUpColor: np.bull, borderDownColor: np.bear, wickUpColor: np.bull, wickDownColor: np.bear,
      });
      setPalette(np);
    });

    return () => {
      offTheme();
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      volumeRef.current = null;
      markersRef.current = null;
      zonesRef.current = null;
      breaksRef.current = null;
      priceLinesRef.current = [];
    };
  }, []);

  // Data + overlays.
  useEffect(() => {
    const chart = chartRef.current;
    const cs = candleRef.current;
    const vs = volumeRef.current;
    if (!chart || !cs || !vs || !palette) return;
    const p = palette;
    const bucket = bucketFor(timeframe);
    const t = (day: string) => toTime(bucket(day));

    cs.setData(bars.map((b) => ({ time: toTime(b.time), open: b.open, high: b.high, low: b.low, close: b.close })));
    vs.setData(
      overlays.volume
        ? bars.map((b) => ({ time: toTime(b.time), value: b.volume, color: b.close >= b.open ? p.bullVolume : p.bearVolume }))
        : [],
    );

    // Markers: swings + events (daily only — weekly bars merge swing bars).
    const markers: SeriesMarker<Time>[] = [];
    if (overlays.swings && timeframe === "1D") {
      for (const s of swings) {
        const bullish = s.label === "HH" || s.label === "HL";
        markers.push({
          time: t(s.time),
          position: s.kind === "high" ? "aboveBar" : "belowBar",
          shape: "circle",
          size: 0.4,
          color: bullish ? p.bull : p.bear,
          text: s.label,
        });
      }
    }
    if (overlays.events) {
      for (const e of events) {
        markers.push({
          time: t(e.time),
          position: e.kind === "breakdown" ? "aboveBar" : "belowBar",
          shape: e.kind === "breakout" ? "arrowUp" : e.kind === "breakdown" ? "arrowDown" : "square",
          size: 1,
          color: e.kind === "retest" ? p.retest : p.event,
          text: e.label,
        });
      }
    }
    markers.sort((a, b) => String(a.time).localeCompare(String(b.time)));
    markersRef.current?.setMarkers(markers);

    zonesRef.current?.setData(
      overlays.zones
        ? zones.map((z) => ({
            from: t(z.fromTime),
            low: z.low,
            high: z.high,
            label: `${z.kind === "support" ? "S" : "R"} · ${z.label}`,
            fill: z.kind === "support" ? p.supportFill : p.resistanceFill,
            line: z.kind === "support" ? p.supportLine : p.resistanceLine,
            text: z.kind === "support" ? p.bull : p.bear,
          }))
        : [],
      p.labelBg,
    );

    breaksRef.current?.setData(
      overlays.breaks && timeframe === "1D"
        ? breaks.map((b) => ({
            from: t(b.fromTime),
            to: t(b.toTime),
            level: b.level,
            label: b.kind,
            color: b.kind === "CHoCH" ? p.choch : b.direction === "bullish" ? p.bull : p.bear,
            dash: b.kind === "CHoCH" ? [2, 3] : [5, 3],
          }))
        : [],
      p.labelBg,
    );

    // Keep trade levels inside the visible price range.
    const lv = overlays.levels && levels ? [levels.entry, levels.stopLoss, levels.target] : [];
    cs.applyOptions({
      autoscaleInfoProvider: (original: () => AutoscaleInfo | null) => {
        const res = original();
        if (!res?.priceRange || lv.length === 0) return res;
        return {
          ...res,
          priceRange: {
            minValue: Math.min(res.priceRange.minValue, ...lv),
            maxValue: Math.max(res.priceRange.maxValue, ...lv),
          },
        };
      },
    });

    for (const line of priceLinesRef.current) cs.removePriceLine(line);
    priceLinesRef.current = [];
    if (overlays.levels && levels) {
      // Entry solid, stop dashed, target dotted: distinguishable without colour.
      // Reference-only levels are all long-dashed and titled "(ref)".
      const ref = referenceLevels ? " (ref)" : "";
      const mk = (price: number, color: string, title: string, style: LineStyle) =>
        cs.createPriceLine({
          price,
          color,
          title: `${title}${ref}`,
          lineStyle: referenceLevels ? LineStyle.LargeDashed : style,
          lineWidth: 1,
          axisLabelVisible: true,
        });
      priceLinesRef.current = [
        mk(levels.entry, p.entry, "Entry", LineStyle.Solid),
        mk(levels.stopLoss, p.bear, "Stop", LineStyle.Dashed),
        mk(levels.target, p.bull, "Target", LineStyle.Dotted),
      ];
    }
  }, [bars, timeframe, swings, breaks, zones, events, levels, overlays, palette, referenceLevels]);

  // Show roughly the last 9 months on first render / timeframe change. Waits
  // until the palette is ready (the data effect above sets the series in the
  // same commit), so the range is never applied to an empty series. Keyed on
  // readiness, not the palette itself, so a theme switch keeps the user's pan.
  const ready = palette !== null;
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !ready || bars.length === 0) return;
    // ~6px per daily bar keeps candle bodies (and their colour) readable on phones.
    const width = container.current?.clientWidth ?? 1000;
    const visible = timeframe === "1D" ? Math.min(170, Math.max(45, Math.floor(width / 6))) : bars.length;
    chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, bars.length - visible), to: bars.length + 6 });
  }, [bars.length, timeframe, ready]);

  useEffect(() => {
    if (fitSignal > 0) chartRef.current?.timeScale().fitContent();
  }, [fitSignal]);

  const up = shown ? shown.close >= shown.open : true;

  return (
    <div className={cn("relative h-full w-full", className)}>
      <div ref={container} className="absolute inset-0" />
      {shown && (
        <div
          className="pointer-events-none absolute left-3 top-2 z-10 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg bg-card/80 px-1.5 py-0.5 text-2xs tabular-nums"
          aria-live="off"
        >
          <span className="text-muted-foreground">{shown.time}</span>
          {(["open", "high", "low", "close"] as const).map((k) => (
            <span key={k} className="text-muted-foreground">
              {k[0].toUpperCase()}{" "}
              <span className={up ? "text-bull" : "text-bear"}>{formatPrice(shown[k])}</span>
            </span>
          ))}
          <span className="text-muted-foreground">
            Vol <span className="text-foreground">{formatCompact(shown.volume)}</span>
          </span>
        </div>
      )}
    </div>
  );
}

