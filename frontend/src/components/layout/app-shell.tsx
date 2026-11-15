"use client";

import { useCallback, useState, type ReactNode } from "react";
import { usePersistentState } from "@/hooks/use-persistent-state";
import type { AppNotification, UserProfile } from "@/types";
import { AppSidebar } from "./app-sidebar";
import type { SearchableStock } from "./global-search";
import { MobileNav } from "./mobile-nav";
import { TopNavigation } from "./top-navigation";

interface AppShellProps {
  children: ReactNode;
  user: UserProfile;
  notifications: AppNotification[];
  stocks: SearchableStock[];
}

/** Authenticated application frame: sidebar + top navigation + content. */
export function AppShell({ children, user, notifications, stocks }: AppShellProps) {
  const [sidebar, setSidebar] = usePersistentState<"expanded" | "collapsed">("pa-sidebar", "expanded");
  const [mobileOpen, setMobileOpen] = useState(false);
  const closeMobile = useCallback(() => setMobileOpen(false), []);

  return (
    <div className="flex min-h-dvh bg-base">
      <AppSidebar
        collapsed={sidebar === "collapsed"}
        onToggle={() => setSidebar(sidebar === "collapsed" ? "expanded" : "collapsed")}
        user={user}
      />
      <MobileNav open={mobileOpen} onClose={closeMobile} user={user} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopNavigation
          user={user}
          notifications={notifications}
          stocks={stocks}
          onOpenMobileNav={() => setMobileOpen(true)}
        />
        <main id="main" className="min-w-0 flex-1">
          {children}
        </main>
      </div>
    </div>
  );
}
