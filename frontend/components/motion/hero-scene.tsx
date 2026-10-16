"use client";

import Image from "next/image";
import { Pause, Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { depthPose, sceneCanMove } from "@/lib/motion/depth";

/** Layered 2.5D art direction, not a downloadable 3D garment model. */
export function HeroScene() {
  const root = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(false);
  const pausedRef = useRef(false);
  const syncRef = useRef<() => void>(() => {});
  useEffect(() => {
    const el = root.current;
    const hero = el?.closest<HTMLElement>("[data-hero]");
    if (!el || !hero) return;
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");
    const fine = matchMedia(
      "(min-width: 1024px) and (hover: hover) and (pointer: fine)",
    );
    let disposed = false,
      generation = 0,
      frame = 0,
      visible = true;
    let destroyMotion = () => {};
    let synchronize = () => {};
    const resetPose = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      for (const name of ["--scene-rx", "--scene-ry", "--scene-x", "--scene-y"])
        el.style.removeProperty(name);
    };
    const move = (event: PointerEvent) => {
      if (
        !fine.matches ||
        !sceneCanMove(reduced.matches, pausedRef.current, visible) ||
        event.pointerType === "touch"
      )
        return;
      const r = hero.getBoundingClientRect();
      const pose = depthPose(
        (event.clientX - r.left) / r.width,
        (event.clientY - r.top) / r.height,
      );
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        frame = 0;
        el.style.setProperty("--scene-rx", `${pose.rotateX}deg`);
        el.style.setProperty("--scene-ry", `${pose.rotateY}deg`);
        el.style.setProperty("--scene-x", `${pose.x}px`);
        el.style.setProperty("--scene-y", `${pose.y}px`);
      });
    };
    const setup = async () => {
      const ticket = ++generation;
      destroyMotion();
      resetPose();
      el.dataset.motion = "still";
      el.dataset.depthEnabled = String(
        fine.matches && !reduced.matches && !pausedRef.current,
      );
      if (reduced.matches || disposed) return;
      try {
        const [{ gsap }, { ScrollTrigger }] = await Promise.all([
          import("gsap"),
          import("gsap/ScrollTrigger"),
        ]);
        if (disposed || ticket !== generation) return;
        gsap.registerPlugin(ScrollTrigger);
        const ctx = gsap.context(() => {}, el);
        let float: ReturnType<typeof gsap.to> | undefined;
        let scroll: ReturnType<typeof gsap.to> | undefined;
        ctx.add(() => {
          float = gsap.to(".scene-garment", {
            y: fine.matches ? -18 : -8,
            rotation: fine.matches ? -1.5 : -0.5,
            rotationY: fine.matches ? 4 : 0,
            rotationX: fine.matches ? -2 : 0,
            duration: 4.8,
            repeat: -1,
            yoyo: true,
            ease: "sine.inOut",
          });
          if (fine.matches)
            scroll = gsap.to(".scene-scroll", {
              yPercent: 6,
              ease: "none",
              scrollTrigger: {
                trigger: hero,
                start: "top top",
                end: "bottom top",
                scrub: 0.8,
              },
            });
        });
        synchronize = () => {
          const active = sceneCanMove(
            reduced.matches,
            pausedRef.current,
            visible && !document.hidden,
          );
          el.dataset.motion = active ? "running" : "still";
          el.dataset.depthEnabled = String(
            fine.matches && !reduced.matches && !pausedRef.current,
          );
          if (active) {
            float?.resume();
            scroll?.scrollTrigger?.enable(false);
          } else {
            float?.pause();
            scroll?.scrollTrigger?.disable(false);
          }
        };
        syncRef.current = synchronize;
        synchronize();
        destroyMotion = () => {
          synchronize = () => {};
          syncRef.current = () => {};
          ctx.revert();
        };
      } catch {
        // Artwork is fully visible at its neutral pose if animation loading fails.
        if (ticket === generation && !disposed) el.dataset.motion = "still";
      }
    };
    const observer = new IntersectionObserver(
      ([entry]) => {
        visible = entry.isIntersecting;
        synchronize();
      },
      { threshold: 0.05 },
    );
    observer.observe(hero);
    const change = () => {
      void setup();
    };
    const visibility = () => synchronize();
    reduced.addEventListener("change", change);
    fine.addEventListener("change", change);
    document.addEventListener("visibilitychange", visibility);
    hero.addEventListener("pointermove", move);
    hero.addEventListener("pointerleave", resetPose);
    hero.addEventListener("pointercancel", resetPose);
    void setup();
    return () => {
      disposed = true;
      generation++;
      destroyMotion();
      resetPose();
      observer.disconnect();
      reduced.removeEventListener("change", change);
      fine.removeEventListener("change", change);
      document.removeEventListener("visibilitychange", visibility);
      hero.removeEventListener("pointermove", move);
      hero.removeEventListener("pointerleave", resetPose);
      hero.removeEventListener("pointercancel", resetPose);
    };
  }, []);
  return (
    <>
      <div
        ref={root}
        className="hero-scene"
        data-motion="still"
        data-paused={paused}
        aria-hidden="true"
      >
        <div className="scene-camera">
          <div className="scene-scroll">
            <div className="scene-stage scene-layer">
              <Image
                src="/editorial/stage.webp"
                alt=""
                width={1376}
                height={768}
                preload
                unoptimized
              />
            </div>
            <div className="scene-aura" />
            <div className="scene-orbit" />
            <div className="scene-garment scene-layer">
              <Image
                src="/editorial/garment.webp"
                alt=""
                width={1376}
                height={768}
                preload
                unoptimized
              />
            </div>
          </div>
        </div>
      </div>
      <button
        className="scene-control"
        onClick={() => {
          const next = !paused;
          pausedRef.current = next;
          setPaused(next);
          syncRef.current();
        }}
        aria-pressed={paused}
        aria-label={paused ? "ادامهٔ حرکت پوستر" : "توقف حرکت پوستر"}
      >
        {paused ? <Play size={15} /> : <Pause size={15} />}
        <span>{paused ? "ادامهٔ حرکت" : "توقف حرکت"}</span>
      </button>
    </>
  );
}
