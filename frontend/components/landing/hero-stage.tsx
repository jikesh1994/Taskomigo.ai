"use client";

import { AmigoAnchor } from "@/components/landing/backdrop";
import { useLive3D } from "@/hooks/use-3d-support";

/** CSS-only amigo: used without WebGL and for prefers-reduced-motion. */
export function StaticAmigo() {
  return (
    <div className="flex h-full items-center justify-center" data-testid="static-amigo">
      <div className="relative size-52 sm:size-72">
        <div className="absolute -inset-10 rounded-full bg-[radial-gradient(circle,rgb(236_72_153/0.45),transparent_65%)] blur-2xl" />
        <div className="absolute inset-0 rounded-full bg-[radial-gradient(circle_at_32%_28%,#f5d0fe,#a78bfa_30%,#7c3aed_62%,#3b0764)] shadow-[0_40px_90px_-20px_rgb(236_72_153/0.6)]" />
        <svg viewBox="0 0 100 100" className="absolute inset-0" aria-hidden>
          <ellipse cx="36" cy="40" rx="7" ry="9" fill="#fff" />
          <ellipse cx="64" cy="40" rx="7" ry="9" fill="#fff" />
          <circle cx="37" cy="41" r="3.5" fill="#1a1033" />
          <circle cx="65" cy="41" r="3.5" fill="#1a1033" />
          <path d="M30 57l12 12 28-26" fill="none" stroke="#fff" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  );
}

const CHIPS = [
  { text: "Filled 11 of 12 fields", tone: "bg-success", className: "left-0 top-8 sm:left-4", depth: 1.2, delay: "0s" },
  { text: "Resume attached", tone: "bg-[#ec4899]", className: "right-0 top-24 sm:right-2", depth: 0.8, delay: "-2s" },
  { text: "Your turn: create an account", tone: "bg-warning", className: "bottom-10 left-2 sm:left-12", depth: 1.5, delay: "-4s" },
];

/**
 * The hero's right-hand stage. With live 3D it is the flying amigo's first anchor
 * (the fixed canvas draws the mascot here); otherwise it shows the static amigo.
 */
export function HeroStage() {
  const live = useLive3D();
  return (
    <div
      className="relative h-[22rem] [perspective:1000px] sm:h-[30rem] lg:h-[36rem]"
      role="img"
      aria-label="Taskomigo's friendly mascot, surrounded by completed tasks and a paused step waiting for you"
    >
      <AmigoAnchor className="absolute inset-0" scale={0.9} turn={-0.15} />
      {live === false ? (
        <StaticAmigo />
      ) : (
        // Shown only if the 3D scene fails at runtime (LandingScene sets the flag).
        <div className="hidden h-full [html[data-amigo=static]_&]:block">
          <StaticAmigo />
        </div>
      )}
      {CHIPS.map((chip) => (
        <div
          key={chip.text}
          aria-hidden
          className={`absolute ${chip.className} motion-safe:animate-float`}
          style={{ animationDelay: chip.delay }}
        >
          <div
            className="glass flex items-center gap-2 rounded-full px-4 py-2.5 text-xs font-medium transition-transform duration-300 ease-out sm:text-sm"
            style={{
              transform: `translate3d(calc(var(--px, 0) * ${chip.depth * 16}px), calc(var(--py, 0) * ${chip.depth * -12}px), 0) rotateY(calc(var(--px, 0) * 14deg)) rotateX(calc(var(--py, 0) * 10deg))`,
            }}
          >
            <span className={`size-2 rounded-full ${chip.tone} shadow-[0_0_10px_currentColor]`} />
            {chip.text}
          </div>
        </div>
      ))}
    </div>
  );
}
