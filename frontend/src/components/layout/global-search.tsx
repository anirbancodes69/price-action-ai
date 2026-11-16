"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { CornerDownLeft, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { Dialog } from "@/components/ui/dialog";

export interface SearchableStock {
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
}

function useStockMatches(stocks: SearchableStock[], query: string) {
  return useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return stocks.slice(0, 6);
    return stocks
      .map((s) => {
        const sym = s.symbol.toLowerCase();
        const name = s.name.toLowerCase();
        const score = sym.startsWith(q) ? 0 : sym.includes(q) ? 1 : name.includes(q) ? 2 : -1;
        return { s, score };
      })
      .filter((x) => x.score >= 0)
      .sort((a, b) => a.score - b.score || a.s.symbol.localeCompare(b.s.symbol))
      .slice(0, 8)
      .map((x) => x.s);
  }, [stocks, query]);
}

function SearchResults({
  id,
  results,
  active,
  onPick,
  onHover,
}: {
  id: string;
  results: SearchableStock[];
  active: number;
  onPick: (s: SearchableStock) => void;
  onHover: (i: number) => void;
}) {
  if (results.length === 0) {
    return <p className="px-3 py-6 text-center text-xs text-muted-foreground">No matching NSE symbols in the sample universe.</p>;
  }
  return (
    <ul id={id} role="listbox" className="max-h-80 overflow-y-auto p-1">
      {results.map((s, i) => (
        <li key={s.symbol} role="option" aria-selected={i === active} id={`${id}-${i}`}>
          <button
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => onPick(s)}
            onMouseEnter={() => onHover(i)}
            className={cn(
              "flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left",
              i === active ? "bg-muted" : "hover:bg-accent",
            )}
          >
            <span className="w-24 shrink-0 text-sm font-medium text-foreground">{s.symbol}</span>
            <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">{s.name}</span>
            <span className="hidden text-xs text-muted-foreground sm:inline">{s.sector}</span>
            <span className="text-xs text-muted-foreground">{s.exchange}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Global stock search with keyboard navigation and a ⌘K / Ctrl+K shortcut. */
export function GlobalSearch({ stocks }: { stocks: SearchableStock[] }) {
  const router = useRouter();
  const listId = useId();
  const input = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [active, setActive] = useState(0);
  const results = useStockMatches(stocks, query);

  const pick = useCallback(
    (s: SearchableStock) => {
      setOpen(false);
      setMobileOpen(false);
      setQuery("");
      input.current?.blur();
      router.push(`/analysis/${encodeURIComponent(s.symbol)}`);
    },
    [router],
  );

  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (window.matchMedia("(min-width: 768px)").matches) input.current?.focus();
        else setMobileOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter" && results[active]) {
      e.preventDefault();
      pick(results[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
      input.current?.blur();
    }
  };

  return (
    <>
      {/* Desktop / tablet inline search */}
      <div className="relative hidden w-full max-w-sm md:block">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <input
          ref={input}
          type="search"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-activedescendant={open && results[active] ? `${listId}-${active}` : undefined}
          aria-label="Search NSE stocks"
          placeholder="Search symbol or company…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={onKeyDown}
          className="h-8 w-full rounded-lg border border-input bg-card pl-8 pr-12 text-sm text-foreground placeholder:text-muted-foreground hover:border-muted-foreground dark:bg-input/30 [&::-webkit-search-cancel-button]:hidden"
        />
        <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded-sm border bg-muted px-1.5 font-mono text-2xs font-medium text-muted-foreground">
          ⌘K
        </kbd>
        {open && (
          <div className="absolute left-0 right-0 top-full z-50 mt-1.5 animate-pop-in overflow-hidden rounded-xl border bg-popover text-popover-foreground shadow-float">
            <p className="flex items-center justify-between border-b px-3 py-1.5 text-xs text-muted-foreground">
              <span>{query ? "Matches" : "Popular in sample universe"}</span>
              <span className="flex items-center gap-1">
                <CornerDownLeft className="size-3" aria-hidden /> to open analysis
              </span>
            </p>
            <SearchResults id={listId} results={results} active={active} onPick={pick} onHover={setActive} />
          </div>
        )}
      </div>

      {/* Mobile trigger */}
      <button
        type="button"
        onClick={() => setMobileOpen(true)}
        className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground md:hidden"
        aria-label="Search stocks"
      >
        <Search className="size-[18px]" />
      </button>
      <Dialog open={mobileOpen} onClose={() => setMobileOpen(false)} title="Search stocks">
        <div className="-mx-5 -my-4">
          <div className="border-b px-4 py-3">
            <input
              type="search"
              autoFocus
              aria-label="Search NSE stocks"
              placeholder="Symbol or company…"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setActive(0);
              }}
              onKeyDown={onKeyDown}
              className="h-10 w-full rounded-lg border border-input bg-card px-3 text-sm text-foreground placeholder:text-muted-foreground dark:bg-input/30"
            />
          </div>
          <SearchResults id={`${listId}-m`} results={results} active={active} onPick={pick} onHover={setActive} />
        </div>
      </Dialog>
    </>
  );
}
