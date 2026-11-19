import type { Metadata } from "next";
import { data } from "@/lib/data";
import { USE_HTTP } from "@/lib/api/config";
import { LiveTradePlans } from "@/features/trade-plans/live-trade-plans";
import { TradePlansView } from "@/features/trade-plans/trade-plans-view";

export const metadata: Metadata = { title: "Trade Plans" };

export default async function TradePlansPage() {
  // HTTP mode: your plans, fetched in the browser with the session cookie.
  if (USE_HTTP) return <LiveTradePlans />;
  const plans = await data.getTradePlans();
  return <TradePlansView initial={plans} asOf={data.asOf} />;
}
