import type { Preferences, Profile, Resume, User } from "@/types/api";

export const STEP_KEYS = [
  "personal",
  "professional",
  "experience",
  "education",
  "skills",
  "resume",
  "job-preferences",
  "application-preferences",
] as const;

export type StepKey = (typeof STEP_KEYS)[number];

export interface StepMeta {
  key: StepKey;
  title: string;
  description: string;
}

export const STEPS: readonly StepMeta[] = [
  {
    key: "personal",
    title: "Personal information",
    description: "How employers should contact you.",
  },
  {
    key: "professional",
    title: "Professional information",
    description: "Your current role, summary and work eligibility.",
  },
  {
    key: "experience",
    title: "Experience",
    description: "Roles you've held. The agent never claims experience you haven't added.",
  },
  {
    key: "education",
    title: "Education",
    description: "Degrees, diplomas and other qualifications.",
  },
  {
    key: "skills",
    title: "Skills",
    description: "What you're good at, and for how long.",
  },
  {
    key: "resume",
    title: "Resume",
    description: "The resumes the agent can attach to applications.",
  },
  {
    key: "job-preferences",
    title: "Job preferences",
    description: "What you want, where, and for how much.",
  },
  {
    key: "application-preferences",
    title: "Application preferences",
    description: "How much the agent may do without asking you.",
  },
];

export function parseStep(value: string | null): StepKey {
  return STEP_KEYS.includes(value as StepKey) ? (value as StepKey) : "personal";
}

export function stepIndex(key: StepKey): number {
  return STEP_KEYS.indexOf(key);
}

/** Whether a step has any data saved yet, for the progress sidebar. */
export function isStepFilled(
  key: StepKey,
  user: User,
  profile: Profile | undefined,
  preferences: Preferences | undefined,
  resumes?: Resume[],
): boolean {
  switch (key) {
    case "personal":
      return Boolean(user.first_name && user.last_name);
    case "professional":
      return Boolean(profile && (profile.headline || profile.current_title || profile.summary));
    case "experience":
      return Boolean(profile?.experiences.length);
    case "education":
      return Boolean(profile?.education.length);
    case "skills":
      return Boolean(profile?.skills.length);
    case "resume":
      return Boolean(resumes?.length);
    case "job-preferences":
      return Boolean(
        profile?.preferred_titles.length || profile?.preferred_locations.length || preferences?.keywords.length,
      );
    case "application-preferences":
      return Boolean(user.onboarding_completed_at);
  }
}
