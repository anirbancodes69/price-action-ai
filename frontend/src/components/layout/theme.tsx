"use client";

import { useEffect } from "react";
import { usePersistentState } from "@/hooks/use-persistent-state";

export type ThemeName = "dark" | "light";
export const THEME_STORAGE_KEY = "pa-theme";

/**
 * Inline script that applies the saved theme before first paint to avoid a
 * flash. Rendered in <head> by the root layout.
 */
export function ThemeScript() {
  const code = `try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t;}catch(e){}`;
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}

export function useTheme(): [ThemeName, (t: ThemeName) => void] {
  const [theme, setTheme] = usePersistentState<ThemeName>(THEME_STORAGE_KEY, "dark");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  return [theme, setTheme];
}
