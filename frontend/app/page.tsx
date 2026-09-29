import { Aurora } from "@/components/landing/backdrop";
import { LandingHeader } from "@/components/landing/landing-header";
import { LandingScene } from "@/components/landing/landing-scene";
import { ScrollFx } from "@/components/landing/scroll-fx";
import {
  FinalCta,
  Hero,
  HowItWorks,
  HumanInTheLoop,
  LandingFooter,
  PainPoints,
  Pipeline,
  RolesMarquee,
  Trust,
} from "@/components/landing/sections";

// Public, server-rendered marketing page with its own vivid theme (`.landing`).
// Layers, back to front: aurora glow → fixed 3D scene (starfield + flying amigo) →
// content. Signed-in visitors see an "Open" button in the header instead of a redirect.
export default function LandingPage() {
  return (
    <div className="landing relative flex min-h-full flex-1 flex-col">
      <Aurora />
      <LandingScene />
      <ScrollFx />
      <div className="relative flex flex-1 flex-col">
        <LandingHeader />
        <main className="flex-1">
          <Hero />
          <RolesMarquee />
          <HumanInTheLoop />
          <PainPoints />
          <Pipeline />
          <HowItWorks />
          <Trust />
          <FinalCta />
        </main>
        <LandingFooter />
      </div>
    </div>
  );
}
