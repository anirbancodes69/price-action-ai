import type { Metadata } from "next";
import { data } from "@/lib/data";
import { USE_HTTP } from "@/lib/api/config";
import { LiveTrades } from "@/features/portfolio/live-trades";
import { PortfolioView } from "@/features/portfolio/portfolio-view";

export const metadata: Metadata = { title: "Active trades" };

export default async function PortfolioPage() {
  // HTTP mode: the owner's logged trades, fetched in the browser with the session cookie.
  if (USE_HTTP) return <LiveTrades />;
  const [holdings, summary, allocation, orders] = await Promise.all([
    data.getHoldings(),
    data.getPortfolioSummary(),
    data.getAllocation(),
    data.getExecutedOrders(),
  ]);
  return <PortfolioView holdings={holdings} summary={summary} allocation={allocation} orders={orders} asOf={data.asOf} />;
}
