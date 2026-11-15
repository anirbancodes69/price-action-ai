import type { Metadata } from "next";
import { data } from "@/lib/data";
import { TradePlansView } from "@/features/trade-plans/trade-plans-view";

export const metadata: Metadata = { title: "Trade Plans" };

export default async function TradePlansPage() {
  const plans = await data.getTradePlans();
  return <TradePlansView initial={plans} asOf={data.asOf} />;
}
