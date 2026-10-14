"use client";
import "lenis/dist/lenis.css";
import { useRef, useEffect } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
gsap.registerPlugin(useGSAP, ScrollTrigger);
export function HomeEffects() {
  const ref = useRef<HTMLSpanElement>(null);
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        const hero = ref.current
            ?.closest(".hero")
            ?.querySelector(".hero-frame"),
          art = hero?.querySelector(".type-mark");
        if (hero && art)
          gsap.to(art, {
            yPercent: 12,
            ease: "none",
            scrollTrigger: {
              trigger: hero,
              start: "top top",
              end: "bottom top",
              scrub: 0.5,
            },
          });
      });
      return () => mm.revert();
    },
    { scope: ref },
  );
  useEffect(() => {
    const fine = window.matchMedia(
      "(pointer: fine) and (min-width: 1024px) and (prefers-reduced-motion: no-preference)",
    );
    let lenis: Lenis | undefined;
    let ticker: ((time: number) => void) | undefined;
    function sync() {
      if (!fine.matches) {
        if (ticker) gsap.ticker.remove(ticker);
        lenis?.destroy();
        lenis = undefined;
        return;
      }
      if (lenis) return;
      lenis = new Lenis({
        autoRaf: false,
        duration: 0.8,
        anchors: true,
        prevent: (element) => !!element.closest('[role="dialog"]'),
      });
      lenis.on("scroll", ScrollTrigger.update);
      ticker = (time) => lenis?.raf(time * 1000);
      gsap.ticker.add(ticker);
    }
    sync();
    fine.addEventListener("change", sync);
    const observer = new MutationObserver(() => {
      if (document.body.hasAttribute("data-scroll-locked")) lenis?.stop();
      else lenis?.start();
    });
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ["data-scroll-locked"],
    });
    return () => {
      fine.removeEventListener("change", sync);
      observer.disconnect();
      if (ticker) gsap.ticker.remove(ticker);
      lenis?.destroy();
    };
  }, []);
  return <span ref={ref} aria-hidden="true" />;
}
