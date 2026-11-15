"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * Tiny localStorage-backed store. The server snapshot is always the
 * fallback, so SSR and hydration stay consistent; the stored value is
 * applied immediately after hydration.
 */
const listeners = new Map<string, Set<() => void>>();

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function emit(key: string) {
  listeners.get(key)?.forEach((l) => l());
}

export function usePersistentState<T extends string>(key: string, fallback: T): [T, (v: T) => void] {
  const subscribe = useCallback(
    (cb: () => void) => {
      if (!listeners.has(key)) listeners.set(key, new Set());
      listeners.get(key)!.add(cb);
      const onStorage = (e: StorageEvent) => e.key === key && cb();
      window.addEventListener("storage", onStorage);
      return () => {
        listeners.get(key)?.delete(cb);
        window.removeEventListener("storage", onStorage);
      };
    },
    [key],
  );

  const value = useSyncExternalStore(
    subscribe,
    () => (read(key) as T | null) ?? fallback,
    () => fallback,
  );

  const set = useCallback(
    (v: T) => {
      try {
        window.localStorage.setItem(key, v);
      } catch {
        /* storage unavailable — keep in-memory behaviour */
      }
      emit(key);
    },
    [key],
  );

  return [value, set];
}
