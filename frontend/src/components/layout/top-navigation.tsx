"use client";

import { useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Bell, LogOut, Menu, Monitor, Moon, Settings, Sun, UserRound } from "lucide-react";
import { formatDateTime } from "@/lib/format";
import { breadcrumbFor } from "@/lib/navigation";
import { cn } from "@/lib/utils";
import type { AppNotification, UserProfile } from "@/types";
import { MarketStatus } from "@/components/data/market-status";
import { Dropdown } from "@/components/ui/dropdown";
import { useToast } from "@/components/ui/toast";
import { Breadcrumb } from "./breadcrumb";
import { GlobalSearch, type SearchableStock } from "./global-search";
import { useTheme } from "./theme";
import { Avatar } from "./user-badge";
import { logout } from "@/lib/api/auth";
import { USE_HTTP } from "@/lib/api/config";

interface TopNavigationProps {
  user: UserProfile;
  notifications: AppNotification[];
  stocks: SearchableStock[];
  onOpenMobileNav: () => void;
}

const iconButton = "relative rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground";

export function TopNavigation({ user, notifications, stocks, onOpenMobileNav }: TopNavigationProps) {
  const pathname = usePathname();
  const crumbs = useMemo(() => breadcrumbFor(pathname), [pathname]);

  return (
    <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center gap-3 border-b bg-background/90 px-4 backdrop-blur-md sm:px-6 lg:px-8">
      <button type="button" onClick={onOpenMobileNav} className={cn(iconButton, "-ml-1 lg:hidden")} aria-label="Open navigation">
        <Menu className="size-5" />
      </button>

      <Breadcrumb items={crumbs} className="mr-auto md:mr-0 md:w-56 md:shrink-0 xl:w-72" />

      <div className="flex flex-1 justify-center">
        <GlobalSearch stocks={stocks} />
      </div>

      <div className="flex items-center gap-1 sm:gap-2">
        <MarketStatus className="hidden sm:inline-flex" />
        <NotificationsMenu initial={notifications} />
        <UserMenu user={user} />
      </div>
    </header>
  );
}

function NotificationsMenu({ initial }: { initial: AppNotification[] }) {
  const [items, setItems] = useState(initial);
  const unread = items.filter((n) => n.unread).length;
  return (
    <Dropdown
      width="w-80"
      trigger={({ open, toggle, id }) => (
        <button
          type="button"
          onClick={toggle}
          aria-haspopup="menu"
          aria-expanded={open}
          aria-controls={open ? id : undefined}
          aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
          className={cn(iconButton, open && "bg-accent text-foreground")}
        >
          <Bell className="size-[18px]" />
          {unread > 0 && <span className="absolute right-1 top-1 flex size-2 rounded-full bg-info ring-2 ring-background" aria-hidden />}
        </button>
      )}
      header={
        <div className="flex items-center justify-between border-b px-3 py-2">
          <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Notifications{unread > 0 && <span className="ml-1 normal-case tracking-normal">· {unread} unread</span>}
          </p>
          <button
            type="button"
            role="menuitem"
            onClick={() => setItems((xs) => xs.map((x) => ({ ...x, unread: false })))}
            disabled={unread === 0}
            className="rounded-lg text-xs font-medium text-foreground underline-offset-4 hover:underline disabled:text-muted-foreground disabled:no-underline"
          >
            Mark all read
          </button>
        </div>
      }
    >
      <ul className="max-h-80 overflow-y-auto">
        {items.map((n) => (
          <li key={n.id} className="flex gap-2.5 border-b px-3 py-2.5 last:border-0">
            <span className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", n.unread ? "bg-info" : "bg-transparent")} aria-hidden />
            <div className="flex min-w-0 flex-col gap-1">
              <p className={cn("text-sm text-foreground", n.unread && "font-medium")}>
                {n.title}
                {n.unread && <span className="sr-only"> (unread)</span>}
              </p>
              <p className="text-xs text-muted-foreground">{n.detail}</p>
              <p className="text-xs text-muted-foreground">{formatDateTime(n.at)}</p>
            </div>
          </li>
        ))}
      </ul>
      <p className="border-t px-3 py-2 text-xs text-muted-foreground">Sample notifications — alerts are not connected yet.</p>
    </Dropdown>
  );
}

function UserMenu({ user }: { user: UserProfile }) {
  const router = useRouter();
  const toast = useToast();
  const [theme, setTheme] = useTheme();
  return (
    <Dropdown
      trigger={({ open, toggle, id }) => (
        <button
          type="button"
          onClick={toggle}
          aria-haspopup="menu"
          aria-expanded={open}
          aria-controls={open ? id : undefined}
          aria-label="Account menu"
          className={cn("flex items-center rounded-full p-0.5 hover:bg-accent", open && "bg-accent")}
        >
          <Avatar name={user.name} />
        </button>
      )}
      header={
        <div className="flex flex-col gap-1 border-b px-3 py-2.5">
          <p className="text-sm font-medium text-foreground">{user.name}</p>
          <p className="text-xs text-muted-foreground">{user.email}</p>
        </div>
      }
      items={[
        { label: "Profile", icon: UserRound, onSelect: () => router.push("/settings") },
        { label: "Settings", icon: Settings, onSelect: () => router.push("/settings") },
        "separator",
        { label: "Light theme", icon: Sun, checked: theme === "light", onSelect: () => setTheme("light") },
        { label: "Dark theme", icon: Moon, checked: theme === "dark", onSelect: () => setTheme("dark") },
        { label: "Match system", icon: Monitor, checked: theme === "system", onSelect: () => setTheme("system") },
        "separator",
        {
          label: "Sign out",
          icon: LogOut,
          tone: "danger",
          onSelect: () => {
            if (!USE_HTTP) {
              toast({ title: "Signed out of demo workspace", tone: "info" });
              router.push("/login");
              return;
            }
            // The session is ended server-side; go to sign in even if the request fails (the cookie expires anyway).
            void logout().finally(() => router.push("/login"));
          },
        },
      ]}
    />
  );
}
