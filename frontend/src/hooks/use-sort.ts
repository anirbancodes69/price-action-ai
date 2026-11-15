"use client";

import { useMemo, useState } from "react";

export type SortDir = "asc" | "desc";

export interface SortState<K extends string> {
  key: K | null;
  dir: SortDir;
}

/**
 * Client-side sorting over a list. `getValue` maps a sort key to a
 * comparable primitive for each row.
 */
export function useSort<T, K extends string>(
  rows: T[],
  getValue: (row: T, key: K) => string | number,
  initial: SortState<K> = { key: null, dir: "desc" },
) {
  const [sort, setSort] = useState<SortState<K>>(initial);

  const sorted = useMemo(() => {
    if (!sort.key) return rows;
    const key = sort.key;
    const mult = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const va = getValue(a, key);
      const vb = getValue(b, key);
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * mult;
      return String(va).localeCompare(String(vb)) * mult;
    });
  }, [rows, sort, getValue]);

  const toggle = (key: K) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "desc" }));

  return { sorted, sort, toggle };
}
