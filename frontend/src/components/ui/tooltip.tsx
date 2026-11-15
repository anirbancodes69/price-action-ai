"use client";

import { useCallback, useId, useRef, useState, type ReactElement, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

type Side = "top" | "right" | "bottom" | "left";

interface TooltipProps {
  content: ReactNode;
  side?: Side;
  /** When false the tooltip never shows (e.g. sidebar expanded). */
  enabled?: boolean;
  children: ReactElement;
  className?: string;
  /** Classes for the wrapping anchor element (e.g. "flex w-full"). */
  anchorClassName?: string;
  delay?: number;
}

const GAP = 8;

/**
 * Lightweight tooltip rendered in a portal so it is never clipped by
 * overflow containers. Opens on hover and keyboard focus.
 */
export function Tooltip({ content, side = "top", enabled = true, children, className, anchorClassName, delay = 120 }: TooltipProps) {
  const id = useId();
  const anchor = useRef<HTMLSpanElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  const show = useCallback(() => {
    if (!enabled) return;
    timer.current = setTimeout(() => {
      const r = anchor.current?.getBoundingClientRect();
      if (!r) return;
      const map: Record<Side, { top: number; left: number }> = {
        top: { top: r.top - GAP, left: r.left + r.width / 2 },
        bottom: { top: r.bottom + GAP, left: r.left + r.width / 2 },
        right: { top: r.top + r.height / 2, left: r.right + GAP },
        left: { top: r.top + r.height / 2, left: r.left - GAP },
      };
      setPos(map[side]);
    }, delay);
  }, [enabled, side, delay]);

  const hide = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    setPos(null);
  }, []);

  const transform: Record<Side, string> = {
    top: "-translate-x-1/2 -translate-y-full",
    bottom: "-translate-x-1/2",
    right: "-translate-y-1/2",
    left: "-translate-x-full -translate-y-1/2",
  };

  return (
    <span
      ref={anchor}
      className={cn("inline-flex", anchorClassName)}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      aria-describedby={pos ? id : undefined}
    >
      {children}
      {pos &&
        createPortal(
          <span
            id={id}
            role="tooltip"
            style={{ top: pos.top, left: pos.left }}
            className={cn(
              "pointer-events-none fixed z-[100] max-w-xs animate-fade-in rounded border border-border-strong bg-raised px-2 py-1 text-2xs leading-snug text-fg shadow-pop",
              transform[side],
              className,
            )}
          >
            {content}
          </span>,
          document.body,
        )}
    </span>
  );
}
