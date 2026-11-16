"use client";

import { Check, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { Dropdown } from "@/components/ui/dropdown";
import { useToast } from "@/components/ui/toast";
import { buttonClasses } from "@/components/ui/button";
import { useWatchlists } from "./watchlist-store";

/** "Add to watchlist" control — picks one or more lists for a symbol. */
export function WatchlistToggle({ symbol, size = "md" }: { symbol: string; size?: "sm" | "md" }) {
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
          className={buttonClasses("outline", size)}
        >
          <Star className={cn(watched && "fill-current")} aria-hidden />
          {watched ? `In ${inLists.length} watchlist${inLists.length > 1 ? "s" : ""}` : "Add to watchlist"}
        </button>
      )}
      header={<p className="border-b px-3 py-2 text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Watchlists</p>}
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
              className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm text-foreground hover:bg-accent focus:bg-accent focus-visible:outline-offset-0"
            >
              <span className={cn("flex size-4 items-center justify-center rounded-sm border", has ? "border-primary bg-primary text-primary-foreground" : "border-input")} aria-hidden>
                {has && <Check className="size-3" />}
              </span>
              <span className="flex-1 truncate">{l.name}</span>
              <span className="text-xs tabular-nums text-muted-foreground">{l.symbols.length}</span>
            </button>
          );
        })}
      </div>
    </Dropdown>
  );
}
