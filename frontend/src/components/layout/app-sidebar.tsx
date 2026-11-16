"use client";

import Link from "next/link";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UserProfile } from "@/types";
import { Tooltip } from "@/components/ui/tooltip";
import { Brand } from "./brand";
import { SidebarNav } from "./sidebar-nav";
import { Avatar } from "./user-badge";

interface AppSidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  user: UserProfile;
}

/** Desktop sidebar (lg+). Mobile uses <MobileNav>. */
export function AppSidebar({ collapsed, onToggle, user }: AppSidebarProps) {
  return (
    <aside
      className={cn(
        "sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200 lg:flex",
        collapsed ? "w-[60px]" : "w-60",
      )}
    >
      <div className={cn("flex h-14 items-center border-b border-sidebar-border", collapsed ? "justify-center px-0" : "justify-between px-4")}>
        <Brand collapsed={collapsed} />
        {!collapsed && (
          <button
            type="button"
            onClick={onToggle}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose className="size-4" />
          </button>
        )}
      </div>

      <div className={cn("flex-1 overflow-y-auto py-4", collapsed ? "px-2" : "px-3")}>
        <SidebarNav collapsed={collapsed} />
      </div>

      {collapsed && (
        <div className="flex justify-center pb-2">
          <Tooltip content="Expand sidebar" side="right">
            <button
              type="button"
              onClick={onToggle}
              className="rounded-lg p-1.5 text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              aria-label="Expand sidebar"
            >
              <PanelLeftOpen className="size-4" />
            </button>
          </Tooltip>
        </div>
      )}

      <div className={cn("border-t border-sidebar-border", collapsed ? "p-2" : "p-3")}>
        <Tooltip content={`${user.name} · ${user.plan}`} side="right" enabled={collapsed} anchorClassName="flex w-full">
          <Link
            href="/settings"
            className={cn(
              "flex w-full items-center gap-2.5 rounded-lg p-1.5 transition-colors hover:bg-sidebar-accent",
              collapsed && "justify-center",
            )}
            aria-label={collapsed ? `${user.name} — settings` : undefined}
          >
            <Avatar name={user.name} />
            {!collapsed && (
              <span className="min-w-0 text-left">
                <span className="block truncate text-sm font-medium">{user.name}</span>
                <span className="block truncate text-xs text-muted-foreground">{user.plan}</span>
              </span>
            )}
          </Link>
        </Tooltip>
      </div>
    </aside>
  );
}
