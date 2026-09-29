"use client";

import { clsx } from "clsx";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { FormError } from "@/components/forms/form-actions";
import { AgentSettingsForm } from "@/components/preferences/agent-settings-form";
import { JobSearchForm } from "@/components/preferences/job-search-form";
import { EducationSection } from "@/components/profile/education-section";
import { ExperienceSection } from "@/components/profile/experience-section";
import { PersonalForm } from "@/components/profile/personal-form";
import { ProfessionalForm } from "@/components/profile/professional-form";
import { SkillsSection } from "@/components/profile/skills-section";
import { ResumesManager } from "@/components/resumes/resumes-manager";
import { Button } from "@/components/ui/button";
import { useAuth, useCurrentUser } from "@/hooks/use-auth";
import { usePreferences } from "@/hooks/use-preferences";
import { useProfile } from "@/hooks/use-profile";
import { useResumes } from "@/hooks/use-resumes";
import { describeError } from "@/services/errors";
import { usersApi } from "@/services/users";
import { STEPS, STEP_KEYS, isStepFilled, parseStep, stepIndex, type StepKey } from "./steps";

export function OnboardingWizard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const step = parseStep(searchParams.get("step"));
  const index = stepIndex(step);
  const meta = STEPS[index];
  const headingRef = useRef<HTMLHeadingElement>(null);

  // Move focus to the new step's heading so keyboard and screen-reader users follow along.
  useEffect(() => {
    headingRef.current?.focus();
  }, [step]);

  const goTo = (key: StepKey) => {
    router.push(`/onboarding?step=${key}`, { scroll: true });
  };
  const next = () => goTo(STEP_KEYS[Math.min(index + 1, STEP_KEYS.length - 1)]);
  const back = index > 0 ? () => goTo(STEP_KEYS[index - 1]) : undefined;

  const backButton = back && (
    <Button variant="ghost" onClick={back}>
      Back
    </Button>
  );

  return (
    // minmax(0,1fr) stops the horizontally scrolling step list from widening the page on phones.
    <div className="mx-auto grid w-full max-w-6xl grid-cols-[minmax(0,1fr)] gap-8 px-4 py-8 lg:grid-cols-[16rem_minmax(0,1fr)] lg:px-8">
      <StepNav current={step} onSelect={goTo} />
      <section aria-labelledby="step-heading" className="min-w-0">
        <p className="text-sm font-medium text-primary">
          Step {index + 1} of {STEPS.length}
        </p>
        <h1 id="step-heading" ref={headingRef} tabIndex={-1} className="mt-1 text-2xl font-semibold outline-none">
          {meta.title}
        </h1>
        <p className="mt-1 text-muted">{meta.description}</p>
        <div className="mt-6 rounded-xl border border-line bg-surface p-6 shadow-xs">
          <StepBody step={step} onNext={next} backButton={backButton} />
        </div>
      </section>
    </div>
  );
}

function StepBody({ step, onNext, backButton }: { step: StepKey; onNext: () => void; backButton: ReactNode }) {
  const continueLabel = "Save and continue";
  switch (step) {
    case "personal":
      return <PersonalForm submitLabel={continueLabel} onSaved={onNext} />;
    case "professional":
      return <ProfessionalForm submitLabel={continueLabel} onSaved={onNext} secondaryAction={backButton} />;
    case "experience":
      return (
        <ListStep backButton={backButton} onNext={onNext} emptyHint="You can add experience later from your profile.">
          <ExperienceSection />
        </ListStep>
      );
    case "education":
      return (
        <ListStep backButton={backButton} onNext={onNext}>
          <EducationSection />
        </ListStep>
      );
    case "skills":
      return (
        <ListStep backButton={backButton} onNext={onNext}>
          <SkillsSection />
        </ListStep>
      );
    case "resume":
      return <ResumeStep backButton={backButton} onNext={onNext} />;
    case "job-preferences":
      return <JobSearchForm submitLabel={continueLabel} onSaved={onNext} secondaryAction={backButton} />;
    case "application-preferences":
      return <FinalStep backButton={backButton} />;
  }
}

/** Steps whose items save individually; "Continue" just moves on. */
function ListStep({
  children,
  onNext,
  backButton,
  emptyHint,
}: {
  children: ReactNode;
  onNext: () => void;
  backButton: ReactNode;
  emptyHint?: string;
}) {
  return (
    <div className="space-y-6">
      {children}
      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-line pt-5">
        {emptyHint && <p className="mr-auto text-xs text-muted">{emptyHint}</p>}
        {backButton}
        <Button onClick={onNext}>Continue</Button>
      </div>
    </div>
  );
}

function ResumeStep({ onNext, backButton }: { onNext: () => void; backButton: ReactNode }) {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted">
        We read your resume and show you anything that differs from your profile, like a
        different number of years for a skill. Nothing is added until you choose.
      </p>
      <ResumesManager compact />
      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-line pt-5">
        <p className="mr-auto text-xs text-muted">You can add more resumes later from the Resumes page.</p>
        {backButton}
        <Button onClick={onNext}>Continue</Button>
      </div>
    </div>
  );
}

function FinalStep({ backButton }: { backButton: ReactNode }) {
  const router = useRouter();
  const { setUser } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const finish = async () => {
    setError(null);
    try {
      setUser(await usersApi.completeOnboarding());
      router.replace("/dashboard");
    } catch (err) {
      setError(describeError(err));
    }
  };

  return (
    <div className="space-y-4">
      <FormError message={error} />
      <AgentSettingsForm submitLabel="Finish setup" onSaved={finish} secondaryAction={backButton} />
    </div>
  );
}

function StepNav({ current, onSelect }: { current: StepKey; onSelect: (key: StepKey) => void }) {
  const user = useCurrentUser();
  const profile = useProfile();
  const preferences = usePreferences();
  const resumes = useResumes();

  return (
    <nav aria-label="Onboarding steps" className="min-w-0 lg:sticky lg:top-8 lg:self-start">
      <ol className="flex gap-2 overflow-x-auto pb-2 lg:flex-col lg:gap-1 lg:overflow-visible lg:pb-0">
        {STEPS.map((step, i) => {
          const active = step.key === current;
          const filled = isStepFilled(step.key, user, profile.data, preferences.data, resumes.data);
          return (
            <li key={step.key} className="shrink-0">
              <button
                type="button"
                onClick={() => onSelect(step.key)}
                aria-current={active ? "step" : undefined}
                className={clsx(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                  "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring",
                  active ? "bg-primary-soft font-medium text-fg" : "text-muted hover:bg-surface-2 hover:text-fg",
                )}
              >
                <span
                  aria-hidden
                  className={clsx(
                    "grid size-6 shrink-0 place-items-center rounded-full border text-xs",
                    filled
                      ? "border-success bg-success text-white"
                      : active
                        ? "border-primary text-primary"
                        : "border-line-strong",
                  )}
                >
                  {filled ? "✓" : i + 1}
                </span>
                <span className="whitespace-nowrap">{step.title}</span>
                {filled && <span className="sr-only">(completed)</span>}
              </button>
            </li>
          );
        })}
      </ol>
      <p className="mt-4 hidden text-xs text-muted lg:block">
        Your answers save as you go.{" "}
        <Link href="/dashboard" className="text-primary hover:underline">
          Finish later
        </Link>
      </p>
    </nav>
  );
}
