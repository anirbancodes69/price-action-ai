import type { Bias, IndexMembership, MarketStructure, ScannerRow, SetupStatus, SetupType } from "@/types";

export interface ScannerFilters {
  query: string;
  exchange: "all" | "NSE" | "BSE";
  index: "all" | IndexMembership;
  bias: "all" | Bias;
  setup: "all" | SetupType;
  structure: "all" | MarketStructure;
  status: "all" | SetupStatus;
  minRR: number;
}

export const DEFAULT_FILTERS: ScannerFilters = {
  query: "",
  exchange: "all",
  index: "all",
  bias: "all",
  setup: "all",
  structure: "all",
  status: "all",
  minRR: 0,
};

export function applyFilters(rows: ScannerRow[], f: ScannerFilters) {
  const q = f.query.trim().toLowerCase();
  return rows.filter((r) => {
    if (q && !r.stock.symbol.toLowerCase().includes(q) && !r.stock.name.toLowerCase().includes(q)) return false;
    if (f.exchange !== "all" && r.stock.exchange !== f.exchange) return false;
    if (f.index !== "all" && !r.stock.indices.includes(f.index)) return false;
    if (f.bias !== "all" && r.bias !== f.bias) return false;
    if (f.setup !== "all" && r.setupType !== f.setup) return false;
    if (f.structure !== "all" && r.structure !== f.structure) return false;
    if (f.status !== "all" && r.setupStatus !== f.status) return false;
    if (f.minRR > 0 && (r.levels?.riskReward ?? 0) < f.minRR) return false;
    return true;
  });
}

export function activeFilterCount(f: ScannerFilters) {
  return (Object.keys(DEFAULT_FILTERS) as (keyof ScannerFilters)[]).filter(
    (k) => k !== "query" && f[k] !== DEFAULT_FILTERS[k],
  ).length;
}
