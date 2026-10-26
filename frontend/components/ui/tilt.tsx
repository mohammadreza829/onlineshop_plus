"use client";
// Adapted from ibelick's Tilt on 21st.dev (demo 1448 / Motion Primitives).
// Uses the project's installed motion package; no duplicate framer-motion.
import { useRef, type ReactNode } from "react";
import {
  motion,
  useMotionTemplate,
  useMotionValue,
  useSpring,
} from "motion/react";

export function Tilt({
  children,
  className = "",
  strength = 6,
}: {
  children: ReactNode;
  className?: string;
  strength?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0),
    y = useMotionValue(0);
  const rx = useSpring(x, { stiffness: 220, damping: 28 });
  const ry = useSpring(y, { stiffness: 220, damping: 28 });
  const transform = useMotionTemplate`perspective(1200px) rotateX(${rx}deg) rotateY(${ry}deg)`;
  const reset = () => {
    x.jump(0);
    y.jump(0);
  };
  return (
    <motion.div
      ref={ref}
      className={`spatial-tilt ${className}`}
      style={{ transform }}
      onPointerMove={(e) => {
        // Check at event time: live preference changes are respected immediately.
        if (
          e.pointerType !== "mouse" ||
          !window.matchMedia(
            "(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)",
          ).matches
        ) {
          reset();
          return;
        }
        const b = ref.current?.getBoundingClientRect();
        if (!b) return;
        x.set((-(e.clientY - b.top - b.height / 2) / b.height) * strength);
        y.set(((e.clientX - b.left - b.width / 2) / b.width) * strength);
      }}
      onPointerLeave={() => {
        x.set(0);
        y.set(0);
      }}
      onPointerCancel={reset}
      onBlur={reset}
    >
      {children}
    </motion.div>
  );
}
