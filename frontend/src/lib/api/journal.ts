/**
 * Journal over HTTP: `GET /api/v1/journal` (J1) and `PATCH /api/v1/journal/{id}` (J3) for the owner's closed actual
 * trades. Trade figures come from the backend as-is; only the vocabulary and number formats are converted here.
 */
import type { JournalEntry, TradeOutcome } from "@/types";
import { apiRequest } from "./client";
import { SETUP_TYPE, num } from "./scanner";

export interface ApiJournalEntry {
  id: string;
  kind: "PAPER" | "ACTUAL";
  status: "DRAFT" | "COMPLETE";
  trade: {
    symbol: string;
    setup_type: string | null;
    direction: "LONG" | "SHORT";
    entry_at: string;
    exit_at: string | null;
    entry_price: string;
    exit_price: string | null;
    quantity: number;
    net_pnl: string | null;
    r_multiple: string | null;
    outcome: "WIN" | "LOSS" | "BREAKEVEN" | null;
  };
  followed_plan: boolean | null;
  notes: string | null;
  tags: string[];
}

const OUTCOME: Record<string, TradeOutcome> = { WIN: "win", LOSS: "loss", BREAKEVEN: "breakeven" };

export function mapJournalEntry(e: ApiJournalEntry): JournalEntry {
  const t = e.trade;
  return {
    id: e.id,
    symbol: t.symbol,
    setupType: t.setup_type ? (SETUP_TYPE[t.setup_type] ?? null) : null,
    direction: t.direction === "LONG" ? "long" : "short",
    entryDate: t.entry_at,
    exitDate: t.exit_at ?? t.entry_at,
    entryPrice: num(t.entry_price),
    exitPrice: num(t.exit_price),
    quantity: t.quantity,
    pnl: num(t.net_pnl),
    rMultiple: t.r_multiple === null ? null : Number(t.r_multiple),
    outcome: t.outcome ? OUTCOME[t.outcome] : "breakeven",
    followedPlan: e.followed_plan,
    notes: e.notes ?? "",
    tags: e.tags,
  };
}

export async function fetchJournal(signal?: AbortSignal): Promise<JournalEntry[]> {
  const res = await apiRequest<ApiJournalEntry[]>("/api/v1/journal?kind=ACTUAL&limit=100", { signal });
  return res.data.map(mapJournalEntry);
}

export async function saveJournalNotes(id: string, notes: string): Promise<void> {
  await apiRequest(`/api/v1/journal/${encodeURIComponent(id)}`, { method: "PATCH", body: { notes } });
}
