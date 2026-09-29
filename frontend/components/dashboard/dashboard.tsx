"use client";

import { clsx } from "clsx";
import Link from "next/link";
import { isStepFilled, STEPS, type StepKey } from "@/components/onboarding/steps";
import { QueryState } from "@/components/query-state";
import { Alert } from "@/components/ui/alert";
import { LinkButton } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { useCurrentUser } from "@/hooks/use-auth";
import { useJobStats } from "@/hooks/use-jobs";
import { usePreferences } from "@/hooks/use-preferences";
import { useProfile } from "@/hooks/use-profile";
import { useResumes } from "@/hooks/use-resumes";
import { timeAgo } from "@/services/jobs";
import type { JobStats, Preferences } from "@/types/api";

// Profile sections a user can fill today, and where to edit each one.
const CHECKLIST: { key: StepKey; href: string }[] = [
  { key: "personal", href: "/profile" },
  { key: "professional", href: "/profile" },
  { key: "experience", href: "/profile" },
  { key: "education", href: "/profile" },
  { key: "skills", href: "/profile" },
  { key: "resume", href: "/resumes" },
  { key: "job-preferences", href: "/settings" },
];

export function Dashboard() {
  const user = useCurrentUser();
  const profile = useProfile();
  const preferences = usePreferences();
  const resumes = useResumes();
  const jobStats = useJobStats();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Welcome, {user.first_name}</h1>
        <p className="mt-1 text-muted">Here’s where your job search stands.</p>
      </div>

      {!user.onboarding_completed_at && (
        <Alert tone="warning" title="Finish setting up your profile">
          <p>Your agent can only apply with information you’ve given it.</p>
          <LinkButton href="/onboarding" size="sm" className="mt-3">
            Continue setup
          </LinkButton>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Profile completeness" description="What the agent knows about you." />
          <CardBody>
            <QueryState query={profile}>
              {(p) => {
                const items = CHECKLIST.map((item) => ({
                  ...item,
                  title: STEPS.find((s) => s.key === item.key)!.title,
                  done: isStepFilled(item.key, user, p, preferences.data, resumes.data),
                }));
                const done = items.filter((i) => i.done).length;
                return (
                  <>
                    <div className="mb-4 flex items-center gap-3">
                      <div
                        className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2"
                        role="progressbar"
                        aria-label="Profile completeness"
                        aria-valuemin={0}
                        aria-valuemax={items.length}
                        aria-valuenow={done}
                      >
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${(done / items.length) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm text-muted">
                        {done} of {items.length}
                      </span>
                    </div>
                    <ul className="space-y-2">
                      {items.map((item) => (
                        <li key={item.key} className="flex items-center justify-between text-sm">
                          <span className="flex items-center gap-2">
                            <span
                              aria-hidden
                              className={clsx(
                                "grid size-5 place-items-center rounded-full text-[10px]",
                                item.done ? "bg-success text-white" : "border border-line-strong",
                              )}
                            >
                              {item.done ? "✓" : ""}
                            </span>
                            {item.title}
                            <span className="sr-only">{item.done ? "(done)" : "(not started)"}</span>
                          </span>
                          {!item.done && (
                            <Link href={item.href} className="text-primary hover:underline">
                              Add
                            </Link>
                          )}
                        </li>
                      ))}
                    </ul>
                  </>
                );
              }}
            </QueryState>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Agent behaviour"
            action={
              <Link href="/settings" className="text-sm text-primary hover:underline">
                Change
              </Link>
            }
          />
          <CardBody>
            <QueryState query={preferences}>{(prefs) => <AgentSummary preferences={prefs} />}</QueryState>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader
          title="Jobs"
          action={
            <Link href="/jobs" className="text-sm text-primary hover:underline">
              View jobs
            </Link>
          }
        />
        <CardBody>
          <QueryState query={jobStats}>{(stats) => <JobsSummary stats={stats} />}</QueryState>
        </CardBody>
      </Card>
    </div>
  );
}

function AgentSummary({ preferences: p }: { preferences: Preferences }) {
  const rows: [string, string][] = [
    ["Fill standard fields", p.auto_fill_enabled ? "Yes" : "No"],
    ["Draft answers", p.auto_answer_enabled ? "Yes" : "No"],
    ["Review before submitting", p.review_before_submit ? "Yes" : "No"],
    ["Automatic submission", p.auto_submit_enabled ? "On" : "Off"],
    ["Minimum match score", String(p.min_match_score)],
    ["Applications per day", String(p.max_applications_per_day)],
  ];
  return (
    <dl className="divide-y divide-line text-sm">
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between py-2">
          <dt className="text-muted">{label}</dt>
          <dd className="font-medium">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function JobsSummary({ stats }: { stats: JobStats }) {
  if (stats.sources === 0) {
    return (
      <div className="text-sm">
        <p className="text-muted">Follow a few companies&apos; job boards and Taskomigo will score every opening for you.</p>
        <LinkButton href="/jobs" size="sm" className="mt-3">
          Find jobs
        </LinkButton>
      </div>
    );
  }
  const tiles: [string, number][] = [
    ["Matches", stats.matches],
    ["New this week", stats.new_this_week],
    ["Saved", stats.saved],
    ["Job boards", stats.sources],
  ];
  const last = stats.last_search;
  return (
    <div className="space-y-3">
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {tiles.map(([label, value]) => (
          <div key={label} className="rounded-lg bg-surface-2 px-4 py-3">
            <dt className="text-xs text-muted">{label}</dt>
            <dd className="text-2xl font-semibold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="text-xs text-muted">
        {last
          ? last.status === "succeeded"
            ? `Last search ${timeAgo(last.finished_at)}.`
            : last.status === "failed"
              ? "The last search didn't finish. Try again from the Jobs page."
              : "A search is running."
          : "You haven't searched yet."}
      </p>
    </div>
  );
}