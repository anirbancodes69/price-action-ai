/**
 * Watchlists over HTTP (W1-W6). The list ids are client-generated for new lists, so the local state and the server
 * agree on them without a round trip.
 */
import type { Watchlist } from "@/types";
import { apiRequest } from "./client";

export interface ApiWatchlist {
  id: string;
  name: string;
  sort_order: number;
  items: { symbol: string; added_at: string }[];
}

export const mapWatchlist = (w: ApiWatchlist): Watchlist => ({
  id: w.id,
  name: w.name,
  symbols: w.items.map((i) => i.symbol),
});

export async function fetchWatchlists(
  signal?: AbortSignal,
): Promise<Watchlist[]> {
  const res = await apiRequest<ApiWatchlist[]>("/api/v1/watchlists", {
    signal,
  });
  return res.data.map(mapWatchlist);
}

export async function createWatchlist(id: string, name: string): Promise<void> {
  await apiRequest("/api/v1/watchlists", {
    method: "POST",
    body: { id, name },
  });
}

export async function renameWatchlist(id: string, name: string): Promise<void> {
  await apiRequest(`/api/v1/watchlists/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: { name },
  });
}

export async function deleteWatchlist(id: string): Promise<void> {
  await apiRequest(`/api/v1/watchlists/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export async function addWatchlistItem(
  id: string,
  symbol: string,
): Promise<void> {
  await apiRequest(
    `/api/v1/watchlists/${encodeURIComponent(id)}/items/${encodeURIComponent(symbol)}`,
    { method: "PUT" },
  );
}

export async function removeWatchlistItem(
  id: string,
  symbol: string,
): Promise<void> {
  await apiRequest(
    `/api/v1/watchlists/${encodeURIComponent(id)}/items/${encodeURIComponent(symbol)}`,
    { method: "DELETE" },
  );
}
