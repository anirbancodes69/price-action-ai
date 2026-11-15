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
        "sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-border bg-subtle transition-[width] duration-200 lg:flex",
        collapsed ? "w-[60px]" : "w-60",
      )}
    >
      <div className={cn("flex h-14 items-center border-b border-border", collapsed ? "justify-center px-0" : "justify-between px-4")}>
        <Brand collapsed={collapsed} />
        {!collapsed && (
          <button
            type="button"
            onClick={onToggle}
            className="rounded p-1 text-fg-subtle hover:bg-hover hover:text-fg"
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
              className="rounded p-1.5 text-fg-subtle hover:bg-hover hover:text-fg"
              aria-label="Expand sidebar"
            >
              <PanelLeftOpen className="size-4" />
            </button>
          </Tooltip>
        </div>
      )}

      <div className={cn("border-t border-border", collapsed ? "p-2" : "p-3")}>
        <Tooltip content={`${user.name} · ${user.plan}`} side="right" enabled={collapsed} anchorClassName="flex w-full">
          <Link
            href="/settings"
            className={cn(
              "flex w-full items-center gap-2.5 rounded p-1.5 transition-colors hover:bg-hover",
              collapsed && "justify-center",
            )}
            aria-label={collapsed ? `${user.name} — settings` : undefined}
          >
            <Avatar name={user.name} />
            {!collapsed && (
              <span className="min-w-0 text-left">
                <span className="block truncate text-[13px] font-medium text-fg">{user.name}</span>
                <span className="block truncate text-2xs text-fg-subtle">{user.plan}</span>
              </span>
            )}
          </Link>
        </Tooltip>
      </div>
    </aside>
  );
}
