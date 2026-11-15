import type { Metadata } from "next";
import { data } from "@/lib/data";
import { WatchlistsView } from "@/features/watchlists/watchlists-view";

export const metadata: Metadata = { title: "Watchlists" };

export default async function WatchlistsPage() {
  const rows = await data.getScannerRows();
  return <WatchlistsView rows={rows} asOf={data.asOf} />;
}
