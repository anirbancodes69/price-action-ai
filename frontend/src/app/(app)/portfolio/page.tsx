import type { Metadata } from "next";
import { data } from "@/lib/data";
import { PortfolioView } from "@/features/portfolio/portfolio-view";

export const metadata: Metadata = { title: "Portfolio" };

export default async function PortfolioPage() {
  const [holdings, summary, allocation, orders] = await Promise.all([
    data.getHoldings(),
    data.getPortfolioSummary(),
    data.getAllocation(),
    data.getExecutedOrders(),
  ]);
  return <PortfolioView holdings={holdings} summary={summary} allocation={allocation} orders={orders} asOf={data.asOf} />;
}
