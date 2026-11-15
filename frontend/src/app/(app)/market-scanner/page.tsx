import type { Metadata } from "next";
import { data } from "@/lib/data";
import { ScannerView } from "@/features/scanner/scanner-view";

export const metadata: Metadata = { title: "Market Scanner" };

export default async function MarketScannerPage() {
  const rows = await data.getScannerRows();
  return <ScannerView rows={rows} asOf={data.asOf} />;
}
