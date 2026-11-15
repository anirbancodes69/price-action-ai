/**
 * MOCK DATA ADAPTER — serves sample data only. Replace with an HTTP adapter
 * once the backend exists. Nothing here represents live market data.
 */
import type { ScannerRow } from "@/types";
import { allDemoSymbols, buildDemoAnalysis } from "@/mocks/demo-analysis";
import { INDICES } from "@/mocks/indices";
import {
  BACKTEST_STRATEGIES,
  EXECUTED_ORDERS,
  JOURNAL,
  SAMPLE_EQUITY_CURVE,
  WATCHLISTS,
  buildActivity,
  buildAllocation,
  buildHoldings,
  buildPortfolioSummary,
  buildTradePlans,
  buildTriggers,
} from "@/mocks/trading";
import { DEMO_USER, NOTIFICATIONS } from "@/mocks/user";
import { SAMPLE_AS_OF } from "@/mocks/universe";
import type { DataSource } from "./source";

function analyses() {
  return allDemoSymbols()
    .map((s) => buildDemoAnalysis(s))
    .filter((a): a is NonNullable<typeof a> => a !== null);
}

function scannerRows(): ScannerRow[] {
  return analyses().map((a) => ({
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
}

export const mockSource: DataSource = {
  kind: "sample",
  asOf: SAMPLE_AS_OF,

  async getIndices() {
    return INDICES;
  },
  async getStocks() {
    return analyses().map((a) => a.stock);
  },
  async getScannerRows() {
    return scannerRows();
  },
  async getAnalysis(symbol) {
    return buildDemoAnalysis(decodeURIComponent(symbol));
  },
  async getAnalysisSymbols() {
    return allDemoSymbols();
  },

  async getDashboardSummary() {
    const rows = scannerRows();
    const plans = buildTradePlans();
    return {
      stocksScanned: rows.length,
      activeSetups: rows.filter((r) => r.direction === "long" && r.setupStatus !== "invalidated" && r.signal !== "no-trade").length,
      awaitingConfirmation: rows.filter((r) => r.setupStatus === "awaiting-confirmation").length,
      activeTradePlans: plans.filter((p) => ["pending", "entry-confirmed", "active"].includes(p.status)).length,
    };
  },
  async getActivity() {
    return buildActivity();
  },
  async getTriggers() {
    return buildTriggers();
  },

  async getWatchlists() {
    return WATCHLISTS;
  },
  async getTradePlans() {
    return buildTradePlans();
  },
  async getHoldings() {
    return buildHoldings();
  },
  async getExecutedOrders() {
    return EXECUTED_ORDERS;
  },
  async getPortfolioSummary() {
    return buildPortfolioSummary(buildHoldings(), JOURNAL);
  },
  async getAllocation() {
    const summary = buildPortfolioSummary(buildHoldings(), JOURNAL);
    return buildAllocation(buildHoldings(), summary.cash);
  },
  async getJournal() {
    return JOURNAL;
  },
  async getBacktestStrategies() {
    return BACKTEST_STRATEGIES;
  },
  async getPlaceholderEquityCurve() {
    return SAMPLE_EQUITY_CURVE;
  },

  async getCurrentUser() {
    return DEMO_USER;
  },
  async getNotifications() {
    return NOTIFICATIONS;
  },
};
