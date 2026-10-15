"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { canUseSmoothScroll } from "@/lib/motion/policy";

/** Progressive motion: motion-import failures leave the native shopping UI usable. */
export function Experience({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const root = useRef<HTMLDivElement>(null);
  const area =
    pathname === "/"
      ? "home"
      : pathname.startsWith("/products")
        ? "catalogue"
        : pathname.startsWith("/account")
          ? "account"
          : pathname === "/login"
            ? "auth"
            : "purchase";
  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const desktop = window.matchMedia(
      "(min-width: 1024px) and (pointer: fine)",
    );
    let disposed = false;
    let generation = 0;
    let cleanup = () => {};
    const setup = async () => {
      const ticket = ++generation;
      cleanup();
      cleanup = () => {};
      if (disposed || ticket !== generation || reduced.matches || !root.current)
        return;
      try {
        const [{ gsap }, { ScrollTrigger }] = await Promise.all([
          import("gsap"),
          import("gsap/ScrollTrigger"),
        ]);
        if (
          disposed ||
          ticket !== generation ||
          reduced.matches ||
          !root.current
        )
          return;
        gsap.registerPlugin(ScrollTrigger);
        const motionListeners: (() => void)[] = [];
        const ctx = gsap.context(() => {
          gsap.from(
            "[data-enter], .page > .section-head, .breadcrumb, .auth-panel",
            {
              y: 32,
              opacity: 0,
              duration: 0.85,
              stagger: 0.1,
              ease: "power3.out",
              clearProps: "transform,opacity",
            },
          );
          if (root.current?.querySelector("[data-hero]")) {
            gsap.from(".hero-picture img", {
              scale: 1.08,
              duration: 1.8,
              ease: "power2.out",
              clearProps: "transform",
            });
          }
          const reveals = gsap.utils.toArray<HTMLElement>("[data-reveal]");
          reveals.forEach((element) =>
            gsap.from(element, {
              y: 26,
              opacity: 0,
              duration: 0.7,
              ease: "power2.out",
              clearProps: "transform,opacity",
              scrollTrigger: { trigger: element, start: "top 94%", once: true },
            }),
          );
          if (desktop.matches) {
            if (root.current?.querySelector("[data-hero]"))
              gsap.to("[data-parallax]", {
                yPercent: 9,
                ease: "none",
                scrollTrigger: {
                  trigger: "[data-hero]",
                  start: "top top",
                  end: "bottom top",
                  scrub: 0.7,
                },
              });
            gsap.utils.toArray<HTMLElement>("[data-magnetic]").forEach((el) => {
              const move = (e: PointerEvent) => {
                const r = el.getBoundingClientRect();
                gsap.to(el, {
                  x: (e.clientX - r.left - r.width / 2) * 0.12,
                  y: (e.clientY - r.top - r.height / 2) * 0.12,
                  duration: 0.35,
                  overwrite: true,
                });
              };
              const leave = () =>
                gsap.to(el, {
                  x: 0,
                  y: 0,
                  duration: 0.6,
                  ease: "elastic.out(1,0.4)",
                });
              el.addEventListener("pointermove", move);
              el.addEventListener("pointerleave", leave);
              motionListeners.push(() => {
                el.removeEventListener("pointermove", move);
                el.removeEventListener("pointerleave", leave);
                gsap.set(el, { clearProps: "transform" });
              });
            });
          }
        }, root);
        let stopped = false;
        // Lenis is browsing-only; checkout, forms and touch devices keep native scrolling.
        let destroySmooth = () => {};
        cleanup = () => {
          stopped = true;
          destroySmooth();
          motionListeners.forEach((fn) => fn());
          ctx.revert();
        };
        if (canUseSmoothScroll(pathname, desktop.matches, reduced.matches)) {
          const { default: Lenis } = await import("lenis");
          if (
            disposed ||
            ticket !== generation ||
            stopped ||
            reduced.matches ||
            !desktop.matches
          )
            return;
          const lenis = new Lenis({
            duration: 1.05,
            smoothWheel: true,
            syncTouch: false,
            autoRaf: false,
            prevent: (node) =>
              !!node.closest(
                "[data-lenis-prevent], [role=dialog], input, textarea, select",
              ),
          });
          const tick = (time: number) => lenis.raf(time * 1000);
          const update = () => ScrollTrigger.update();
          lenis.on("scroll", update);
          gsap.ticker.add(tick);
          // Respect Radix's native scroll lock instead of fighting open dialogs.
          const syncLock = () => {
            if (document.body.hasAttribute("data-scroll-locked")) lenis.stop();
            else lenis.start();
          };
          const observer = new MutationObserver(syncLock);
          observer.observe(document.body, {
            attributes: true,
            attributeFilter: ["data-scroll-locked"],
          });
          syncLock();
          destroySmooth = () => {
            observer.disconnect();
            gsap.ticker.remove(tick);
            lenis.off("scroll", update);
            lenis.destroy();
          };
        }
      } catch {
        if (ticket === generation) cleanup(); // Motion is an enhancement, never a prerequisite for shopping.
      }
    };
    void setup();
    const change = () => {
      void setup();
    };
    reduced.addEventListener("change", change);
    desktop.addEventListener("change", change);
    return () => {
      disposed = true;
      cleanup();
      reduced.removeEventListener("change", change);
      desktop.removeEventListener("change", change);
    };
  }, [pathname]);
  return (
    <div ref={root} className="route-stage" data-area={area}>
      {children}
    </div>
  );
}
