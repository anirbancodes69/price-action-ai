import type { Metadata } from "next";
import { data } from "@/lib/data";
import { USE_HTTP } from "@/lib/api/config";
import { LiveJournal } from "@/features/journal/live-journal";
import { JournalView } from "@/features/journal/journal-view";

export const metadata: Metadata = { title: "Trading Journal" };

export default async function JournalPage() {
  // HTTP mode: the owner's journal, fetched in the browser with the session cookie.
  if (USE_HTTP) return <LiveJournal />;
  const entries = await data.getJournal();
  return <JournalView initial={entries} asOf={data.asOf} />;
}
