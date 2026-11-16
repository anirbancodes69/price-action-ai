"use client";

import { useEffect } from "react";
import { usePersistentState } from "@/hooks/use-persistent-state";

/** What the user chose. "system" follows the OS colour-scheme setting. */
export type ThemePreference = "dark" | "light" | "system";
/** What is applied to <html data-theme>. */
export type ResolvedTheme = "dark" | "light";

export const THEME_STORAGE_KEY = "pa-theme";
/** Dark-first product (PRD-07 UX-01): dark until the user chooses otherwise. */
export const DEFAULT_THEME: ThemePreference = "dark";

const DARK_QUERY = "(prefers-color-scheme: dark)";

export function resolveTheme(pref: ThemePreference, systemDark: boolean): ResolvedTheme {
  if (pref === "system") return systemDark ? "dark" : "light";
  return pref;
}

/**
 * Inline script that applies the saved theme before first paint to avoid a
 * flash. Rendered in <head> by the root layout. Mirrors resolveTheme().
 */
export function ThemeScript() {
  const code =
    `try{var p=localStorage.getItem("${THEME_STORAGE_KEY}")||"${DEFAULT_THEME}";` +
    `if(p==="system")p=matchMedia("${DARK_QUERY}").matches?"dark":"light";` +
    `if(p==="light"||p==="dark")document.documentElement.dataset.theme=p;}catch(e){}`;
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}

/** Theme preference with live OS tracking while "system" is selected. */
export function useTheme(): [ThemePreference, (t: ThemePreference) => void] {
  const [pref, setPref] = usePersistentState<ThemePreference>(THEME_STORAGE_KEY, DEFAULT_THEME);
  useEffect(() => {
    const mq = window.matchMedia(DARK_QUERY);
    const apply = () => {
      document.documentElement.dataset.theme = resolveTheme(pref, mq.matches);
    };
    apply();
    if (pref !== "system") return;
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [pref]);
  return [pref, setPref];
}
