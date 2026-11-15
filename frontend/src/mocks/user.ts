/** SAMPLE DATA — demo user and notifications. */
import type { AppNotification, UserProfile } from "@/types";

export const DEMO_USER: UserProfile = {
  name: "Demo Trader",
  email: "demo@priceaction.ai",
  plan: "Demo workspace",
  tradingStyle: "Swing · Positional",
};

export const NOTIFICATIONS: AppNotification[] = [
  { id: "n1", title: "MARUTI entry trigger met", detail: "Plan TP-1039 is ready for review.", at: "2026-11-13T15:31:00+05:30", unread: true },
  { id: "n2", title: "RELIANCE retest detected", detail: "Breakout zone held on the pullback.", at: "2026-11-13T15:30:00+05:30", unread: true },
  { id: "n3", title: "HCLTECH setup invalidated", detail: "Closed below support before trigger.", at: "2026-11-10T15:30:00+05:30", unread: false },
];
