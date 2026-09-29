"use client";

import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useLatestSearch, useStartSearch } from "@/hooks/use-jobs";
import { describeError } from "@/services/errors";
import { isSearchActive, timeAgo } from "@/services/jobs";
import type { SearchRun } from "@/types/api";

export function SearchPanel({ hasSources }: { hasSources: boolean }) {
  const latest = useLatestSearch();
  const start = useStartSearch();
  const [error, setError] = useState<string | null>(null);
  const run = latest.data ?? null;
  const active = isSearchActive(run);

  const search = async () => {
    setError(null);
    try {
      await start.mutateAsync();
    } catch (err) {
      setError(describeError(err));
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={search} loading={start.isPending || active} disabled={!hasSources}>
          {active ? "Searching…" : "Search for jobs"}
        </Button>
        <p className="text-sm text-muted" aria-live="polite">
          {!hasSources
            ? "Add a company job board below to start searching."
            : run
              ? <RunSummary run={run} />
              : "Searches every job board you've added and scores each job for you."}
        </p>
      </div>
      {active && run && run.sources_total > 0 && (
        <div
          className="h-1.5 overflow-hidden rounded-full bg-surface-2"
          role="progressbar"
          aria-label="Search progress"
          aria-valuemin={0}
          aria-valuemax={run.sources_total}
          aria-valuenow={run.sources_done}
        >
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${Math.max(5, (run.sources_done / run.sources_total) * 100)}%` }}
          />
        </div>
      )}
      {error && <Alert tone="danger">{error}</Alert>}
      {run?.status === "failed" && run.error && !active && <Alert tone="danger">{run.error}</Alert>}
      {run && !active && run.source_errors.length > 0 && run.status !== "failed" && (
        <Alert tone="warning" title="Some job boards couldn't be searched">
          <ul className="list-inside list-disc">
            {run.source_errors.map((e) => (
              <li key={e.source}>
                {e.source}: {e.message}
              </li>
            ))}
          </ul>
        </Alert>
      )}
    </div>
  );
}

function RunSummary({ run }: { run: SearchRun }) {
  if (isSearchActive(run)) {
    return (
      <>
        Checked {run.sources_done} of {run.sources_total} job boards…
      </>
    );
  }
  if (run.status === "failed") return <>The last search didn&apos;t finish.</>;
  return (
    <>
      Last search {timeAgo(run.finished_at)}: {run.jobs_fetched} open jobs, {run.jobs_new} new
      {run.jobs_closed ? `, ${run.jobs_closed} closed` : ""}.
    </>
  );
}
