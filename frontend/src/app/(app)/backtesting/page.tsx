import type { Metadata } from "next";
import { data } from "@/lib/data";
import { BacktestingView } from "@/features/backtesting/backtesting-view";

export const metadata: Metadata = { title: "Backtesting" };

export default async function BacktestingPage() {
  const [strategies, symbols, curve] = await Promise.all([
    data.getBacktestStrategies(),
    data.getAnalysisSymbols(),
    data.getPlaceholderEquityCurve(),
  ]);
  return <BacktestingView strategies={strategies} symbols={symbols} placeholderCurve={curve} />;
}
