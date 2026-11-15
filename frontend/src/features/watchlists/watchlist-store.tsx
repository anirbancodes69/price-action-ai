"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { Watchlist } from "@/types";

/**
 * In-session watchlist state shared across pages. Seeded from the data
 * source; mutations are local only in Phase 1 (no persistence API yet).
 */
interface WatchlistStore {
  watchlists: Watchlist[];
  add: (listId: string, symbol: string) => void;
  remove: (listId: string, symbol: string) => void;
  create: (name: string) => Watchlist;
  rename: (listId: string, name: string) => void;
  removeList: (listId: string) => void;
  listsContaining: (symbol: string) => Watchlist[];
}

const Ctx = createContext<WatchlistStore | null>(null);

export function WatchlistProvider({ initial, children }: { initial: Watchlist[]; children: ReactNode }) {
  const [watchlists, setWatchlists] = useState(initial);

  const add = useCallback((listId: string, symbol: string) => {
    setWatchlists((ls) => ls.map((l) => (l.id === listId && !l.symbols.includes(symbol) ? { ...l, symbols: [...l.symbols, symbol] } : l)));
  }, []);

  const remove = useCallback((listId: string, symbol: string) => {
    setWatchlists((ls) => ls.map((l) => (l.id === listId ? { ...l, symbols: l.symbols.filter((s) => s !== symbol) } : l)));
  }, []);

  const create = useCallback((name: string) => {
    const wl: Watchlist = { id: `wl-${Date.now().toString(36)}`, name, symbols: [] };
    setWatchlists((ls) => [...ls, wl]);
    return wl;
  }, []);

  const rename = useCallback((listId: string, name: string) => {
    setWatchlists((ls) => ls.map((l) => (l.id === listId ? { ...l, name } : l)));
  }, []);

  const removeList = useCallback((listId: string) => {
    setWatchlists((ls) => ls.filter((l) => l.id !== listId));
  }, []);

  const value = useMemo<WatchlistStore>(
    () => ({
      watchlists,
      add,
      remove,
      create,
      rename,
      removeList,
      listsContaining: (symbol) => watchlists.filter((l) => l.symbols.includes(symbol)),
    }),
    [watchlists, add, remove, create, rename, removeList],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useWatchlists() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useWatchlists must be used inside <WatchlistProvider>");
  return ctx;
}
