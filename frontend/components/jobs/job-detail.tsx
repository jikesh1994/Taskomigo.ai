"use client";

import { clsx } from "clsx";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { JobMeta } from "@/components/jobs/job-card";
import { ScoreBadge, ScoreBar } from "@/components/jobs/score-badge";
import { QueryState } from "@/components/query-state";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { useAnalyzeJob, useJob, useSetJobStatus } from "@/hooks/use-jobs";
import { ApiError, describeError } from "@/services/errors";
import { PLATFORM_LABELS, formatSalary } from "@/services/jobs";
import type { Basis, JobDetail, JobMatchStatus, MatchComponent } from "@/types/api";

const COMPONENT_LABELS: Record<MatchComponent, string> = {
  skills: "Skills",
  experience: "Experience",
  location: "Location",
  salary: "Salary",
  preferences: "Your preferences",
  other: "Other requirements",
};

export function JobDetailView({ id }: { id: string }) {
  const job = useJob(id);
  if (job.isError && job.error instanceof ApiError && job.error.status === 404) {
    return (
      <Alert tone="warning" title="Job not found">
        <p>It may have been removed from your lists.</p>
        <Link href="/jobs" className="mt-2 inline-block text-primary hover:underline">
          Back to jobs
        </Link>
      </Alert>
    );
  }
  return <QueryState query={job}>{(data) => <Detail job={data} />}</QueryState>;
}

function Detail({ job }: { job: JobDetail }) {
  return (
    <div className="space-y-6">
      <Link href="/jobs" className="text-sm text-primary hover:underline">
        ← All jobs
      </Link>
      <Header job={job} />
      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <div className="min-w-0 space-y-6">
          <WhyCard job={job} />
          <AnalysisCard job={job} />
          <Card>
            <CardHeader title="Job description" description={`From ${job.company}'s careers page.`} />
            <CardBody>
              <div className="max-w-none text-sm leading-relaxed whitespace-pre-line">{job.description}</div>
            </CardBody>
          </Card>
        </div>
        <aside className="space-y-6">
          <BreakdownCard job={job} />
          <ResumeCard job={job} />
          <FactsCard job={job} />
        </aside>
      </div>
    </div>
  );
}

function Header({ job }: { job: JobDetail }) {
  const setStatus = useSetJobStatus();
  const [error, setError] = useState<string | null>(null);
  const change = async (status: JobMatchStatus) => {
    setError(null);
    try {
      await setStatus.mutateAsync({ id: job.id, status });
    } catch (err) {
      setError(describeError(err));
    }
  };

  return (
    <Card>
      <CardBody className="space-y-4">
        <div className="flex flex-wrap items-start gap-4">
          <ScoreBadge score={job.overall_match} size="lg" />
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-semibold">{job.title}</h1>
            <p className="font-medium">
              {job.company}
              {job.department && <span className="font-normal text-muted"> · {job.department}</span>}
            </p>
            <JobMeta job={job} />
          </div>
        </div>
        {!job.is_active && (
          <Alert tone="warning">This job is no longer posted on {job.company}&apos;s careers page.</Alert>
        )}
        {job.excluded_reason && <Alert tone="warning">Hidden from your matches: {job.excluded_reason}</Alert>}
        {!job.excluded_reason && job.below_min_score && (
          <Alert tone="info">
            This scores below your minimum match score ({job.min_match_score}), so it&apos;s hidden from Matches.
          </Alert>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <Button disabled title="Supervised applications arrive in the next release">
            Apply with AI (coming next)
          </Button>
          {job.status === "saved" ? (
            <Button variant="secondary" loading={setStatus.isPending} onClick={() => change("new")}>
              Saved ✓ (undo)
            </Button>
          ) : (
            <Button variant="secondary" loading={setStatus.isPending} onClick={() => change("saved")}>
              Save
            </Button>
          )}
          {job.status === "skipped" ? (
            <Button variant="ghost" disabled={setStatus.isPending} onClick={() => change("new")}>
              Restore
            </Button>
          ) : (
            <Button variant="ghost" disabled={setStatus.isPending} onClick={() => change("skipped")}>
              Skip
            </Button>
          )}
          <a
            href={job.application_url}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto text-sm text-primary hover:underline"
          >
            Open on {PLATFORM_LABELS[job.platform] ?? "the careers site"} ↗
          </a>
        </div>
        {error && <p className="text-sm text-danger">{error}</p>}
      </CardBody>
    </Card>
  );
}

function List({ items, icon, tone, label }: { items: string[]; icon: string; tone: string; label: string }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="mb-1.5 text-sm font-semibold">{label}</h3>
      <ul className="space-y-1 text-sm">
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <span aria-hidden className={tone}>
              {icon}
            </span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function WhyCard({ job }: { job: JobDetail }) {
  const empty = !job.reasons.length && !job.missing_requirements.length && !job.concerns.length;
  return (
    <Card>
      <CardHeader
        title="How this job fits you"
        description="Based only on your profile, skills and preferences. Not a prediction of hiring."
      />
      <CardBody className="space-y-5">
        {empty && <p className="text-sm text-muted">There isn&apos;t much in this posting to compare.</p>}
        <List label="Why it matches" items={job.reasons} icon="✓" tone="text-success" />
        <List label="What you're missing" items={job.missing_requirements} icon="–" tone="text-warning" />
        <List label="Things to consider" items={job.concerns} icon="!" tone="text-warning" />
        <List label="Not stated in the posting" items={job.notes} icon="·" tone="text-muted" />
      </CardBody>
    </Card>
  );
}

function BreakdownCard({ job }: { job: JobDetail }) {
  return (
    <Card>
      <CardHeader
        title="Score breakdown"
        action={
          <Link href="/settings#matching" className="text-sm text-primary hover:underline">
            Weights
          </Link>
        }
      />
      <CardBody className="space-y-3">
        {(Object.keys(COMPONENT_LABELS) as MatchComponent[]).map((key) => (
          <ScoreBar key={key} label={COMPONENT_LABELS[key]} score={job.scores[key]} weight={job.weights[key]} />
        ))}
      </CardBody>
    </Card>
  );
}

function ResumeCard({ job }: { job: JobDetail }) {
  return (
    <Card>
      <CardHeader title="Suggested resume" />
      <CardBody className="text-sm">
        {job.recommended_resume ? (
          <>
            <p className="font-medium">{job.recommended_resume.name}</p>
            {job.recommended_resume.reason && <p className="mt-0.5 text-muted">{job.recommended_resume.reason}</p>}
          </>
        ) : (
          <p className="text-muted">
            <Link href="/resumes" className="text-primary hover:underline">
              Upload a resume
            </Link>{" "}
            to get a suggestion for each job.
          </p>
        )}
      </CardBody>
    </Card>
  );
}

function Fact({ label, value, evidence }: { label: string; value: ReactNode; evidence?: string | null }) {
  return (
    <div className="py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="font-medium">{value}</dd>
      {evidence && <dd className="mt-0.5 text-xs text-muted italic">“{evidence}”</dd>}
    </div>
  );
}

function FactsCard({ job }: { job: JobDetail }) {
  const f = job.facts;
  const salary = formatSalary(f.salary_min, f.salary_max, f.salary_currency);
  const unknown = <span className="font-normal text-muted">Not stated</span>;
  return (
    <Card>
      <CardHeader title="From the posting" description="Read directly from the text, with the line it came from." />
      <CardBody>
        <dl className="divide-y divide-line text-sm">
          <Fact
            label="Required skills"
            value={f.required_skills.length ? f.required_skills.join(", ") : unknown}
          />
          {f.preferred_skills.length > 0 && <Fact label="Nice to have" value={f.preferred_skills.join(", ")} />}
          <Fact
            label="Experience"
            value={f.min_years !== null ? `${f.min_years}+ years` : unknown}
            evidence={f.years_evidence}
          />
          <Fact label="Salary" value={salary ?? unknown} evidence={salary ? f.salary_evidence : null} />
          <Fact
            label="Visa sponsorship"
            value={f.sponsorship === null ? unknown : f.sponsorship ? "Offered" : "Not offered"}
            evidence={f.sponsorship_evidence}
          />
        </dl>
      </CardBody>
    </Card>
  );
}

const BASIS_STYLES: Record<Basis, string> = {
  explicit: "bg-success-soft text-success",
  inferred: "bg-warning-soft text-warning",
  unknown: "bg-surface-2 text-muted",
};

function BasisTag({ basis }: { basis: Basis }) {
  const label = basis === "explicit" ? "Stated" : basis === "inferred" ? "Inferred" : "Unknown";
  return (
    <span
      className={clsx("rounded px-1.5 py-0.5 text-[11px] font-medium", BASIS_STYLES[basis])}
      title={
        basis === "explicit"
          ? "Quoted from the posting"
          : basis === "inferred"
            ? "A reading of the posting, not stated directly"
            : "The posting doesn't say"
      }
    >
      {label}
    </span>
  );
}

function AnalysisCard({ job }: { job: JobDetail }) {
  const analyze = useAnalyzeJob(job.id);
  const [error, setError] = useState<string | null>(null);
  const working = job.analysis_status === "pending" || job.analysis_status === "processing";
  const a = job.analysis;

  const run = async () => {
    setError(null);
    try {
      await analyze.mutateAsync();
    } catch (err) {
      setError(describeError(err));
    }
  };

  return (
    <Card>
      <CardHeader
        title="AI analysis"
        description="A structured read of the posting. Each point says whether it's stated or inferred."
        action={
          !a && (
            <Button size="sm" variant="secondary" onClick={run} loading={analyze.isPending || working}>
              {working ? "Analysing…" : job.analysis_status === "failed" ? "Try again" : "Analyse with AI"}
            </Button>
          )
        }
      />
      <CardBody className="space-y-5 text-sm">
        {error && <Alert tone="danger">{error}</Alert>}
        {job.analysis_status === "failed" && job.analysis_error && !working && (
          <Alert tone="danger">{job.analysis_error}</Alert>
        )}
        {!a && !working && job.analysis_status !== "failed" && (
          <p className="text-muted">
            Get a summary, every requirement (required or nice to have), responsibilities and benefits.
          </p>
        )}
        {working && <p className="text-muted">Reading the posting…</p>}
        {a && (
          <>
            <p>{a.summary}</p>
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              <span>
                Seniority: <strong className="capitalize">{a.seniority.value}</strong>{" "}
                <BasisTag basis={a.seniority.basis} />
              </span>
              <span>
                Work authorisation: <strong>{a.work_authorization.value}</strong>{" "}
                <BasisTag basis={a.work_authorization.basis} />
              </span>
            </div>
            {a.requirements.length > 0 && (
              <div>
                <h3 className="mb-1.5 font-semibold">Requirements</h3>
                <ul className="divide-y divide-line">
                  {a.requirements.map((r) => (
                    <li key={r.text} className="py-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{r.text}</span>
                        <span className="text-xs text-muted">
                          {r.importance === "required" ? "Required" : "Nice to have"}
                        </span>
                        <BasisTag basis={r.basis} />
                      </div>
                      {r.evidence && <p className="mt-0.5 text-xs text-muted italic">“{r.evidence}”</p>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <List label="Responsibilities" items={a.responsibilities} icon="•" tone="text-muted" />
            <List label="Benefits" items={a.benefits} icon="•" tone="text-muted" />
          </>
        )}
      </CardBody>
    </Card>
  );
}
