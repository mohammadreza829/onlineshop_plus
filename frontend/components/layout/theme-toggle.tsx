"use client";
import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";
const query = "(prefers-color-scheme: dark)";
const subscribe = (f: () => void) => {
  const m = matchMedia(query);
  m.addEventListener("change", f);
  return () => m.removeEventListener("change", f);
};
// System theme only: avoids a flash of incorrect theme or persistence scripts.
export function ThemeIndicator() {
  const dark = useSyncExternalStore(
    subscribe,
    () => matchMedia(query).matches,
    () => false,
  );
  return (
    <span
      className="theme-indicator"
      title="رنگ‌بندی مطابق تنظیم دستگاه"
      aria-label="رنگ‌بندی مطابق تنظیم دستگاه"
    >
      {dark ? <Moon size={15} /> : <Sun size={15} />}
      <span>با حال‌وهوای شما</span>
    </span>
  );
}
