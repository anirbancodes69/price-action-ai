"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_GROUPS, isNavActive } from "@/lib/navigation";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/tooltip";

/**
 * Navigation list shared by the desktop sidebar and the mobile drawer. The
 * sidebar is the navigation (design-standards §2); the active row takes the
 * CTA pair (§6, §13).
 */
export function SidebarNav({ collapsed = false, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Primary" className="flex flex-col gap-6">
      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="flex flex-col gap-1">
          {collapsed ? (
            <div className="mx-auto h-px w-5 bg-sidebar-border" aria-hidden />
          ) : (
            <p className="px-2.5 text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">{group.label}</p>
          )}
          <ul className="flex flex-col gap-0.5">
            {group.items.map((item) => {
              const active = isNavActive(item, pathname);
              const Icon = item.icon;
              return (
                <li key={item.href}>
                  <Tooltip content={item.label} side="right" enabled={collapsed} anchorClassName="flex w-full">
                    <Link
                      href={item.href}
                      onClick={onNavigate}
                      aria-current={active ? "page" : undefined}
                      aria-label={collapsed ? item.label : undefined}
                      className={cn(
                        "flex h-8 w-full items-center gap-2.5 rounded-lg text-sm transition-colors",
                        collapsed ? "justify-center px-0" : "px-2.5",
                        active
                          ? "bg-sidebar-primary font-medium text-sidebar-primary-foreground"
                          : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                      )}
                    >
                      <Icon className="size-4 shrink-0" aria-hidden />
                      {!collapsed && <span className="truncate">{item.label}</span>}
                    </Link>
                  </Tooltip>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
