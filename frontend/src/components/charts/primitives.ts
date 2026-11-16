/**
 * Custom lightweight-charts series primitives for price-action overlays:
 *  - ZonesPrimitive: shaded support/resistance bands extending to the right edge.
 *  - BreaksPrimitive: dashed BOS / CHoCH segments with labels.
 */
import type {
  IChartApi,
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesApi,
  ISeriesPrimitive,
  PrimitivePaneViewZOrder,
  SeriesAttachedParameter,
  SeriesType,
  Time,
} from "lightweight-charts";

type CanvasRenderingTarget2D = Parameters<IPrimitivePaneRenderer["draw"]>[0];

export interface ZoneDraw {
  from: Time;
  low: number;
  high: number;
  label: string;
  fill: string;
  line: string;
  text: string;
}

export interface BreakDraw {
  from: Time;
  to: Time;
  level: number;
  label: string;
  color: string;
  /** Dash pattern: BOS and CHoCH differ in pattern as well as colour. */
  dash?: number[];
}

abstract class BasePrimitive implements ISeriesPrimitive<Time> {
  protected chart: IChartApi | null = null;
  protected series: ISeriesApi<SeriesType> | null = null;
  private requestUpdate: (() => void) | null = null;
  private readonly views: IPrimitivePaneView[];

  constructor(zOrder: PrimitivePaneViewZOrder) {
    const renderer: IPrimitivePaneRenderer = { draw: (t) => this.draw(t) };
    this.views = [{ zOrder: () => zOrder, renderer: () => renderer }];
  }

  attached(p: SeriesAttachedParameter<Time>) {
    this.chart = p.chart as IChartApi;
    this.series = p.series;
    this.requestUpdate = p.requestUpdate;
  }

  detached() {
    this.chart = null;
    this.series = null;
    this.requestUpdate = null;
  }

  paneViews() {
    return this.views;
  }

  protected update() {
    this.requestUpdate?.();
  }

  protected x(time: Time): number | null {
    return this.chart?.timeScale().timeToCoordinate(time) ?? null;
  }

  protected y(price: number): number | null {
    return this.series?.priceToCoordinate(price) ?? null;
  }

  protected abstract draw(target: CanvasRenderingTarget2D): void;
}

let FONT = "500 10px ui-sans-serif, system-ui, sans-serif";

/** Use the page's text face on the canvas (next/font hashes the family name). */
export function setPrimitiveFont(family: string) {
  FONT = `500 10px ${family}`;
}

function label(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, color: string, bg: string) {
  ctx.font = FONT;
  const w = ctx.measureText(text).width + 8;
  ctx.fillStyle = bg;
  ctx.fillRect(x, y - 7, w, 14);
  ctx.fillStyle = color;
  ctx.textBaseline = "middle";
  ctx.fillText(text, x + 4, y);
}

export class ZonesPrimitive extends BasePrimitive {
  private zones: ZoneDraw[] = [];
  private labelBg = "rgba(0,0,0,0.6)";

  constructor() {
    super("bottom");
  }

  setData(zones: ZoneDraw[], labelBg: string) {
    this.zones = zones;
    this.labelBg = labelBg;
    this.update();
  }

  protected draw(target: CanvasRenderingTarget2D) {
    target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
      for (const z of this.zones) {
        const yTop = this.y(z.high);
        const yBot = this.y(z.low);
        if (yTop === null || yBot === null) continue;
        const x0 = Math.max(0, this.x(z.from) ?? 0);
        const w = mediaSize.width - x0;
        if (w <= 0) continue;
        ctx.fillStyle = z.fill;
        ctx.fillRect(x0, yTop, w, yBot - yTop);
        ctx.strokeStyle = z.line;
        ctx.lineWidth = 1;
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(x0, Math.round(yTop) + 0.5);
        ctx.lineTo(mediaSize.width, Math.round(yTop) + 0.5);
        ctx.moveTo(x0, Math.round(yBot) + 0.5);
        ctx.lineTo(mediaSize.width, Math.round(yBot) + 0.5);
        ctx.stroke();
        if (mediaSize.width >= 480) label(ctx, z.label, x0 + 6, yTop + 10, z.text, this.labelBg);
      }
    });
  }
}

export class BreaksPrimitive extends BasePrimitive {
  private breaks: BreakDraw[] = [];
  private labelBg = "rgba(0,0,0,0.6)";

  constructor() {
    super("normal");
  }

  setData(breaks: BreakDraw[], labelBg: string) {
    this.breaks = breaks;
    this.labelBg = labelBg;
    this.update();
  }

  protected draw(target: CanvasRenderingTarget2D) {
    target.useMediaCoordinateSpace(({ context: ctx }) => {
      for (const b of this.breaks) {
        const x1 = this.x(b.from);
        const x2 = this.x(b.to);
        const y = this.y(b.level);
        if (x1 === null || x2 === null || y === null) continue;
        const yy = Math.round(y) + 0.5;
        ctx.strokeStyle = b.color;
        ctx.lineWidth = 1;
        ctx.setLineDash(b.dash ?? [5, 3]);
        ctx.beginPath();
        ctx.moveTo(x1, yy);
        ctx.lineTo(x2, yy);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.font = FONT;
        const tw = ctx.measureText(b.label).width + 8;
        const mid = (x1 + x2) / 2 - tw / 2;
        label(ctx, b.label, mid, yy - 9, b.color, this.labelBg);
      }
    });
  }
}
