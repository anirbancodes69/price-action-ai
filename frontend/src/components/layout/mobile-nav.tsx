"use client";

import { useEffect } from "react";
import { X } from "lucide-react";
import type { UserProfile } from "@/types";
import { Brand } from "./brand";
import { SidebarNav } from "./sidebar-nav";
import { Avatar } from "./user-badge";

/** Slide-in navigation drawer for < lg screens. */
export function MobileNav({ open, onClose, user }: { open: boolean; onClose: () => void; user: UserProfile }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[80] lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
      <div className="absolute inset-0 animate-fade-in bg-overlay" onClick={onClose} aria-hidden />
      <div className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] animate-slide-in-left flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground shadow-float">
        <div className="flex h-14 items-center justify-between border-b border-sidebar-border px-4">
          <Brand />
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" aria-label="Close navigation">
            <X className="size-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-4">
          <SidebarNav onNavigate={onClose} />
        </div>
        <div className="flex items-center gap-2.5 border-t border-sidebar-border p-4">
          <Avatar name={user.name} />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{user.name}</p>
            <p className="truncate text-xs text-muted-foreground">{user.plan}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
