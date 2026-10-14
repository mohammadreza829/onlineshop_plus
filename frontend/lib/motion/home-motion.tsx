"use client";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
// Desktop precision-pointer enhancement only. Native mobile/reduced-motion needs
// neither GSAP nor Lenis bytes; essential hero content is always server-rendered.
const Effects = dynamic(
  () => import("./home-effects").then((m) => m.HomeEffects),
  { ssr: false },
);
export function HomeMotion() {
  const [enabled, setEnabled] = useState(false);
  useEffect(() => {
    const match = window.matchMedia(
      "(pointer: fine) and (min-width: 1024px) and (prefers-reduced-motion: no-preference)",
    );
    const sync = () => setEnabled(match.matches);
    sync();
    match.addEventListener("change", sync);
    return () => match.removeEventListener("change", sync);
  }, []);
  return enabled ? <Effects /> : null;
}
