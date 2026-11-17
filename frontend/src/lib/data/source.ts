/**
 * Data-source contract for the frontend.
 *
 * UI code depends only on this interface. Phase 1 ships a mock
 * implementation backed by sample data; later phases add an HTTP
 * implementation that calls the Laravel API (which in turn uses the Python
 * analysis engine) without any change to pages or components.
 */
import type {
  Book,
  RiskToday,
  ActivityItem,
  AllocationSlice,
  BacktestStrategy,
  ExecutedOrder,
  Holding,
  JournalEntry,
  MarketIndex,
  PortfolioSummary,
  ScannerRow,
  Stock,
  StockAnalysis,
  TradePlan,
  TriggerAlert,
  Watchlist,
} from "@/types";
import type { AppNotification, UserProfile } from "@/types";

export interface DashboardSummary {
  stocksScanned: number;
  activeSetups: number;
  awaitingConfirmation: number;
  activeTradePlans: number;
}

export interface DataSource {
  /** "sample" until a real market-data provider is connected. */
  readonly kind: "sample" | "live";
  /** End of the last completed bar the data reflects (ISO timestamp, IST offset). */
  readonly asOf: string;

  getIndices(): Promise<MarketIndex[]>;
  getStocks(): Promise<Stock[]>;
  getScannerRows(): Promise<ScannerRow[]>;
  getAnalysis(symbol: string): Promise<StockAnalysis | null>;
  getAnalysisSymbols(): Promise<string[]>;

  getDashboardSummary(): Promise<DashboardSummary>;
  getActivity(): Promise<ActivityItem[]>;
  getTriggers(): Promise<TriggerAlert[]>;

  getWatchlists(): Promise<Watchlist[]>;
  getTradePlans(): Promise<TradePlan[]>;
  getHoldings(): Promise<Holding[]>;
  getExecutedOrders(): Promise<ExecutedOrder[]>;
  getPortfolioSummary(): Promise<PortfolioSummary>;
  /** Account state of one book for the current session (ARC-04 R2 `GET /risk/today`). */
  getRiskToday(book: Book): Promise<RiskToday>;
  getAllocation(): Promise<AllocationSlice[]>;
  getJournal(): Promise<JournalEntry[]>;
  getBacktestStrategies(): Promise<BacktestStrategy[]>;
  /** Illustrative layout curve only — never a backtest result. */
  getPlaceholderEquityCurve(): Promise<{ time: string; value: number }[]>;

  getCurrentUser(): Promise<UserProfile>;
  getNotifications(): Promise<AppNotification[]>;
}
