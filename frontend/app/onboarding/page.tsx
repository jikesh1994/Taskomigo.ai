import type { Metadata } from "next";
import { Suspense } from "react";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import { FullPageSpinner } from "@/components/ui/spinner";

export const metadata: Metadata = { title: "Set up your profile" };

export default function OnboardingPage() {
  // The wizard reads ?step= with useSearchParams, which needs a Suspense boundary.
  return (
    <Suspense fallback={<FullPageSpinner />}>
      <OnboardingWizard />
    </Suspense>
  );
}
