"use client";

import dynamic from "next/dynamic";
import { Component, type ReactNode } from "react";
import { useLive3D } from "@/hooks/use-3d-support";

// three.js is only downloaded in the browser, after the page is interactive.
const AmigoScene = dynamic(() => import("@/components/landing/three/amigo-scene"), { ssr: false });

/** If WebGL fails at runtime, render nothing; the hero shows the static amigo. */
class SceneBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    document.documentElement.dataset.amigo = "static";
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

/** The fixed, full-viewport 3D layer behind the landing page content. */
export function LandingScene() {
  const live = useLive3D();
  if (!live) return null;
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0" data-testid="landing-3d">
      <SceneBoundary>
        <AmigoScene />
      </SceneBoundary>
    </div>
  );
}
