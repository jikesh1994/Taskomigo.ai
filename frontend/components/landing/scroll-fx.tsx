"use client";

import { useEffect } from "react";
import { pointer } from "@/lib/pointer";

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

/**
 * Drives the landing page's scroll effects by writing CSS variables (no React
 * re-renders on scroll):
 *
 * - `[data-scroll="through"]`: `--p` goes 0→1 as the element crosses the viewport.
 * - `[data-scroll="sticky"]`: `--p` goes 0→1 while its sticky child is pinned.
 *   With `data-steps="n"` it also sets `data-step` and marks the matching
 *   `[data-stage]` child with `data-active`.
 * - `[data-reveal]`: gets `data-visible` once scrolled into view.
 * - Pointer position goes to `--px`/`--py` on <html> and to the shared `pointer`.
 */
export function ScrollFx() {
  useEffect(() => {
    const root = document.documentElement;
    root.classList.add("fx-ready");
    const scrollers = Array.from(document.querySelectorAll<HTMLElement>("[data-scroll]"));

    let frame = 0;
    const update = () => {
      frame = 0;
      const vh = window.innerHeight;
      for (const el of scrollers) {
        const rect = el.getBoundingClientRect();
        const p =
          el.dataset.scroll === "sticky"
            ? clamp01(-rect.top / Math.max(rect.height - vh, 1))
            : clamp01((vh - rect.top) / (rect.height + vh));
        el.style.setProperty("--p", p.toFixed(4));
        const steps = Number(el.dataset.steps);
        if (steps > 1) {
          const step = String(Math.round(p * (steps - 1)));
          if (el.dataset.step !== step) {
            el.dataset.step = step;
            el.querySelectorAll<HTMLElement>("[data-stage]").forEach((stage) =>
              stage.toggleAttribute("data-active", stage.dataset.stage === step),
            );
          }
        }
      }
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);

    const revealer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.setAttribute("data-visible", "");
            revealer.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.1 },
    );
    document.querySelectorAll("[data-reveal]").forEach((el) => revealer.observe(el));

    const onPointer = (event: PointerEvent) => {
      pointer.x = (event.clientX / window.innerWidth) * 2 - 1;
      pointer.y = -((event.clientY / window.innerHeight) * 2 - 1);
      root.style.setProperty("--px", pointer.x.toFixed(3));
      root.style.setProperty("--py", pointer.y.toFixed(3));
    };
    window.addEventListener("pointermove", onPointer, { passive: true });

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      window.removeEventListener("pointermove", onPointer);
      revealer.disconnect();
      root.classList.remove("fx-ready");
    };
  }, []);

  return null;
}
