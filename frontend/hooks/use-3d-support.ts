"use client";

import { useSyncExternalStore } from "react";

const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

function subscribeReducedMotion(onChange: () => void) {
  const media = window.matchMedia(REDUCED_MOTION);
  media.addEventListener("change", onChange);
  return () => media.removeEventListener("change", onChange);
}

export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeReducedMotion,
    () => window.matchMedia(REDUCED_MOTION).matches,
    () => false,
  );
}

let webglSupport: boolean | undefined;
function hasWebGL(): boolean {
  if (webglSupport === undefined) {
    try {
      const canvas = document.createElement("canvas");
      webglSupport = Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
    } catch {
      webglSupport = false;
    }
  }
  return webglSupport;
}

/** null during the server render (unknown), then true/false in the browser. */
export function useWebGL(): boolean | null {
  return useSyncExternalStore(
    () => () => {},
    hasWebGL,
    () => null,
  );
}

/** Whether the flying 3D amigo should run: WebGL available and motion allowed. */
export function useLive3D(): boolean | null {
  const webgl = useWebGL();
  const reduced = usePrefersReducedMotion();
  return webgl === null ? null : webgl && !reduced;
}
