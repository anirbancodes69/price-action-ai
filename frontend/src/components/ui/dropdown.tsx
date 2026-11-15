"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DropdownItem {
  label: string;
  icon?: LucideIcon;
  onSelect?: () => void;
  href?: string;
  tone?: "default" | "danger";
  disabled?: boolean;
}

interface DropdownProps {
  /** Render prop receives the open state for styling the trigger. */
  trigger: (props: { open: boolean; toggle: () => void; id: string }) => ReactNode;
  items?: (DropdownItem | "separator")[];
  /** Custom panel content (used by notifications). Overrides `items`. */
  children?: ReactNode;
  header?: ReactNode;
  align?: "start" | "end";
  width?: string;
  className?: string;
}

export function Dropdown({ trigger, items, children, header, align = "end", width = "w-56", className }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const id = useId();

  const close = useCallback(() => setOpen(false), []);
  const toggle = useCallback(() => setOpen((o) => !o), []);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) close();
    };
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    menu.current?.querySelector<HTMLElement>("[role^=menuitem]:not([disabled])")?.focus();
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, close]);

  const onMenuKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const els = Array.from(menu.current?.querySelectorAll<HTMLElement>("[role^=menuitem]:not([disabled])") ?? []);
    const idx = els.indexOf(document.activeElement as HTMLElement);
    const next = e.key === "ArrowDown" ? (idx + 1) % els.length : (idx - 1 + els.length) % els.length;
    els[next]?.focus();
  };

  return (
    <div ref={root} className={cn("relative", className)}>
      {trigger({ open, toggle, id })}
      {open && (
        <div
          ref={menu}
          id={id}
          role="menu"
          onKeyDown={onMenuKey}
          className={cn(
            "absolute top-full z-50 mt-1.5 origin-top animate-pop-in overflow-hidden rounded-md border border-border-strong bg-raised shadow-pop",
            align === "end" ? "right-0" : "left-0",
            width,
          )}
        >
          {header}
          {children ?? (
            <div className="p-1">
              {items?.map((item, i) =>
                item === "separator" ? (
                  <div key={`sep-${i}`} className="my-1 h-px bg-border" />
                ) : (
                  <DropdownMenuItem key={item.label} item={item} onDone={close} />
                ),
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DropdownMenuItem({ item, onDone }: { item: DropdownItem; onDone: () => void }) {
  const Icon = item.icon;
  const cls = cn(
    "flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-[13px] outline-none transition-colors",
    "focus:bg-hover hover:bg-hover disabled:opacity-50",
    item.tone === "danger" ? "text-bear" : "text-fg",
  );
  const inner = (
    <>
      {Icon && <Icon className="size-4 text-fg-subtle" />}
      {item.label}
    </>
  );
  if (item.href) {
    return (
      <a role="menuitem" href={item.href} className={cls} onClick={onDone}>
        {inner}
      </a>
    );
  }
  return (
    <button
      role="menuitem"
      type="button"
      disabled={item.disabled}
      className={cls}
      onClick={() => {
        item.onSelect?.();
        onDone();
      }}
    >
      {inner}
    </button>
  );
}
