"use client";

import { useEffect, useRef, type ReactNode } from "react";

/** Small, RAF-coalesced pointer depth; never tracks touch or reduced-motion users. */
export function TiltSurface({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const fine = matchMedia("(hover: hover) and (pointer: fine)");
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;
    let x = 0.5,
      y = 0.5;
    const reset = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      el.style.removeProperty("--tilt-x");
      el.style.removeProperty("--tilt-y");
      el.style.removeProperty("--light-x");
      el.style.removeProperty("--light-y");
      delete el.dataset.tilting;
    };
    const sync = () => {
      reset();
      el.dataset.tiltEnabled = String(fine.matches && !reduced.matches);
    };
    const move = (event: PointerEvent) => {
      if (!fine.matches || reduced.matches || event.pointerType === "touch")
        return;
      const r = el.getBoundingClientRect();
      x = Math.max(0, Math.min(1, (event.clientX - r.left) / r.width));
      y = Math.max(0, Math.min(1, (event.clientY - r.top) / r.height));
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        el.style.setProperty("--tilt-x", `${(0.5 - y) * 6}deg`);
        el.style.setProperty("--tilt-y", `${(x - 0.5) * 7}deg`);
        el.style.setProperty("--light-x", `${x * 100}%`);
        el.style.setProperty("--light-y", `${y * 100}%`);
        el.dataset.tilting = "true";
      });
    };
    sync();
    fine.addEventListener("change", sync);
    reduced.addEventListener("change", sync);
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerleave", reset);
    el.addEventListener("pointercancel", reset);
    return () => {
      reset();
      fine.removeEventListener("change", sync);
      reduced.removeEventListener("change", sync);
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerleave", reset);
      el.removeEventListener("pointercancel", reset);
    };
  }, []);
  return (
    <div ref={ref} className="tilt-surface">
      {children}
    </div>
  );
}
