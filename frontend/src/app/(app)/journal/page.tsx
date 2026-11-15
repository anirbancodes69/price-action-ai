import type { Metadata } from "next";
import { data } from "@/lib/data";
import { JournalView } from "@/features/journal/journal-view";

export const metadata: Metadata = { title: "Trading Journal" };

export default async function JournalPage() {
  const entries = await data.getJournal();
  return <JournalView initial={entries} asOf={data.asOf} />;
}
