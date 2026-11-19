"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  addWatchlistItem,
  createWatchlist,
  deleteWatchlist,
  fetchWatchlists,
  removeWatchlistItem,
  renameWatchlist,
} from "@/lib/api/watchlists";
import type { Watchlist } from "@/types";

/**
 * Watchlist state shared across pages. Seeded from the data source. In `remote` (HTTP) mode it is loaded from the API
 * and every change is applied here first, then sent to the server; a failed change is reported and the server's
 * lists are loaded again. Otherwise changes stay in this session.
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

export function WatchlistProvider({ initial, remote = false, children }: { initial: Watchlist[]; remote?: boolean; children: ReactNode }) {
  const [watchlists, setWatchlists] = useState(initial);
  const toast = useToast();

  const sync = useCallback(async () => {
    try {
      setWatchlists(await fetchWatchlists());
    } catch {
      /* keep what is shown; the session gate handles an expired session */
    }
  }, []);

  useEffect(() => {
    if (!remote) return;
    const first = window.setTimeout(() => void sync(), 0);
    return () => window.clearTimeout(first);
  }, [remote, sync]);

  /** Sends a change to the server (remote mode only); on failure says why and shows the server's lists again. */
  const send = useCallback(
    (call: () => Promise<void>) => {
      if (!remote) return;
      call().catch((e: unknown) => {
        const taken = e instanceof ApiError && e.code === "NAME_TAKEN";
        toast({
          title: taken ? "That name is already used" : "Could not save the watchlist change",
          description: taken ? undefined : "Showing your saved watchlists.",
          tone: "warn",
        });
        void sync();
      });
    },
    [remote, toast, sync],
  );

  const add = useCallback(
    (listId: string, symbol: string) => {
      setWatchlists((ls) => ls.map((l) => (l.id === listId && !l.symbols.includes(symbol) ? { ...l, symbols: [...l.symbols, symbol] } : l)));
      send(() => addWatchlistItem(listId, symbol));
    },
    [send],
  );

  const remove = useCallback(
    (listId: string, symbol: string) => {
      setWatchlists((ls) => ls.map((l) => (l.id === listId ? { ...l, symbols: l.symbols.filter((s) => s !== symbol) } : l)));
      send(() => removeWatchlistItem(listId, symbol));
    },
    [send],
  );

  const create = useCallback(
    (name: string) => {
      const wl: Watchlist = { id: remote ? crypto.randomUUID() : `wl-${Date.now().toString(36)}`, name, symbols: [] };
      setWatchlists((ls) => [...ls, wl]);
      send(() => createWatchlist(wl.id, name));
      return wl;
    },
    [remote, send],
  );

  const rename = useCallback(
    (listId: string, name: string) => {
      setWatchlists((ls) => ls.map((l) => (l.id === listId ? { ...l, name } : l)));
      send(() => renameWatchlist(listId, name));
    },
    [send],
  );

  const removeList = useCallback(
    (listId: string) => {
      setWatchlists((ls) => ls.filter((l) => l.id !== listId));
      send(() => deleteWatchlist(listId));
    },
    [send],
  );

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
