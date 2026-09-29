"use client";

import { clsx } from "clsx";
import { useRef, type PointerEvent, type ReactNode } from "react";

interface TiltCardProps {
  children: ReactNode;
  className?: string;
  /** Maximum tilt in degrees while the mouse is over the card. */
  max?: number;
  /** Resting pose, e.g. to present a card at an angle. */
  restX?: number;
  restY?: number;
}

/**
 * Tilts towards the mouse in 3D with a soft glare. Mouse only (not touch), and off
 * for prefers-reduced-motion. Children can pop forward with `[transform:translateZ(…)]`.
 */
export function TiltCard({ children, className, max = 7, restX = 0, restY = 0 }: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null);

  const set = (rx: number, ry: number, gx = 50, gy = 50, glare = 0) => {
    const style = ref.current?.style;
    if (!style) return;
    style.setProperty("--rx", `${rx}deg`);
    style.setProperty("--ry", `${ry}deg`);
    style.setProperty("--gx", `${gx}%`);
    style.setProperty("--gy", `${gy}%`);
    style.setProperty("--glare", String(glare));
  };

  const onMove = (event: PointerEvent<HTMLDivElement>) => {
    if (event.pointerType !== "mouse" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    set((0.5 - y) * max * 2, (x - 0.5) * max * 2, x * 100, y * 100, 1);
  };

  return (
    <div
      ref={ref}
      onPointerMove={onMove}
      onPointerLeave={() => set(restX, restY)}
      className={clsx("group/tilt relative transition-transform duration-300 ease-out [transform-style:preserve-3d]", className)}
      style={
        {
          "--rx": `${restX}deg`,
          "--ry": `${restY}deg`,
          transform: "perspective(1000px) rotateX(var(--rx)) rotateY(var(--ry))",
        } as React.CSSProperties
      }
    >
      {children}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-[inherit] transition-opacity duration-300"
        style={{
          opacity: "var(--glare, 0)",
          background: "radial-gradient(circle at var(--gx, 50%) var(--gy, 50%), rgb(255 255 255 / 0.16), transparent 55%)",
        }}
      />
    </div>
  );
}
