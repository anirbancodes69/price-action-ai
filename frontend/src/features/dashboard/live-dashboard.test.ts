import { describe, expect, it } from "vitest";
import type { ScannerRow } from "@/types";
import { topSetups } from "./live-dashboard";

const row = (symbol: string, over: Partial<ScannerRow>): ScannerRow =>
  ({
    stock: { symbol },
    direction: "long",
    signal: "buy-watch",
    qualityScore: 50,
    ...over,
  }) as ScannerRow;

describe("topSetups", () => {
  it("keeps long rows with a signal, best quality first, at most n", () => {
    const rows = [
      row("A", { qualityScore: 60 }),
      row("B", { qualityScore: 90 }),
      row("C", { signal: "no-trade", qualityScore: 99 }),
      row("D", { direction: "short", qualityScore: 95 }),
      row("E", { qualityScore: 75 }),
    ];
    expect(topSetups(rows).map((r) => r.stock.symbol)).toEqual(["B", "E", "A"]);
    expect(topSetups(rows, 2).map((r) => r.stock.symbol)).toEqual(["B", "E"]);
  });

  it("does not change the input order", () => {
    const rows = [row("A", { qualityScore: 1 }), row("B", { qualityScore: 2 })];
    topSetups(rows);
    expect(rows.map((r) => r.stock.symbol)).toEqual(["A", "B"]);
  });
});
