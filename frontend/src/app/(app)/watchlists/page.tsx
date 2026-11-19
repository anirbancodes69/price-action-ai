import type { Metadata } from "next";
import { data } from "@/lib/data";
import { USE_HTTP } from "@/lib/api/config";
import { LiveWatchlists } from "@/features/watchlists/live-watchlists";
import { WatchlistsView } from "@/features/watchlists/watchlists-view";

export const metadata: Metadata = { title: "Watchlists" };

export default async function WatchlistsPage() {
  // HTTP mode: lists from the server, setups from the live scan, both fetched in the browser.
  if (USE_HTTP) return <LiveWatchlists />;
  const rows = await data.getScannerRows();
  return <WatchlistsView rows={rows} asOf={data.asOf} />;
}
