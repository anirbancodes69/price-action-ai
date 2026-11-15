"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_GROUPS, isNavActive } from "@/lib/navigation";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/tooltip";

/** Navigation list shared by the desktop sidebar and the mobile drawer. */
export function SidebarNav({ collapsed = false, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Primary" className="flex flex-col gap-5">
      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="flex flex-col gap-0.5">
          {collapsed ? (
            <div className="mx-auto mb-1 h-px w-5 bg-border" aria-hidden />
          ) : (
            <p className="mb-1 px-2.5 text-2xs font-medium uppercase tracking-wider text-fg-subtle">{group.label}</p>
          )}
          {group.items.map((item) => {
            const active = isNavActive(item, pathname);
            const Icon = item.icon;
            return (
              <Tooltip key={item.href} content={item.label} side="right" enabled={collapsed} anchorClassName="flex w-full">
                <Link
                  href={item.href}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  aria-label={collapsed ? item.label : undefined}
                  className={cn(
                    "group relative flex h-8 w-full items-center gap-2.5 rounded text-[13px] font-medium transition-colors",
                    collapsed ? "justify-center px-0" : "px-2.5",
                    active ? "bg-accent/12 text-fg" : "text-fg-muted hover:bg-hover hover:text-fg",
                  )}
                >
                  {active && <span className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-accent" aria-hidden />}
                  <Icon className={cn("size-4 shrink-0", active ? "text-accent" : "text-fg-subtle group-hover:text-fg-muted")} />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
              </Tooltip>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
