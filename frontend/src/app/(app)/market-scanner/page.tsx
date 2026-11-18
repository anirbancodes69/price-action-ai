import type { Metadata } from "next";
import { data } from "@/lib/data";
import { USE_HTTP } from "@/lib/api/config";
import { LiveScanner } from "@/features/scanner/live-scanner";
import { ScannerView } from "@/features/scanner/scanner-view";

export const metadata: Metadata = { title: "Market Scanner" };

export default async function MarketScannerPage() {
  // HTTP mode: the scan is fetched in the browser with the session cookie and refreshed while the tab is visible.
  if (USE_HTTP) return <LiveScanner />;
  const rows = await data.getScannerRows();
  return <ScannerView rows={rows} asOf={data.asOf} />;
}
