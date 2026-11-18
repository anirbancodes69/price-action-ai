import { AppShell } from "@/components/layout/app-shell";
import { WatchlistProvider } from "@/features/watchlists/watchlist-store";
import { SessionGate } from "@/features/auth/session-gate";
import { data } from "@/lib/data";

export default async function AuthenticatedLayout({ children }: LayoutProps<"/">) {
  const [user, notifications, stocks, watchlists] = await Promise.all([
    data.getCurrentUser(),
    data.getNotifications(),
    data.getStocks(),
    data.getWatchlists(),
  ]);
  return (
    <SessionGate>
    <WatchlistProvider initial={watchlists}>
      <AppShell
        user={user}
        notifications={notifications}
        stocks={stocks.map(({ symbol, name, exchange, sector }) => ({ symbol, name, exchange, sector }))}
      >
        {children}
      </AppShell>
    </WatchlistProvider>
    </SessionGate>
  );
}
