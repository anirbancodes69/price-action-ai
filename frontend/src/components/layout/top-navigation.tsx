"use client";

import { useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Bell, LogOut, Menu, Moon, Settings, Sun, UserRound } from "lucide-react";
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

interface TopNavigationProps {
  user: UserProfile;
  notifications: AppNotification[];
  stocks: SearchableStock[];
  onOpenMobileNav: () => void;
}

export function TopNavigation({ user, notifications, stocks, onOpenMobileNav }: TopNavigationProps) {
  const pathname = usePathname();
  const crumbs = useMemo(() => breadcrumbFor(pathname), [pathname]);

  return (
    <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center gap-3 border-b border-border bg-base/85 px-3 backdrop-blur-md sm:px-4 lg:px-6">
      <button
        type="button"
        onClick={onOpenMobileNav}
        className="-ml-1 rounded p-1.5 text-fg-muted hover:bg-hover hover:text-fg lg:hidden"
        aria-label="Open navigation"
      >
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
          className={cn("relative rounded p-1.5 text-fg-muted hover:bg-hover hover:text-fg", open && "bg-hover text-fg")}
        >
          <Bell className="size-[18px]" />
          {unread > 0 && (
            <span className="absolute right-1 top-1 flex size-2 rounded-full bg-accent ring-2 ring-base" aria-hidden />
          )}
        </button>
      )}
      header={
        <div className="flex items-center justify-between border-b border-border px-3 py-2">
          <p className="text-[13px] font-semibold text-fg">Notifications</p>
          <button
            type="button"
            role="menuitem"
            onClick={() => setItems((xs) => xs.map((x) => ({ ...x, unread: false })))}
            disabled={unread === 0}
            className="text-2xs font-medium text-accent hover:underline disabled:text-fg-subtle disabled:no-underline"
          >
            Mark all read
          </button>
        </div>
      }
    >
      <ul className="max-h-80 overflow-y-auto py-1">
        {items.map((n) => (
          <li key={n.id} className="flex gap-2.5 px-3 py-2.5 hover:bg-hover/60">
            <span className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", n.unread ? "bg-accent" : "bg-transparent")} aria-hidden />
            <div className="min-w-0">
              <p className="text-[13px] text-fg">{n.title}</p>
              <p className="text-xs text-fg-muted">{n.detail}</p>
              <p className="mt-0.5 text-2xs text-fg-subtle">{formatDateTime(n.at)}</p>
            </div>
          </li>
        ))}
      </ul>
      <p className="border-t border-border px-3 py-2 text-2xs text-fg-subtle">Sample notifications — alerts are not connected yet.</p>
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
          className={cn("flex items-center gap-2 rounded p-0.5 hover:bg-hover", open && "bg-hover")}
        >
          <Avatar name={user.name} />
        </button>
      )}
      header={
        <div className="border-b border-border px-3 py-2.5">
          <p className="text-[13px] font-medium text-fg">{user.name}</p>
          <p className="text-2xs text-fg-subtle">{user.email}</p>
        </div>
      }
      items={[
        { label: "Profile", icon: UserRound, onSelect: () => router.push("/settings") },
        { label: "Settings", icon: Settings, onSelect: () => router.push("/settings") },
        {
          label: theme === "dark" ? "Light theme (preview)" : "Dark theme",
          icon: theme === "dark" ? Sun : Moon,
          onSelect: () => setTheme(theme === "dark" ? "light" : "dark"),
        },
        "separator",
        {
          label: "Sign out",
          icon: LogOut,
          tone: "danger",
          onSelect: () => {
            toast({ title: "Signed out of demo workspace", tone: "info" });
            router.push("/login");
          },
        },
      ]}
    />
  );
}
