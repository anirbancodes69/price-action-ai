"use client";

import { Check, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { Dropdown } from "@/components/ui/dropdown";
import { useToast } from "@/components/ui/toast";
import { buttonClasses } from "@/components/ui/button";
import { useWatchlists } from "./watchlist-store";

/** "Add to watchlist" control — picks one or more lists for a symbol. */
export function WatchlistToggle({ symbol, size = "sm" }: { symbol: string; size?: "sm" | "md" }) {
  const { watchlists, add, remove, listsContaining } = useWatchlists();
  const toast = useToast();
  const inLists = listsContaining(symbol);
  const watched = inLists.length > 0;

  return (
    <Dropdown
      width="w-60"
      trigger={({ open, toggle, id }) => (
        <button
          type="button"
          onClick={toggle}
          aria-haspopup="menu"
          aria-expanded={open}
          aria-controls={open ? id : undefined}
          className={buttonClasses("secondary", size, cn(watched && "border-warn/40 text-warn"))}
        >
          <Star className={cn(watched && "fill-warn")} />
          {watched ? `In ${inLists.length} watchlist${inLists.length > 1 ? "s" : ""}` : "Add to watchlist"}
        </button>
      )}
      header={<p className="border-b border-border px-3 py-2 text-2xs font-medium uppercase tracking-wider text-fg-subtle">Watchlists</p>}
    >
      <div className="p-1">
        {watchlists.map((l) => {
          const has = l.symbols.includes(symbol);
          return (
            <button
              key={l.id}
              type="button"
              role="menuitemcheckbox"
              aria-checked={has}
              onClick={() => {
                if (has) remove(l.id, symbol);
                else add(l.id, symbol);
                toast({ title: has ? `Removed ${symbol} from ${l.name}` : `Added ${symbol} to ${l.name}`, tone: has ? "info" : "success" });
              }}
              className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-[13px] text-fg hover:bg-hover focus:bg-hover focus:outline-none"
            >
              <span className={cn("flex size-4 items-center justify-center rounded-sm border", has ? "border-accent bg-accent text-white" : "border-border-strong")}>
                {has && <Check className="size-3" />}
              </span>
              <span className="flex-1 truncate">{l.name}</span>
              <span className="tnum text-2xs text-fg-subtle">{l.symbols.length}</span>
            </button>
          );
        })}
      </div>
    </Dropdown>
  );
}
