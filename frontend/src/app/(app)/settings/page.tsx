import type { Metadata } from "next";
import { data } from "@/lib/data";
import { SettingsView } from "@/features/settings/settings-view";

export const metadata: Metadata = { title: "Settings" };

export default async function SettingsPage() {
  const user = await data.getCurrentUser();
  return <SettingsView user={user} />;
}
