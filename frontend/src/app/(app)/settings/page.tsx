import type { Metadata } from "next";
import { data } from "@/lib/data";
import { USE_HTTP } from "@/lib/api/config";
import { LiveSettings } from "@/features/settings/live-settings";
import { SettingsView } from "@/features/settings/settings-view";

export const metadata: Metadata = { title: "Settings" };

export default async function SettingsPage() {
  const user = await data.getCurrentUser();
  // HTTP mode: the risk section is stored on the server; the other sections stay sample data.
  if (USE_HTTP) return <LiveSettings user={user} />;
  return <SettingsView user={user} />;
}
