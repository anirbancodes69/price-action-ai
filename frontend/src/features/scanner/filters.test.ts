import { describe, expect, it } from "vitest";
import { allDemoSymbols, buildDemoAnalysis } from "@/mocks/demo-analysis";
import type { ScannerRow } from "@/types";
import { activeFilterCount, applyFilters, DEFAULT_FILTERS } from "./filters";

const rows: ScannerRow[] = allDemoSymbols()
  .map((s) => buildDemoAnalysis(s))
  .filter((a): a is NonNullable<typeof a> => a !== null)
  .map((a) => ({
    stock: a.stock,
    structure: a.structure,
    bias: a.bias,
    setupType: a.setup.type,
    direction: a.setup.direction,
    setupStatus: a.setup.status,
    signal: a.setup.signal,
    levels: a.levels,
    qualityScore: a.qualityScore,
  }));

describe("scanner filters", () => {
  it("returns every row with default filters", () => {
    expect(rows.length).toBeGreaterThan(0);
    expect(applyFilters(rows, DEFAULT_FILTERS)).toHaveLength(rows.length);
    expect(activeFilterCount(DEFAULT_FILTERS)).toBe(0);
  });

  it("matches symbol or name case-insensitively", () => {
    const out = applyFilters(rows, { ...DEFAULT_FILTERS, query: "reliance" });
    expect(out.map((r) => r.stock.symbol)).toContain("RELIANCE");
  });

  it("enforces minimum risk/reward", () => {
    const out = applyFilters(rows, { ...DEFAULT_FILTERS, minRR: 2 });
    expect(out.every((r) => r.levels.riskReward >= 2)).toBe(true);
  });

  it("counts active filters excluding the text query", () => {
    expect(activeFilterCount({ ...DEFAULT_FILTERS, query: "x", bias: "bullish", minRR: 2 })).toBe(2);
  });
});
