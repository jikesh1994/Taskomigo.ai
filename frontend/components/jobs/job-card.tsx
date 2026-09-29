"use client";

import Link from "next/link";
import { useState } from "react";
import { ScoreBadge } from "@/components/jobs/score-badge";
import { Button } from "@/components/ui/button";
import { useSetJobStatus } from "@/hooks/use-jobs";
import { describeError } from "@/services/errors";
import { WORKPLACE_LABELS, formatSalary, timeAgo } from "@/services/jobs";
import type { JobSummary } from "@/types/api";

export function JobMeta({ job }: { job: JobSummary }) {
  const salary = formatSalary(job.salary_min, job.salary_max, job.salary_currency);
  const parts = [
    job.location,
    WORKPLACE_LABELS[job.workplace],
    salary,
    job.posted_at ? `Posted ${timeAgo(job.posted_at)}` : null,
  ].filter(Boolean);
  return <p className="text-sm text-muted">{parts.join(" · ")}</p>;
}

export function JobCard({ job }: { job: JobSummary }) {
  const setStatus = useSetJobStatus();
  const [error, setError] = useState<string | null>(null);

  const change = async (status: JobSummary["status"]) => {
    setError(null);
    try {
      await setStatus.mutateAsync({ id: job.id, status });
    } catch (err) {
      setError(describeError(err));
    }
  };

  const busy = setStatus.isPending;
  return (
    <article aria-label={`${job.title} at ${job.company}`} className="rounded-xl border border-line bg-surface p-4">
      <div className="flex gap-4">
        <ScoreBadge score={job.overall_match} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2">
            <h3 className="font-semibold">
              <Link href={`/jobs/${job.id}`} className="hover:underline focus-visible:underline">
                {job.title}
              </Link>
            </h3>
            <span className="text-sm text-muted">{job.company}</span>
            {!job.is_active && (
              <span className="rounded bg-surface-2 px-1.5 py-0.5 text-xs text-muted">No longer posted</span>
            )}
          </div>
          <JobMeta job={job} />

          {job.excluded_reason ? (
            <p className="mt-2 text-sm text-warning">Hidden: {job.excluded_reason}</p>
          ) : job.below_min_score && job.status === "new" ? (
            <p className="mt-2 text-sm text-warning">Hidden: below your minimum match score</p>
          ) : null}

          {job.reasons.length > 0 && (
            <ul className="mt-2 space-y-0.5 text-sm" aria-label="Why it matches">
              {job.reasons.slice(0, 3).map((reason) => (
                <li key={reason} className="flex gap-2">
                  <span aria-hidden className="text-success">
                    ✓
                  </span>
                  {reason}
                </li>
              ))}
            </ul>
          )}
          {job.missing_requirements.length > 0 && (
            <p className="mt-1 text-sm text-muted">
              Missing: {job.missing_requirements.slice(0, 4).join(", ")}
              {job.missing_requirements.length > 4 && ` +${job.missing_requirements.length - 4} more`}
            </p>
          )}
          {error && <p className="mt-2 text-sm text-danger">{error}</p>}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap justify-end gap-2 border-t border-line pt-3">
        {job.status === "new" ? (
          <>
            <Button variant="ghost" size="sm" disabled={busy} onClick={() => change("skipped")}>
              Skip
            </Button>
            <Button variant="secondary" size="sm" disabled={busy} onClick={() => change("saved")}>
              Save
            </Button>
          </>
        ) : (
          <Button variant="ghost" size="sm" disabled={busy} onClick={() => change("new")}>
            {job.status === "saved" ? "Unsave" : "Restore"}
          </Button>
        )}
        <Link
          href={`/jobs/${job.id}`}
          className="inline-flex h-8 items-center rounded-lg px-3 text-sm font-medium text-primary hover:bg-primary-soft"
        >
          View details
        </Link>
      </div>
    </article>
  );
}
